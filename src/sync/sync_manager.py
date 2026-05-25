"""
Менеджер синхронизации данных
Обрабатывает файлы от менеджеров и обновляет центральную БД
"""
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import json

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.database import get_database
from database.models import (
    Manager, Client, Address, Product, Order, OrderItem,
    PaymentLocation, BonusTransaction, SyncLog,
    OrderStatus, PaymentStatus, PaymentType, BonusTransactionType
)
from sync.webdav_client import LocalWebDAVManager
from sync.json_parser import JSONParser
from sync.conflict_resolver import ConflictResolver


class SyncManager:
    """Менеджер синхронизации данных между устройствами и центральной системой"""

    def __init__(self, engine_or_webdav_root):
        """
        Инициализация менеджера синхронизации

        Args:
            engine_or_webdav_root: SQLAlchemy engine или путь к корневой директории WebDAV
        """
        # Поддерживаем оба варианта инициализации
        if isinstance(engine_or_webdav_root, str):
            # Старый вариант - путь к WebDAV
            self.db = get_database()
            self.webdav = LocalWebDAVManager(engine_or_webdav_root)
            self.engine = self.db.engine
        else:
            # Новый вариант - SQLAlchemy engine
            self.engine = engine_or_webdav_root
            self.db = None
            self.webdav = None

        self.parser = JSONParser()
        self.resolver = ConflictResolver()
        self.Session = sessionmaker(bind=self.engine)

    def sync_all_managers(self) -> Dict[str, Dict]:
        """
        Синхронизировать данные всех менеджеров

        Returns:
            Словарь с результатами синхронизации для каждого менеджера
        """
        results = {}
        managers = self.webdav.list_managers()

        for pin_code in managers:
            print(f"Syncing manager {pin_code}...")
            result = self.sync_manager(pin_code)
            results[pin_code] = result

        return results

    def sync_manager(self, pin_code: str) -> Dict:
        """
        Синхронизировать данные конкретного менеджера

        Args:
            pin_code: PIN-код менеджера

        Returns:
            Словарь с результатами синхронизации
        """
        result = {
            "pin_code": pin_code,
            "started_at": datetime.utcnow(),
            "orders_processed": 0,
            "clients_processed": 0,
            "payments_processed": 0,
            "errors": []
        }

        session = self.db.get_session()

        try:
            # Получаем или создаем менеджера
            manager = self._get_or_create_manager(session, pin_code)

            # Обрабатываем файлы из outgoing
            outgoing_files = self.webdav.list_outgoing_files(pin_code)

            for file_path in outgoing_files:
                try:
                    self._process_file(session, manager, file_path, result)
                except Exception as e:
                    error_msg = f"Error processing {file_path.name}: {str(e)}"
                    print(error_msg)
                    result["errors"].append(error_msg)

            # Генерируем файлы для incoming
            self._generate_incoming_files(session, pin_code)

            # Обновляем время последней синхронизации
            manager.last_sync_at = datetime.utcnow()
            session.commit()

            # Логируем синхронизацию
            self._log_sync(session, manager, result)

            result["completed_at"] = datetime.utcnow()
            result["success"] = True

        except Exception as e:
            session.rollback()
            result["errors"].append(f"Sync failed: {str(e)}")
            result["success"] = False
            print(f"Sync failed for manager {pin_code}: {e}")

        finally:
            session.close()

        return result

    def _get_or_create_manager(self, session, pin_code: str) -> Manager:
        """Получить или создать менеджера"""
        manager = session.query(Manager).filter_by(pin_code=pin_code).first()

        if not manager:
            manager = Manager(
                pin_code=pin_code,
                name=f"Менеджер {pin_code}",
                status="ACTIVE"
            )
            session.add(manager)
            session.commit()
            print(f"Created new manager: {pin_code}")

        return manager

    def _process_file(self, session, manager: Manager, file_path: Path, result: Dict):
        """Обработать один файл"""
        data = self.webdav.read_json_file(file_path)
        if not data:
            raise ValueError(f"Failed to read JSON from {file_path}")

        file_name = file_path.name

        # Определяем тип файла и обрабатываем
        if file_name.startswith("orders_"):
            self._process_orders(session, manager, data, result)
        elif file_name.startswith("clients_"):
            self._process_clients(session, manager, data, result)
        elif file_name.startswith("payments_"):
            self._process_payments(session, data, result)
        elif file_name.startswith("sync_ack_"):
            self._process_sync_ack(session, manager, data)
        else:
            print(f"Unknown file type: {file_name}")
            return

        # Перемещаем обработанный файл в processed
        self.webdav.move_to_processed(file_path, manager.pin_code)

    def _process_orders(self, session, manager: Manager, data: Dict, result: Dict):
        """Обработать файл с заказами"""
        orders_data = data.get("orders", [])

        for order_data in orders_data:
            try:
                # Проверяем существование заказа
                existing_order = session.query(Order).filter_by(
                    external_id=order_data["id"]
                ).first()

                if existing_order:
                    # Разрешаем конфликт
                    if self.resolver.should_update_order(existing_order, order_data):
                        self._update_order(session, existing_order, order_data)
                else:
                    # Создаем новый заказ
                    self._create_order(session, manager, order_data)

                result["orders_processed"] += 1

                # Коммитим после каждого заказа, чтобы избежать накопления ошибок
                session.commit()

            except Exception as e:
                # Откатываем транзакцию и очищаем сессию
                session.rollback()
                error_msg = f"Error processing order {order_data.get('id')}: {str(e)}"
                result["errors"].append(error_msg)
                print(error_msg)

    def _create_order(self, session, manager: Manager, order_data: Dict):
        """Создать новый заказ"""
        # Получаем или создаем клиента
        client = self._get_or_create_client(session, order_data)

        # Получаем или создаем адрес
        address = None
        if order_data.get("address_latitude") and order_data.get("address_longitude"):
            address = self._get_or_create_address(session, client, order_data)

        # Создаем заказ
        order = Order(
            external_id=order_data["id"],
            order_number=order_data["order_number"],
            manager_id=manager.id,
            client_id=client.id,
            address_id=address.id if address else None,
            address_text=order_data["address_text"],
            address_latitude=order_data.get("address_latitude"),
            address_longitude=order_data.get("address_longitude"),
            delivery_date=datetime.fromtimestamp(order_data["delivery_date"] / 1000),
            delivery_time_slot=order_data.get("delivery_time_slot", ""),
            status=OrderStatus[order_data["status"]],
            payment_status=PaymentStatus[order_data["payment_status"]],
            payment_type=PaymentType[order_data["payment_type"]],
            total_amount=order_data["total_amount"],
            bonus_used=order_data.get("bonus_used", 0.0),
            bonus_earned=order_data.get("bonus_earned", 0.0),
            comment=order_data.get("comment", ""),
            created_at=datetime.fromtimestamp(order_data["created_at"] / 1000),
            updated_at=datetime.fromtimestamp(order_data["updated_at"] / 1000)
        )
        session.add(order)
        session.flush()  # Получаем ID заказа

        # Создаем позиции заказа
        for item_data in order_data.get("items", []):
            self._create_order_item(session, order, item_data)

        # Создаем координаты оплаты если есть
        payment_location_data = order_data.get("payment_location")
        if payment_location_data:
            self._create_payment_location(session, order, payment_location_data)

        # Создаем GPS-события доставки если есть
        events_data = order_data.get("events", [])
        for event_data in events_data:
            self._create_delivery_event(session, order, event_data)

        # Обновляем статистику клиента
        self._update_client_stats(session, client, order)

        # Создаем транзакцию бонусов
        if order.bonus_earned > 0:
            self._create_bonus_transaction(
                session, client, order,
                BonusTransactionType.EARNED,
                order.bonus_earned,
                f"Начисление за заказ {order.order_number}"
            )

        if order.bonus_used > 0:
            self._create_bonus_transaction(
                session, client, order,
                BonusTransactionType.SPENT,
                -order.bonus_used,
                f"Списание за заказ {order.order_number}"
            )

    def _update_order(self, session, order: Order, order_data: Dict):
        """Обновить существующий заказ"""
        order.status = OrderStatus[order_data["status"]]
        order.payment_status = PaymentStatus[order_data["payment_status"]]
        order.payment_type = PaymentType[order_data["payment_type"]]
        order.updated_at = datetime.fromtimestamp(order_data["updated_at"] / 1000)

        # Обновляем координаты оплаты если есть
        payment_location_data = order_data.get("payment_location")
        if payment_location_data and not order.payment_location:
            self._create_payment_location(session, order, payment_location_data)

    def _get_or_create_client(self, session, order_data: Dict) -> Client:
        """Получить или создать клиента"""
        phone = order_data["client_phone"]
        client = session.query(Client).filter_by(phone=phone).first()

        if not client:
            # Не устанавливаем external_id при создании из заказа,
            # так как он может конфликтовать с клиентами от других менеджеров
            client = Client(
                external_id=None,  # Будет установлен при импорте из clients_*.json
                phone=phone,
                name=order_data.get("client_name", ""),
                bonus_balance=0.0,
                total_orders=0,
                total_spent=0.0
            )
            session.add(client)
            session.flush()

        return client

    def _get_or_create_address(self, session, client: Client, order_data: Dict) -> Address:
        """Получить или создать адрес"""
        address_text = order_data["address_text"]
        latitude = order_data.get("address_latitude")
        longitude = order_data.get("address_longitude")
        external_id = order_data.get("address_id")

        # Сначала ищем по external_id (если указан)
        address = None
        if external_id:
            address = session.query(Address).filter_by(external_id=external_id).first()
            # Если нашли адрес по external_id, обновляем его привязку к текущему клиенту
            if address:
                address.client_id = client.id
                address.address_text = address_text
                address.latitude = latitude
                address.longitude = longitude
                return address

        # Если не нашли по external_id, ищем по клиенту и тексту адреса
        address = session.query(Address).filter_by(
            client_id=client.id,
            address_text=address_text
        ).first()

        if not address:
            # Создаем новый адрес
            address = Address(
                external_id=external_id,
                client_id=client.id,
                address_text=address_text,
                latitude=latitude,
                longitude=longitude,
                is_default=False
            )
            session.add(address)
            session.flush()

        return address

    def _create_order_item(self, session, order: Order, item_data: Dict):
        """Создать позицию заказа"""
        # Ищем товар по external_id
        product = None
        if item_data.get("product_id"):
            product = session.query(Product).filter_by(
                external_id=item_data["product_id"]
            ).first()

        item = OrderItem(
            order_id=order.id,
            product_id=product.id if product else None,
            product_external_id=item_data.get("product_id"),
            product_name=item_data["product_name"],
            quantity=item_data["quantity"],
            price_at_moment=item_data["price_at_moment"],
            sum=item_data["sum"]
        )
        session.add(item)

    def _create_payment_location(self, session, order: Order, location_data: Dict):
        """Создать координаты оплаты"""
        payment_location = PaymentLocation(
            order_id=order.id,
            latitude=location_data["latitude"],
            longitude=location_data["longitude"],
            accuracy=location_data.get("accuracy"),
            altitude=location_data.get("altitude"),
            speed=location_data.get("speed"),
            timestamp=datetime.fromtimestamp(location_data["timestamp"] / 1000)
        )
        session.add(payment_location)

    def _create_delivery_event(self, session, order: Order, event_data: Dict):
        """Создать GPS-событие доставки"""
        from ..database.models import DeliveryEvent, DeliveryEventType

        delivery_event = DeliveryEvent(
            order_id=order.id,
            event_type=DeliveryEventType[event_data["type"].upper()],
            latitude=event_data["latitude"],
            longitude=event_data["longitude"],
            accuracy=event_data.get("accuracy"),
            timestamp=datetime.fromtimestamp(event_data["timestamp"] / 1000)
        )
        session.add(delivery_event)

    def _update_client_stats(self, session, client: Client, order: Order):
        """Обновить статистику клиента"""
        client.total_orders += 1
        client.total_spent += order.total_amount
        client.last_order_date = order.created_at

    def _create_bonus_transaction(self, session, client: Client, order: Order,
                                   trans_type: BonusTransactionType, amount: float, description: str):
        """Создать транзакцию бонусов"""
        balance_before = client.bonus_balance
        client.bonus_balance += amount
        balance_after = client.bonus_balance

        transaction = BonusTransaction(
            client_id=client.id,
            order_id=order.id,
            type=trans_type,
            amount=abs(amount),
            balance_before=balance_before,
            balance_after=balance_after,
            description=description
        )
        session.add(transaction)

    def _process_clients(self, session, manager: Manager, data: Dict, result: Dict):
        """Обработать файл с клиентами"""
        clients_data = data.get("clients", [])

        for client_data in clients_data:
            try:
                phone = client_data["phone"]
                external_id = f"{manager.pin_code}-{client_data['id']}"

                # Ищем клиента по телефону ИЛИ по external_id
                client = session.query(Client).filter(
                    (Client.phone == phone) | (Client.external_id == external_id)
                ).first()

                if client:
                    # Обновляем существующего клиента
                    if self.resolver.should_update_client(client, client_data):
                        client.name = client_data.get("name", client.name)
                        client.notes = client_data.get("notes", client.notes)
                        client.updated_at = datetime.fromtimestamp(client_data["updated_at"] / 1000)
                        # Обновляем external_id только если он не установлен или отличается
                        if not client.external_id or client.external_id != external_id:
                            # Проверяем, не занят ли уже этот external_id другим клиентом
                            existing_with_id = session.query(Client).filter_by(external_id=external_id).first()
                            if not existing_with_id or existing_with_id.id == client.id:
                                client.external_id = external_id
                else:
                    # Создаем нового клиента
                    # Делаем external_id уникальным: PIN-CLIENT_ID
                    client = Client(
                        external_id=external_id,
                        phone=phone,
                        name=client_data.get("name", ""),
                        bonus_balance=client_data.get("bonus_balance", 0.0),
                        notes=client_data.get("notes", ""),
                        created_at=datetime.fromtimestamp(client_data["created_at"] / 1000),
                        updated_at=datetime.fromtimestamp(client_data["updated_at"] / 1000)
                    )
                    session.add(client)
                    session.flush()

                # Обрабатываем адреса
                for address_data in client_data.get("addresses", []):
                    self._process_address(session, client, address_data)

                result["clients_processed"] += 1

                # Коммитим после каждого клиента, чтобы избежать накопления ошибок
                session.commit()

            except Exception as e:
                # Откатываем транзакцию и очищаем сессию
                session.rollback()
                error_msg = f"Error processing client {client_data.get('phone')}: {str(e)}"
                result["errors"].append(error_msg)
                print(error_msg)

    def _process_address(self, session, client: Client, address_data: Dict):
        """Обработать адрес клиента"""
        # Ищем существующий адрес по external_id
        address = session.query(Address).filter_by(
            external_id=address_data["id"]
        ).first()

        if address:
            # Обновляем существующий адрес и привязываем к текущему клиенту
            address.client_id = client.id
            address.address_text = address_data["address_text"]
            address.street = address_data.get("street")
            address.house = address_data.get("house")
            address.apartment = address_data.get("apartment")
            address.latitude = address_data.get("latitude")
            address.longitude = address_data.get("longitude")
            address.is_default = address_data.get("is_default", False)
            address.label = address_data.get("label")
            address.updated_at = datetime.fromtimestamp(address_data["updated_at"] / 1000)
        else:
            # Создаем новый адрес
            address = Address(
                external_id=address_data["id"],
                client_id=client.id,
                address_text=address_data["address_text"],
                street=address_data.get("street"),
                house=address_data.get("house"),
                apartment=address_data.get("apartment"),
                latitude=address_data.get("latitude"),
                longitude=address_data.get("longitude"),
                is_default=address_data.get("is_default", False),
                label=address_data.get("label"),
                created_at=datetime.fromtimestamp(address_data["created_at"] / 1000),
                updated_at=datetime.fromtimestamp(address_data["updated_at"] / 1000)
            )
            session.add(address)

    def _process_payments(self, session, data: Dict, result: Dict):
        """Обработать файл с координатами оплат"""
        payments_data = data.get("payments", [])

        for payment_data in payments_data:
            try:
                order = session.query(Order).filter_by(
                    external_id=payment_data["order_id"]
                ).first()

                if order and not order.payment_location:
                    location_data = payment_data["location"]
                    self._create_payment_location(session, order, {
                        **location_data,
                        "timestamp": payment_data["timestamp"]
                    })

                result["payments_processed"] += 1

                # Коммитим после каждой оплаты
                session.commit()

            except Exception as e:
                # Откатываем транзакцию и очищаем сессию
                session.rollback()
                error_msg = f"Error processing payment for order {payment_data.get('order_id')}: {str(e)}"
                result["errors"].append(error_msg)
                print(error_msg)

    def _process_sync_ack(self, session, manager: Manager, data: Dict):
        """Обработать подтверждение синхронизации"""
        # Просто логируем что менеджер получил данные
        print(f"Manager {manager.pin_code} acknowledged sync: {data.get('acknowledged')}")

    def _generate_incoming_files(self, session, pin_code: str):
        """Генерировать файлы для incoming"""
        # Генерируем products.json
        products = session.query(Product).filter_by(is_active=True).all()
        products_data = [
            {
                "id": p.external_id,
                "name": p.name,
                "category": p.category,
                "price": p.price,
                "unit": p.unit,
                "image_url": p.image_url,
                "is_active": p.is_active,
                "barcode": p.barcode,
                "description": p.description,
                "updated_at": int(p.updated_at.timestamp() * 1000)
            }
            for p in products
        ]
        self.webdav.create_products_file(pin_code, products_data)

        # Генерируем settings.json
        from database.models import Settings
        settings_records = session.query(Settings).all()
        settings_dict = {s.key: s.value for s in settings_records}

        settings_data = {
            "bonus_settings": {
                "enabled": settings_dict.get("bonus_enabled", "true") == "true",
                "earn_percentage": float(settings_dict.get("bonus_earn_percentage", "5.0")),
                "min_order_amount": float(settings_dict.get("bonus_min_order_amount", "500.0")),
                "max_bonus_per_order": float(settings_dict.get("bonus_max_per_order", "1000.0")),
                "expiry_days": int(settings_dict.get("bonus_expiry_days", "365"))
            },
            "delivery_settings": {
                "default_time_slots": ["10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"],
                "min_order_amount": float(settings_dict.get("delivery_min_amount", "300.0"))
            },
            "sync_settings": {
                "sync_interval_minutes": int(settings_dict.get("sync_interval_minutes", "10")),
                "keep_orders_days": int(settings_dict.get("keep_orders_days", "1")),
                "auto_cleanup": settings_dict.get("auto_cleanup", "true") == "true"
            }
        }
        self.webdav.create_settings_file(pin_code, settings_data)

        # Генерируем sync_metadata.json
        metadata = {
            "last_sync": {
                "products": int(datetime.utcnow().timestamp() * 1000),
                "settings": int(datetime.utcnow().timestamp() * 1000),
                "orders_processed": int(datetime.utcnow().timestamp() * 1000)
            },
            "server_info": {
                "version": "1.0.0",
                "timezone": "Europe/Moscow"
            }
        }
        self.webdav.create_sync_metadata_file(pin_code, metadata)

    def _log_sync(self, session, manager: Manager, result: Dict):
        """Логировать синхронизацию"""
        duration = (result["completed_at"] - result["started_at"]).total_seconds()

        log = SyncLog(
            manager_id=manager.id,
            sync_type="upload",
            status="success" if result["success"] else "error",
            records_processed=result["orders_processed"] + result["clients_processed"] + result["payments_processed"],
            records_failed=len(result["errors"]),
            error_message="\n".join(result["errors"]) if result["errors"] else None,
            started_at=result["started_at"],
            completed_at=result["completed_at"],
            duration_seconds=duration
        )
        session.add(log)
        session.commit()

    def generate_products_json(self, output_path: str):
        """
        Генерировать products.json для выгрузки на устройства

        Args:
            output_path: Путь для сохранения файла
        """
        session = self.Session()
        try:
            products = session.query(Product).filter_by(is_active=True).all()
            products_data = {
                "products": [
                    {
                        "id": p.external_id or f"PROD-{p.id}",
                        "name": p.name,
                        "category": p.category or "",
                        "price": float(p.price),
                        "unit": p.unit or "шт",
                        # Используем относительный путь для WebDAV
                        "image_url": self._get_relative_image_path(p.image_url) if p.image_url else "",
                        "is_active": p.is_active,
                        "barcode": p.barcode or "",
                        "description": p.description or "",
                        "updated_at": int(p.updated_at.timestamp() * 1000) if isinstance(p.updated_at, datetime) else p.updated_at
                    }
                    for p in products
                ],
                "generated_at": int(datetime.utcnow().timestamp() * 1000)
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(products_data, f, ensure_ascii=False, indent=2)

        finally:
            session.close()

    def _get_relative_image_path(self, image_url: str) -> str:
        """
        Получить относительный путь к изображению для WebDAV

        Args:
            image_url: Полный путь к изображению

        Returns:
            Относительный путь типа images/PROD-123.jpg
        """
        if not image_url:
            return ""

        # Извлекаем имя файла из полного пути
        image_path = Path(image_url)
        # Проверяем существование файла или просто возвращаем имя
        if image_path.exists() or image_path.name:
            return f"images/{image_path.name}"

        return ""

    def copy_product_images(self, manager_pin: str) -> int:
        """
        Копировать изображения товаров в папку менеджера

        Args:
            manager_pin: PIN-код менеджера

        Returns:
            Количество скопированных изображений
        """
        session = self.Session()
        copied_count = 0

        try:
            products = session.query(Product).filter_by(is_active=True).all()

            # Создаем папку для изображений
            images_dir = Path(f"data/webdav/{manager_pin}/incoming/images")
            images_dir.mkdir(parents=True, exist_ok=True)

            for product in products:
                # Используем image_path (абсолютный путь) вместо image_url
                image_source = product.image_path or product.image_url
                if image_source:
                    source_path = Path(image_source)

                    # Копируем основное изображение
                    if source_path.exists():
                        dest_path = images_dir / source_path.name

                        import shutil
                        shutil.copy2(source_path, dest_path)
                        copied_count += 1

                        # Копируем миниатюру если есть
                        thumb_path = Path(str(source_path).replace('.jpg', '_thumb.jpg').replace('.jpeg', '_thumb.jpeg').replace('.png', '_thumb.png'))
                        if thumb_path.exists():
                            thumb_dest = images_dir / thumb_path.name
                            shutil.copy2(thumb_path, thumb_dest)
                            copied_count += 1

            return copied_count

        finally:
            session.close()

    def generate_settings_json(self, output_path: str):
        """
        Генерировать settings.json для выгрузки на устройства

        Args:
            output_path: Путь для сохранения файла
        """
        session = self.Session()
        try:
            from database.models import Settings
            settings_records = session.query(Settings).all()
            settings_dict = {s.key: s.value for s in settings_records}

            settings_data = {
                "bonus_settings": {
                    "enabled": settings_dict.get("bonus_enabled", "true") == "true",
                    "earn_percentage": float(settings_dict.get("bonus_earn_percentage", "5.0")),
                    "min_order_amount": float(settings_dict.get("bonus_min_order_amount", "500.0")),
                    "max_bonus_per_order": float(settings_dict.get("bonus_max_per_order", "1000.0")),
                    "expiry_days": int(settings_dict.get("bonus_expiry_days", "365"))
                },
                "delivery_settings": {
                    "default_time_slots": ["10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"],
                    "min_order_amount": float(settings_dict.get("delivery_min_amount", "300.0"))
                },
                "sync_settings": {
                    "sync_interval_minutes": int(settings_dict.get("sync_interval_minutes", "10")),
                    "keep_orders_days": int(settings_dict.get("keep_orders_days", "1")),
                    "auto_cleanup": settings_dict.get("auto_cleanup", "true") == "true"
                },
                "generated_at": int(datetime.utcnow().timestamp() * 1000)
            }

            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(settings_data, f, ensure_ascii=False, indent=2)

        finally:
            session.close()

    def process_json_file(self, file_path: str, manager_pin: str):
        """
        Обработать JSON файл от менеджера (orders, clients, payments)

        Args:
            file_path: Путь к JSON файлу
            manager_pin: PIN-код менеджера
        """
        session = self.Session()
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Получаем или создаем менеджера
            manager = self._get_or_create_manager(session, manager_pin)

            result = {
                "orders_processed": 0,
                "clients_processed": 0,
                "payments_processed": 0,
                "errors": []
            }

            # Определяем тип файла по содержимому
            if "orders" in data:
                self._process_orders(session, manager, data, result)
            elif "clients" in data:
                self._process_clients(session, manager, data, result)
            elif "payments" in data:
                self._process_payments(session, data, result)

            session.commit()

        except Exception as e:
            session.rollback()
            raise Exception(f"Ошибка обработки файла {file_path}: {str(e)}")
        finally:
            session.close()


if __name__ == "__main__":
    # Тест синхронизации
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    from database.database import init_database

    # Инициализируем БД
    init_database()

    # Создаем менеджер синхронизации
    sync_manager = SyncManager("../../webdav_root")

    # Синхронизируем всех менеджеров
    results = sync_manager.sync_all_managers()

    print("\nSync results:")
    for pin_code, result in results.items():
        print(f"\nManager {pin_code}:")
        print(f"  Orders: {result['orders_processed']}")
        print(f"  Clients: {result['clients_processed']}")
        print(f"  Payments: {result['payments_processed']}")
        print(f"  Errors: {len(result['errors'])}")
