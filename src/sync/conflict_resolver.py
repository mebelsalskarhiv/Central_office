"""
Разрешение конфликтов при синхронизации
Стратегия: Last-Write-Wins по timestamp
"""
from datetime import datetime
from typing import Dict
from database.models import Order, Client


class ConflictResolver:
    """Разрешение конфликтов при синхронизации данных"""

    def should_update_order(self, existing_order: Order, new_data: Dict) -> bool:
        """
        Определить, нужно ли обновлять существующий заказ

        Args:
            existing_order: Существующий заказ в БД
            new_data: Новые данные из JSON

        Returns:
            True если нужно обновить
        """
        # Заказы со статусом DELIVERED не обновляются
        if existing_order.status.value == "DELIVERED":
            return False

        # Сравниваем timestamp
        new_updated_at = datetime.fromtimestamp(new_data["updated_at"] / 1000)

        if new_updated_at > existing_order.updated_at:
            return True

        return False

    def should_update_client(self, existing_client: Client, new_data: Dict) -> bool:
        """
        Определить, нужно ли обновлять существующего клиента

        Args:
            existing_client: Существующий клиент в БД
            new_data: Новые данные из JSON

        Returns:
            True если нужно обновить
        """
        # Сравниваем timestamp
        new_updated_at = datetime.fromtimestamp(new_data["updated_at"] / 1000)

        if new_updated_at > existing_client.updated_at:
            return True

        return False

    def resolve_bonus_conflict(self, db_balance: float, device_balance: float) -> float:
        """
        Разрешить конфликт баланса бонусов

        Args:
            db_balance: Баланс в БД (авторитетный источник)
            device_balance: Баланс на устройстве

        Returns:
            Итоговый баланс (всегда из БД)
        """
        # Баланс бонусов всегда берется из центральной БД
        return db_balance

    def merge_client_data(self, existing_client: Client, new_data: Dict) -> Dict:
        """
        Объединить данные клиента

        Args:
            existing_client: Существующий клиент
            new_data: Новые данные

        Returns:
            Объединенные данные
        """
        merged = {
            "name": new_data.get("name") or existing_client.name,
            "notes": new_data.get("notes") or existing_client.notes,
            "bonus_balance": existing_client.bonus_balance,  # Всегда из БД
            "updated_at": max(
                existing_client.updated_at,
                datetime.fromtimestamp(new_data["updated_at"] / 1000)
            )
        }

        return merged
