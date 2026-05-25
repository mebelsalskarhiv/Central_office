"""
Парсер JSON файлов синхронизации
"""
from typing import Dict, List, Optional
from datetime import datetime
import json


class JSONParser:
    """Парсер для JSON файлов обмена данными"""

    def parse_orders_file(self, data: Dict) -> List[Dict]:
        """
        Парсить файл orders_{timestamp}.json

        Args:
            data: Словарь с данными из JSON

        Returns:
            Список заказов
        """
        self._validate_version(data)
        return data.get("orders", [])

    def parse_clients_file(self, data: Dict) -> List[Dict]:
        """
        Парсить файл clients_{timestamp}.json

        Args:
            data: Словарь с данными из JSON

        Returns:
            Список клиентов
        """
        self._validate_version(data)
        return data.get("clients", [])

    def parse_payments_file(self, data: Dict) -> List[Dict]:
        """
        Парсить файл payments_{timestamp}.json

        Args:
            data: Словарь с данными из JSON

        Returns:
            Список оплат
        """
        self._validate_version(data)
        return data.get("payments", [])

    def parse_products_file(self, data: Dict) -> List[Dict]:
        """
        Парсить файл products.json

        Args:
            data: Словарь с данными из JSON

        Returns:
            Список товаров
        """
        self._validate_version(data)
        return data.get("products", [])

    def parse_settings_file(self, data: Dict) -> Dict:
        """
        Парсить файл settings.json

        Args:
            data: Словарь с данными из JSON

        Returns:
            Словарь с настройками
        """
        self._validate_version(data)
        return {
            "bonus_settings": data.get("bonus_settings", {}),
            "delivery_settings": data.get("delivery_settings", {}),
            "sync_settings": data.get("sync_settings", {})
        }

    def _validate_version(self, data: Dict):
        """Проверить версию формата"""
        version = data.get("version")
        if version != 1:
            raise ValueError(f"Unsupported format version: {version}")

    def validate_order(self, order_data: Dict) -> bool:
        """
        Валидировать данные заказа

        Args:
            order_data: Данные заказа

        Returns:
            True если валидны
        """
        required_fields = [
            "id", "order_number", "client_phone", "address_text",
            "delivery_date", "status", "payment_status", "payment_type",
            "total_amount", "items", "created_at", "updated_at"
        ]

        for field in required_fields:
            if field not in order_data:
                raise ValueError(f"Missing required field: {field}")

        # Проверяем позиции заказа
        items = order_data.get("items", [])
        if not items:
            raise ValueError("Order must have at least one item")

        for item in items:
            self.validate_order_item(item)

        return True

    def validate_order_item(self, item_data: Dict) -> bool:
        """Валидировать позицию заказа"""
        required_fields = ["product_name", "quantity", "price_at_moment", "sum"]

        for field in required_fields:
            if field not in item_data:
                raise ValueError(f"Missing required field in order item: {field}")

        return True

    def validate_client(self, client_data: Dict) -> bool:
        """Валидировать данные клиента"""
        required_fields = ["id", "phone", "created_at", "updated_at"]

        for field in required_fields:
            if field not in client_data:
                raise ValueError(f"Missing required field: {field}")

        return True

    def validate_payment(self, payment_data: Dict) -> bool:
        """Валидировать данные оплаты"""
        required_fields = ["order_id", "amount", "payment_type", "location", "timestamp"]

        for field in required_fields:
            if field not in payment_data:
                raise ValueError(f"Missing required field: {field}")

        # Проверяем координаты
        location = payment_data.get("location", {})
        if "latitude" not in location or "longitude" not in location:
            raise ValueError("Payment location must have latitude and longitude")

        return True

    def validate_delivery_event(self, event_data: Dict) -> bool:
        """
        Валидировать данные GPS-события доставки

        Args:
            event_data: Данные события

        Returns:
            True если валидны
        """
        required_fields = ["type", "latitude", "longitude", "timestamp"]

        for field in required_fields:
            if field not in event_data:
                raise ValueError(f"Missing required field in delivery event: {field}")

        # Проверяем тип события
        valid_types = ["started", "payment_received", "delivered"]
        if event_data["type"] not in valid_types:
            raise ValueError(f"Invalid event type: {event_data['type']}")

        # Проверяем координаты
        lat = event_data["latitude"]
        lon = event_data["longitude"]
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise ValueError(f"Invalid coordinates: lat={lat}, lon={lon}")

        return True
