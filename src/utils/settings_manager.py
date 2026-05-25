"""
Менеджер настроек приложения
"""
from PyQt6.QtCore import QSettings
import json
from pathlib import Path
from typing import Dict, Any


class SettingsManager:
    """Менеджер настроек приложения"""

    def __init__(self):
        self.settings = QSettings("OrderManager", "CentralOffice")
        self.config_file = Path("config.json")

    # WebDAV настройки
    def get_webdav_url(self) -> str:
        return self.settings.value("webdav/url", "")

    def set_webdav_url(self, url: str):
        self.settings.setValue("webdav/url", url)

    def get_webdav_username(self) -> str:
        return self.settings.value("webdav/username", "")

    def set_webdav_username(self, username: str):
        self.settings.setValue("webdav/username", username)

    def get_webdav_password(self) -> str:
        return self.settings.value("webdav/password", "")

    def set_webdav_password(self, password: str):
        self.settings.setValue("webdav/password", password)

    def get_webdav_enabled(self) -> bool:
        return self.settings.value("webdav/enabled", False, type=bool)

    def set_webdav_enabled(self, enabled: bool):
        self.settings.setValue("webdav/enabled", enabled)

    # Настройки синхронизации
    def get_sync_interval(self) -> int:
        """Интервал автосинхронизации в минутах"""
        return self.settings.value("sync/interval", 5, type=int)

    def set_sync_interval(self, minutes: int):
        self.settings.setValue("sync/interval", minutes)

    def get_sync_enabled(self) -> bool:
        return self.settings.value("sync/enabled", True, type=bool)

    def set_sync_enabled(self, enabled: bool):
        self.settings.setValue("sync/enabled", enabled)

    # Настройки бонусной системы
    def get_bonus_percentage(self) -> float:
        """Процент начисления бонусов от суммы заказа"""
        return self.settings.value("bonus/percentage", 5.0, type=float)

    def set_bonus_percentage(self, percentage: float):
        self.settings.setValue("bonus/percentage", percentage)

    def get_bonus_max_payment_percentage(self) -> float:
        """Максимальный процент оплаты бонусами"""
        return self.settings.value("bonus/max_payment_percentage", 50.0, type=float)

    def set_bonus_max_payment_percentage(self, percentage: float):
        self.settings.setValue("bonus/max_payment_percentage", percentage)

    def get_bonus_expiry_days(self) -> int:
        """Срок действия бонусов в днях (0 = бессрочно)"""
        return self.settings.value("bonus/expiry_days", 365, type=int)

    def set_bonus_expiry_days(self, days: int):
        self.settings.setValue("bonus/expiry_days", days)

    def get_bonus_enabled(self) -> bool:
        return self.settings.value("bonus/enabled", True, type=bool)

    def set_bonus_enabled(self, enabled: bool):
        self.settings.setValue("bonus/enabled", enabled)

    # Настройки CommerceML
    def get_commerceml_import_path(self) -> str:
        """Путь к папке импорта из 1С"""
        return self.settings.value("commerceml/import_path", "")

    def set_commerceml_import_path(self, path: str):
        self.settings.setValue("commerceml/import_path", path)

    def get_commerceml_export_path(self) -> str:
        """Путь к папке экспорта в 1С"""
        return self.settings.value("commerceml/export_path", "")

    def set_commerceml_export_path(self, path: str):
        self.settings.setValue("commerceml/export_path", path)

    def get_commerceml_auto_import(self) -> bool:
        """Автоматический импорт товаров из 1С"""
        return self.settings.value("commerceml/auto_import", False, type=bool)

    def set_commerceml_auto_import(self, enabled: bool):
        self.settings.setValue("commerceml/auto_import", enabled)

    def get_commerceml_auto_export(self) -> bool:
        """Автоматический экспорт заказов в 1С"""
        return self.settings.value("commerceml/auto_export", False, type=bool)

    def set_commerceml_auto_export(self, enabled: bool):
        self.settings.setValue("commerceml/auto_export", enabled)

    # Общие методы
    def get_all_settings(self) -> Dict[str, Any]:
        """Получить все настройки"""
        return {
            "webdav": {
                "url": self.get_webdav_url(),
                "username": self.get_webdav_username(),
                "enabled": self.get_webdav_enabled()
            },
            "sync": {
                "interval": self.get_sync_interval(),
                "enabled": self.get_sync_enabled()
            },
            "bonus": {
                "percentage": self.get_bonus_percentage(),
                "max_payment_percentage": self.get_bonus_max_payment_percentage(),
                "expiry_days": self.get_bonus_expiry_days(),
                "enabled": self.get_bonus_enabled()
            },
            "commerceml": {
                "import_path": self.get_commerceml_import_path(),
                "export_path": self.get_commerceml_export_path(),
                "auto_import": self.get_commerceml_auto_import(),
                "auto_export": self.get_commerceml_auto_export()
            }
        }

    def export_to_json(self, file_path: str = None):
        """Экспорт настроек в JSON"""
        if file_path is None:
            file_path = self.config_file

        settings = self.get_all_settings()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)

    def import_from_json(self, file_path: str = None):
        """Импорт настроек из JSON"""
        if file_path is None:
            file_path = self.config_file

        if not Path(file_path).exists():
            return

        with open(file_path, 'r', encoding='utf-8') as f:
            settings = json.load(f)

        # WebDAV
        if "webdav" in settings:
            self.set_webdav_url(settings["webdav"].get("url", ""))
            self.set_webdav_username(settings["webdav"].get("username", ""))
            self.set_webdav_enabled(settings["webdav"].get("enabled", False))

        # Sync
        if "sync" in settings:
            self.set_sync_interval(settings["sync"].get("interval", 5))
            self.set_sync_enabled(settings["sync"].get("enabled", True))

        # Bonus
        if "bonus" in settings:
            self.set_bonus_percentage(settings["bonus"].get("percentage", 5.0))
            self.set_bonus_max_payment_percentage(settings["bonus"].get("max_payment_percentage", 50.0))
            self.set_bonus_expiry_days(settings["bonus"].get("expiry_days", 365))
            self.set_bonus_enabled(settings["bonus"].get("enabled", True))

        # CommerceML
        if "commerceml" in settings:
            self.set_commerceml_import_path(settings["commerceml"].get("import_path", ""))
            self.set_commerceml_export_path(settings["commerceml"].get("export_path", ""))
            self.set_commerceml_auto_import(settings["commerceml"].get("auto_import", False))
            self.set_commerceml_auto_export(settings["commerceml"].get("auto_export", False))

    def reset_to_defaults(self):
        """Сброс настроек к значениям по умолчанию"""
        self.settings.clear()
