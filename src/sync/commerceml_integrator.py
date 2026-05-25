"""
Интегратор CommerceML для импорта данных из 1С в базу данных
"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict
import logging
import os
from pathlib import Path

from database.models import Product, Client, Order, OrderItem, Address, OrderStatus, PaymentStatus
from sync.commerceml_parser import CommerceMLParser

logger = logging.getLogger(__name__)


class CommerceMLIntegrator:
    """Интегратор для импорта данных из CommerceML в БД"""

    def __init__(self, db_engine):
        """
        Args:
            db_engine: SQLAlchemy engine
        """
        self.engine = db_engine

    def import_from_1c(self, import_xml_path: str, offers_xml_path: str = None) -> Dict:
        """
        Импорт товаров из 1С

        Args:
            import_xml_path: Путь к import.xml (товары и категории) или директория с import*.xml файлами
            offers_xml_path: Путь к offers.xml (цены и остатки) или директория с offers*.xml файлами

        Returns:
            Dict со статистикой импорта
        """
        stats = {
            'products_created': 0,
            'products_updated': 0,
            'errors': []
        }

        try:
            # Определяем, это файл или директория
            import_path = Path(import_xml_path)

            if import_path.is_dir():
                # Директория - парсим все import*.xml файлы
                logger.info(f"Parsing multiple import files from directory: {import_xml_path}")
                import_data = CommerceMLParser.parse_import_files(str(import_path), "import*.xml")
                base_dir = str(import_path)
            elif import_path.is_file():
                # Один файл - парсим его
                logger.info(f"Parsing single import file: {import_xml_path}")
                import_data = CommerceMLParser.parse_import_xml(import_xml_path)
                base_dir = os.path.dirname(import_xml_path)
            else:
                raise FileNotFoundError(f"Path not found: {import_xml_path}")

            products_data = import_data['products']

            # Парсим offers.xml если есть
            offers_data = {}
            if offers_xml_path:
                offers_path = Path(offers_xml_path)

                if offers_path.is_dir():
                    # Директория - парсим все offers*.xml файлы
                    logger.info(f"Parsing multiple offers files from directory: {offers_xml_path}")
                    offers_list = CommerceMLParser.parse_offers_files(str(offers_path), "offers*.xml")
                elif offers_path.is_file():
                    # Один файл - парсим его
                    logger.info(f"Parsing single offers file: {offers_xml_path}")
                    offers_list = CommerceMLParser.parse_offers_xml(offers_xml_path)
                else:
                    logger.warning(f"Offers path not found: {offers_xml_path}")
                    offers_list = []

                offers_data = {offer['product_id']: offer for offer in offers_list}

            # Импортируем категории в БД
            categories_data = import_data.get('categories', [])
            category_map = {}  # Маппинг external_id -> db_id

            with Session(self.engine) as session:
                from database.models import Category

                logger.info(f"Importing {len(categories_data)} categories...")

                for cat_data in categories_data:
                    try:
                        # Ищем существующую категорию по external_id
                        existing_cat = session.query(Category).filter(
                            Category.external_id == cat_data['id']
                        ).first()

                        if existing_cat:
                            # Обновляем существующую категорию
                            existing_cat.name = cat_data['name']
                            existing_cat.updated_at = datetime.utcnow()
                            category_map[cat_data['id']] = existing_cat.id
                        else:
                            # Создаем новую категорию (пока без parent_id)
                            new_cat = Category(
                                external_id=cat_data['id'],
                                name=cat_data['name']
                            )
                            session.add(new_cat)
                            session.flush()  # Получаем ID
                            category_map[cat_data['id']] = new_cat.id

                    except Exception as e:
                        logger.error(f"Error importing category {cat_data.get('id')}: {e}")

                # Второй проход - устанавливаем parent_id
                for cat_data in categories_data:
                    if cat_data.get('parent_id'):
                        parent_db_id = category_map.get(cat_data['parent_id'])
                        if parent_db_id:
                            cat = session.query(Category).filter(
                                Category.external_id == cat_data['id']
                            ).first()
                            if cat:
                                cat.parent_id = parent_db_id

                session.commit()
                logger.info(f"Categories imported: {len(category_map)}")

            # Импортируем товары
            with Session(self.engine) as session:
                for product_data in products_data:
                    try:
                        # Ищем существующий товар по external_id (1C ID)
                        existing_product = session.query(Product).filter(
                            Product.external_id == product_data['id']
                        ).first()

                        # Получаем цену из offers
                        offer = offers_data.get(product_data['id'])
                        price = offer['price'] if offer else 0.0
                        is_active = offer['is_active'] if offer else True

                        # Преобразуем относительный путь к изображению в абсолютный
                        image_url = product_data['image_url']
                        image_path = None
                        if image_url and not os.path.isabs(image_url):
                            image_path = os.path.join(base_dir, image_url).replace('\\', '/')
                            image_url = image_path  # Для обратной совместимости

                        # Получаем category_id из маппинга
                        category_db_id = category_map.get(product_data['category_id']) if product_data.get('category_id') else None

                        if existing_product:
                            # Обновляем существующий товар
                            existing_product.name = product_data['name']
                            existing_product.category = self._get_category_name(
                                product_data['category_id'],
                                import_data['categories']
                            )
                            existing_product.category_id = category_db_id  # Новая связь
                            existing_product.price = price
                            existing_product.unit = product_data['unit']
                            existing_product.article = product_data['article']
                            existing_product.barcode = product_data['barcode']
                            existing_product.image_url = image_url
                            existing_product.image_path = image_path
                            existing_product.is_active = is_active
                            existing_product.updated_at = datetime.utcnow()

                            stats['products_updated'] += 1
                        else:
                            # Создаем новый товар
                            new_product = Product(
                                external_id=product_data['id'],
                                name=product_data['name'],
                                category=self._get_category_name(
                                    product_data['category_id'],
                                    import_data['categories']
                                ),
                                category_id=category_db_id,  # Новая связь
                                price=price,
                                unit=product_data['unit'],
                                article=product_data['article'],
                                barcode=product_data['barcode'],
                                image_url=image_url,
                                image_path=image_path,
                                is_active=is_active
                            )
                            session.add(new_product)
                            stats['products_created'] += 1

                    except Exception as e:
                        error_msg = f"Error importing product {product_data.get('id')}: {str(e)}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)

                session.commit()

            logger.info(
                f"Import completed: {stats['products_created']} created, "
                f"{stats['products_updated']} updated, {len(stats['errors'])} errors"
            )

        except Exception as e:
            error_msg = f"Fatal error during import: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)

        return stats

    def import_orders_from_1c(self, orders_xml_path: str) -> Dict:
        """
        Импорт заказов из 1С

        Args:
            orders_xml_path: Путь к orders.xml

        Returns:
            Dict со статистикой импорта
        """
        stats = {
            'orders_created': 0,
            'orders_updated': 0,
            'errors': []
        }

        try:
            # Парсим orders.xml
            orders_data = CommerceMLParser.parse_orders_xml(orders_xml_path)

            with Session(self.engine) as session:
                for order_data in orders_data:
                    try:
                        # Ищем существующий заказ по external_id (1C ID)
                        existing_order = session.query(Order).filter(
                            Order.external_id == order_data['id']
                        ).first()

                        if existing_order:
                            # Обновляем существующий заказ
                            # (обычно только статус, т.к. заказы создаются в мобильном приложении)
                            stats['orders_updated'] += 1
                        else:
                            # Создаем новый заказ (редкий случай - заказ создан в 1С)
                            # Ищем или создаем клиента
                            client = self._get_or_create_client(
                                session,
                                order_data['client_id'],
                                order_data['client_name']
                            )

                            # Создаем заказ
                            new_order = Order(
                                external_id=order_data['id'],
                                order_number=order_data['number'],
                                client_id=client.id,
                                client_name=client.name,
                                client_phone=client.phone,
                                address_text="Адрес не указан",
                                delivery_date=datetime.fromisoformat(order_data['date']),
                                total_amount=order_data['total'],
                                status=OrderStatus.NEW,
                                payment_status=PaymentStatus.UNPAID
                            )
                            session.add(new_order)
                            session.flush()  # Получаем ID заказа

                            # Создаем позиции заказа
                            for item_data in order_data['items']:
                                # Ищем товар по external_id
                                product = session.query(Product).filter(
                                    Product.external_id == item_data['product_id']
                                ).first()

                                if product:
                                    order_item = OrderItem(
                                        order_id=new_order.id,
                                        product_id=product.id,
                                        product_name=product.name,
                                        quantity=item_data['quantity'],
                                        unit_price=item_data['price']
                                    )
                                    session.add(order_item)

                            stats['orders_created'] += 1

                    except Exception as e:
                        error_msg = f"Error importing order {order_data.get('id')}: {str(e)}"
                        logger.error(error_msg)
                        stats['errors'].append(error_msg)

                session.commit()

            logger.info(
                f"Orders import completed: {stats['orders_created']} created, "
                f"{stats['orders_updated']} updated, {len(stats['errors'])} errors"
            )

        except Exception as e:
            error_msg = f"Fatal error during orders import: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)

        return stats

    def export_orders_to_1c(self, output_path: str, date_from: datetime = None) -> int:
        """
        Экспорт заказов в формате CommerceML для 1С

        Args:
            output_path: Путь для сохранения orders.xml
            date_from: Экспортировать заказы начиная с этой даты

        Returns:
            Количество экспортированных заказов
        """
        try:
            with Session(self.engine) as session:
                # Получаем заказы для экспорта
                query = session.query(Order)
                if date_from:
                    query = query.filter(Order.created_at >= date_from)

                orders = query.all()

                # Формируем данные для XML
                orders_data = []
                for order in orders:
                    # Получаем позиции заказа
                    items = session.query(OrderItem).filter(
                        OrderItem.order_id == order.id
                    ).all()

                    order_data = {
                        'id': order.external_id or f"ORD-{order.id}",
                        'number': order.order_number,
                        'date': order.created_at.isoformat() if isinstance(order.created_at, datetime) else datetime.fromtimestamp(order.created_at / 1000).isoformat(),
                        'client_id': order.client_id,
                        'client_name': order.client.name if order.client else 'Неизвестный клиент',
                        'client_phone': order.client.phone if order.client else '',
                        'address': order.address_text,
                        'delivery_date': order.delivery_date.isoformat() if order.delivery_date else '',
                        'delivery_time_slot': order.delivery_time_slot or '',
                        'status': order.status.value if order.status else 'new',
                        'payment_status': order.payment_status.value if order.payment_status else 'unpaid',
                        'payment_type': order.payment_type.value if order.payment_type else 'cash',
                        'comment': order.comment or '',
                        'bonus_used': order.bonus_used,
                        'total': order.total_amount,
                        'items': []
                    }

                    for item in items:
                        # Получаем external_id товара и единицу измерения
                        product_external_id = item.product_external_id
                        product_unit = 'шт'
                        product_unit_code = '796'

                        # Если нет product_external_id, пытаемся получить из Product
                        if not product_external_id and item.product_id:
                            product = session.query(Product).filter(
                                Product.id == item.product_id
                            ).first()
                            if product:
                                product_external_id = product.external_id
                                product_unit = product.unit or 'шт'

                        order_data['items'].append({
                            'product_id': product_external_id or f"PROD-{item.product_id}",
                            'name': item.product_name,
                            'quantity': item.quantity,
                            'price': item.price_at_moment,
                            'total': item.sum,
                            'unit': product_unit,
                            'unit_code': product_unit_code
                        })

                    orders_data.append(order_data)

                # Генерируем XML
                CommerceMLParser.generate_orders_xml(orders_data, output_path)

                logger.info(f"Exported {len(orders_data)} orders to {output_path}")
                return len(orders_data)

        except Exception as e:
            logger.error(f"Error exporting orders to 1C: {e}")
            raise

    def _get_category_name(self, category_id: str, categories: List[Dict]) -> str:
        """Получить название категории по ID"""
        if not category_id:
            return None

        for category in categories:
            if category['id'] == category_id:
                return category['name']

        return None

    def _get_or_create_client(self, session: Session, client_id: str, client_name: str) -> Client:
        """Получить или создать клиента"""
        # Ищем по external_id
        client = session.query(Client).filter(
            Client.external_id == client_id
        ).first()

        if not client:
            # Создаем нового клиента
            client = Client(
                external_id=client_id,
                name=client_name,
                phone="",  # Телефон неизвестен
                bonus_balance=0.0,
                total_orders=0,
                total_spent=0.0
            )
            session.add(client)
            session.flush()

        return client
