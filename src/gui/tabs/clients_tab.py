"""
Вкладка клиентов
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QHeaderView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database.database import get_database
from database.models import Client, Order, Address
from gui.dialogs.client_details_dialog import ClientDetailsDialog
from gui.utils.table_settings import TableSettings
from utils.datetime_utils import format_date, safe_datetime


class ClientsTab(QWidget):
    """Вкладка клиентов"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.table_settings = TableSettings("clients_tab")
        self.init_ui()
        self.load_clients()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель поиска
        search_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по имени, телефону...")
        self.search_input.textChanged.connect(self.filter_clients)
        search_layout.addWidget(QLabel("Поиск:"))
        search_layout.addWidget(self.search_input)

        # Кнопка сброса
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_filters)
        search_layout.addWidget(reset_btn)

        search_layout.addStretch()

        layout.addLayout(search_layout)

        # Таблица клиентов
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Телефон", "Имя", "Бонусы", "Заказов", "Потрачено",
            "Последний заказ", "Адресов", "Создан"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.show_client_details)

        # Восстанавливаем ширину колонок
        self.table_settings.restore_column_widths(self.table)

        # Сохраняем ширину при изменении
        self.table.horizontalHeader().sectionResized.connect(self.on_column_resized)

        layout.addWidget(self.table)

        # Панель кнопок
        button_layout = QHBoxLayout()

        view_btn = QPushButton("Просмотр")
        view_btn.clicked.connect(self.show_client_details)
        button_layout.addWidget(view_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_clients)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        # Статистика
        self.stats_label = QLabel()
        button_layout.addWidget(self.stats_label)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_clients(self):
        """Загрузить клиентов из БД"""
        with Session(self.db.engine) as session:
            # Загружаем клиентов с подсчетом адресов
            self.all_clients = session.query(Client).all()

            # Загружаем количество адресов для каждого клиента
            self.client_addresses_count = {}
            for client in self.all_clients:
                count = session.query(func.count(Address.id)).filter(
                    Address.client_id == client.id
                ).scalar()
                self.client_addresses_count[client.id] = count

            # Detach from session
            session.expunge_all()

        self.filter_clients()

    def filter_clients(self):
        """Применить фильтры"""
        search_text = self.search_input.text().lower()

        filtered_clients = []

        for client in self.all_clients:
            # Фильтр по поиску
            if search_text:
                if not (
                    search_text in client.name.lower() or
                    search_text in client.phone.lower()
                ):
                    continue

            filtered_clients.append(client)

        self.display_clients(filtered_clients)
        self.update_stats(filtered_clients)

    def display_clients(self, clients):
        """Отобразить клиентов в таблице"""
        self.table.setRowCount(len(clients))

        for row, client in enumerate(clients):
            from datetime import datetime

            # Телефон
            self.table.setItem(row, 0, QTableWidgetItem(client.phone))

            # Имя
            self.table.setItem(row, 1, QTableWidgetItem(client.name))

            # Бонусы
            bonus_item = QTableWidgetItem(f"{client.bonus_balance:.0f}")
            if client.bonus_balance > 0:
                bonus_item.setBackground(QColor("#C8E6C9"))
            self.table.setItem(row, 2, bonus_item)

            # Заказов
            self.table.setItem(row, 3, QTableWidgetItem(str(client.total_orders)))

            # Потрачено
            self.table.setItem(row, 4, QTableWidgetItem(f"{client.total_spent:.2f} ₽"))

            # Последний заказ
            last_order_str = format_date(client.last_order_date)
            self.table.setItem(row, 5, QTableWidgetItem(last_order_str))

            # Адресов
            address_count = self.client_addresses_count.get(client.id, 0)
            self.table.setItem(row, 6, QTableWidgetItem(str(address_count)))

            # Создан
            created_str = format_date(client.created_at)
            self.table.setItem(row, 7, QTableWidgetItem(created_str))

            # Сохраняем ID клиента
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, client.id)

    def update_stats(self, clients):
        """Обновить статистику"""
        total = len(clients)
        total_spent = sum(client.total_spent for client in clients)
        total_bonuses = sum(client.bonus_balance for client in clients)
        self.stats_label.setText(
            f"Всего клиентов: {total} | "
            f"Общая сумма покупок: {total_spent:.2f} ₽ | "
            f"Бонусов на счетах: {total_bonuses:.0f}"
        )

    def reset_filters(self):
        """Сбросить фильтры"""
        self.search_input.clear()

    def show_client_details(self):
        """Показать детали клиента"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        client_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            client = session.query(Client).filter(Client.id == client_id).first()
            if client:
                dialog = ClientDetailsDialog(client, self)
                dialog.exec()
                # Обновляем данные после закрытия диалога
                self.load_clients()

    def on_column_resized(self):
        """Обработчик изменения ширины колонки"""
        self.table_settings.save_column_widths(self.table)
