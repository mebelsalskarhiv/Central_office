"""
Вкладка менеджеров
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QHeaderView, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database.database import get_database
from database.models import Manager, ManagerStatus, Order, SyncLog
from gui.dialogs.manager_edit_dialog import ManagerEditDialog
from gui.utils.table_settings import TableSettings


class ManagersTab(QWidget):
    """Вкладка менеджеров"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.table_settings = TableSettings("managers_tab")
        self.init_ui()
        self.load_managers()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель фильтров
        filter_layout = QHBoxLayout()

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени, PIN, телефону...")
        self.search_input.textChanged.connect(self.filter_managers)
        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_input)

        # Фильтр по статусу
        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        self.status_filter.addItem("Активные", ManagerStatus.ACTIVE)
        self.status_filter.addItem("Заблокированные", ManagerStatus.BLOCKED)
        self.status_filter.addItem("Неактивные", ManagerStatus.INACTIVE)
        self.status_filter.currentIndexChanged.connect(self.filter_managers)
        filter_layout.addWidget(QLabel("Статус:"))
        filter_layout.addWidget(self.status_filter)

        # Кнопка сброса
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(reset_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Таблица менеджеров
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "PIN", "Имя", "Телефон", "Email", "Статус", "Заказов",
            "Последняя синхронизация", "Устройство", "Версия", "Создан"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_manager)

        # Восстанавливаем ширину колонок
        self.table_settings.restore_column_widths(self.table)

        # Сохраняем ширину при изменении
        self.table.horizontalHeader().sectionResized.connect(self.on_column_resized)

        layout.addWidget(self.table)

        # Панель кнопок
        button_layout = QHBoxLayout()

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_manager)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_manager)
        button_layout.addWidget(edit_btn)

        block_btn = QPushButton("Заблокировать/Разблокировать")
        block_btn.clicked.connect(self.toggle_block)
        button_layout.addWidget(block_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_managers)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        # Статистика
        self.stats_label = QLabel()
        button_layout.addWidget(self.stats_label)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_managers(self):
        """Загрузить менеджеров из БД"""
        with Session(self.db.engine) as session:
            self.all_managers = session.query(Manager).all()

            # Загружаем количество заказов для каждого менеджера
            self.manager_orders_count = {}
            for manager in self.all_managers:
                count = session.query(func.count(Order.id)).filter(
                    Order.manager_id == manager.id
                ).scalar()
                self.manager_orders_count[manager.id] = count

            # Detach from session
            session.expunge_all()

        self.filter_managers()

    def filter_managers(self):
        """Применить фильтры"""
        search_text = self.search_input.text().lower()
        status = self.status_filter.currentData()

        filtered_managers = []

        for manager in self.all_managers:
            # Фильтр по поиску
            if search_text:
                if not (
                    search_text in manager.name.lower() or
                    search_text in manager.pin_code.lower() or
                    search_text in (manager.phone or "").lower()
                ):
                    continue

            # Фильтр по статусу
            if status is not None and manager.status != status:
                continue

            filtered_managers.append(manager)

        self.display_managers(filtered_managers)
        self.update_stats(filtered_managers)

    def display_managers(self, managers):
        """Отобразить менеджеров в таблице"""
        self.table.setRowCount(len(managers))

        for row, manager in enumerate(managers):
            # PIN
            self.table.setItem(row, 0, QTableWidgetItem(manager.pin_code))

            # Имя
            self.table.setItem(row, 1, QTableWidgetItem(manager.name))

            # Телефон
            self.table.setItem(row, 2, QTableWidgetItem(manager.phone or "-"))

            # Email
            self.table.setItem(row, 3, QTableWidgetItem(manager.email or "-"))

            # Статус
            status_item = QTableWidgetItem(self.get_status_text(manager.status))
            status_item.setBackground(QColor(self.get_status_color(manager.status)))
            self.table.setItem(row, 4, status_item)

            # Заказов
            orders_count = self.manager_orders_count.get(manager.id, 0)
            self.table.setItem(row, 5, QTableWidgetItem(str(orders_count)))

            # Последняя синхронизация
            if manager.last_sync_at:
                if isinstance(manager.last_sync_at, datetime):
                    last_sync = manager.last_sync_at
                else:
                    last_sync = datetime.fromtimestamp(manager.last_sync_at / 1000)
                last_sync_str = last_sync.strftime("%d.%m.%Y %H:%M")
            else:
                last_sync_str = "Никогда"
            self.table.setItem(row, 6, QTableWidgetItem(last_sync_str))

            # Устройство
            device = manager.device_model or "-"
            self.table.setItem(row, 7, QTableWidgetItem(device))

            # Версия приложения
            version = manager.app_version or "-"
            self.table.setItem(row, 8, QTableWidgetItem(version))

            # Создан
            if isinstance(manager.created_at, datetime):
                created = manager.created_at
            else:
                created = datetime.fromtimestamp(manager.created_at / 1000)
            created_str = created.strftime("%d.%m.%Y")
            self.table.setItem(row, 9, QTableWidgetItem(created_str))

            # Сохраняем ID менеджера
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, manager.id)

    def update_stats(self, managers):
        """Обновить статистику"""
        total = len(managers)
        active = sum(1 for m in managers if m.status == ManagerStatus.ACTIVE)
        blocked = sum(1 for m in managers if m.status == ManagerStatus.BLOCKED)
        self.stats_label.setText(
            f"Всего менеджеров: {total} | Активных: {active} | Заблокированных: {blocked}"
        )

    def get_status_text(self, status):
        """Получить текст статуса"""
        status_map = {
            ManagerStatus.ACTIVE: "Активен",
            ManagerStatus.BLOCKED: "Заблокирован",
            ManagerStatus.INACTIVE: "Неактивен"
        }
        return status_map.get(status, "Неизвестно")

    def get_status_color(self, status):
        """Получить цвет статуса"""
        color_map = {
            ManagerStatus.ACTIVE: "#C8E6C9",
            ManagerStatus.BLOCKED: "#FFCDD2",
            ManagerStatus.INACTIVE: "#FFE0B2"
        }
        return color_map.get(status, "#FFFFFF")

    def reset_filters(self):
        """Сбросить фильтры"""
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)

    def add_manager(self):
        """Добавить менеджера"""
        dialog = ManagerEditDialog(None, self)
        if dialog.exec():
            self.load_managers()

    def edit_manager(self):
        """Редактировать менеджера"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        manager_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            manager = session.query(Manager).filter(Manager.id == manager_id).first()
            if manager:
                dialog = ManagerEditDialog(manager, self)
                if dialog.exec():
                    self.load_managers()

    def toggle_block(self):
        """Заблокировать/разблокировать менеджера"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        manager_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            manager = session.query(Manager).filter(Manager.id == manager_id).first()
            if manager:
                if manager.status == ManagerStatus.BLOCKED:
                    manager.status = ManagerStatus.ACTIVE
                    action = "разблокирован"
                else:
                    manager.status = ManagerStatus.BLOCKED
                    action = "заблокирован"

                manager.updated_at = datetime.utcnow()
                session.commit()

                QMessageBox.information(self, "Успех", f"Менеджер {action}")

        self.load_managers()

    def on_column_resized(self):
        """Обработчик изменения ширины колонки"""
        self.table_settings.save_column_widths(self.table)
