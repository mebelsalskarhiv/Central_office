"""
Утилиты для работы с настройками GUI
"""
from PyQt6.QtCore import QSettings


class TableSettings:
    """Класс для сохранения и восстановления настроек таблиц"""

    def __init__(self, table_name: str):
        """
        Args:
            table_name: Уникальное имя таблицы для сохранения настроек
        """
        self.settings = QSettings("OrderManager", "CentralOffice")
        self.table_name = table_name

    def save_column_widths(self, table):
        """
        Сохранить ширину колонок таблицы

        Args:
            table: QTableWidget
        """
        widths = []
        for i in range(table.columnCount()):
            widths.append(table.columnWidth(i))

        self.settings.setValue(f"{self.table_name}/column_widths", widths)

    def restore_column_widths(self, table):
        """
        Восстановить ширину колонок таблицы

        Args:
            table: QTableWidget
        """
        widths = self.settings.value(f"{self.table_name}/column_widths")

        if widths and len(widths) == table.columnCount():
            for i, width in enumerate(widths):
                if isinstance(width, int) and width > 0:
                    table.setColumnWidth(i, width)

    def save_window_geometry(self, window):
        """
        Сохранить геометрию окна

        Args:
            window: QWidget
        """
        self.settings.setValue(f"{self.table_name}/geometry", window.saveGeometry())

    def restore_window_geometry(self, window):
        """
        Восстановить геометрию окна

        Args:
            window: QWidget
        """
        geometry = self.settings.value(f"{self.table_name}/geometry")
        if geometry:
            window.restoreGeometry(geometry)
