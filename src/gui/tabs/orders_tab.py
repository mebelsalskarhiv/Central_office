"""
Вкладка заказов
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QComboBox, QLabel, QDateEdit, QHeaderView,
    QMessageBox
)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor
from sqlalchemy.orm import Session
from datetime import datetime

from database.database import get_database
from database.models import Order, OrderStatus, PaymentStatus
from gui.dialogs.order_details_dialog import OrderDetailsDialog
from gui.utils.table_settings import TableSettings
from utils.datetime_utils import safe_datetime, format_datetime


class OrdersTab(QWidget):
    """Вкладка заказов"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.table_settings = TableSettings("orders_tab")
        self.init_ui()
        self.load_orders()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель фильтров
        filter_layout = QHBoxLayout()

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по номеру заказа, клиенту, телефону...")
        self.search_input.textChanged.connect(self.filter_orders)
        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_input)

        # Фильтр по статусу
        self.status_filter = QComboBox()
        self.status_filter.addItem("Все статусы", None)
        self.status_filter.addItem("Новый", OrderStatus.NEW)
        self.status_filter.addItem("В работе", OrderStatus.IN_PROGRESS)
        self.status_filter.addItem("Доставлен", OrderStatus.DELIVERED)
        self.status_filter.addItem("Отменен", OrderStatus.CANCELED)
        self.status_filter.currentIndexChanged.connect(self.filter_orders)
        filter_layout.addWidget(QLabel("Статус:"))
        filter_layout.addWidget(self.status_filter)

        # Фильтр по оплате
        self.payment_filter = QComboBox()
        self.payment_filter.addItem("Все", None)
        self.payment_filter.addItem("Не оплачен", PaymentStatus.UNPAID)
        self.payment_filter.addItem("Частично оплачен", PaymentStatus.PARTIALLY_PAID)
        self.payment_filter.addItem("Оплачен", PaymentStatus.PAID)
        self.payment_filter.currentIndexChanged.connect(self.filter_orders)
        filter_layout.addWidget(QLabel("Оплата:"))
        filter_layout.addWidget(self.payment_filter)

        # Фильтр по дате
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.filter_orders)
        filter_layout.addWidget(QLabel("С:"))
        filter_layout.addWidget(self.date_from)

        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate().addDays(1))
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.filter_orders)
        filter_layout.addWidget(QLabel("По:"))
        filter_layout.addWidget(self.date_to)

        # Кнопка сброса фильтров
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(reset_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Таблица заказов
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "№ заказа", "Дата доставки", "Клиент", "Телефон", "Адрес",
            "Сумма", "Статус", "Оплата", "Менеджер", "Создан"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.show_order_details)

        # Восстанавливаем ширину колонок
        self.table_settings.restore_column_widths(self.table)

        # Сохраняем ширину при изменении
        self.table.horizontalHeader().sectionResized.connect(self.on_column_resized)

        layout.addWidget(self.table)

        # Панель кнопок
        button_layout = QHBoxLayout()

        view_btn = QPushButton("Просмотр")
        view_btn.clicked.connect(self.show_order_details)
        button_layout.addWidget(view_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_orders)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        # Статистика
        self.stats_label = QLabel()
        button_layout.addWidget(self.stats_label)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_orders(self):
        """Загрузить заказы из БД"""
        from sqlalchemy.orm import joinedload

        with Session(self.db.engine) as session:
            # Используем joinedload для загрузки relationships
            self.all_orders = session.query(Order)\
                .options(joinedload(Order.client))\
                .options(joinedload(Order.manager))\
                .all()
            # Detach from session
            session.expunge_all()

        self.filter_orders()

    def filter_orders(self):
        """Применить фильтры"""
        search_text = self.search_input.text().lower()
        status = self.status_filter.currentData()
        payment = self.payment_filter.currentData()
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()

        filtered_orders = []

        for order in self.all_orders:
            # Фильтр по поиску
            if search_text:
                try:
                    client_name = order.client.name.lower() if order.client else ""
                    client_phone = order.client.phone.lower() if order.client else ""
                except:
                    client_name = ""
                    client_phone = ""
                if not (
                    search_text in order.order_number.lower() or
                    search_text in client_name or
                    search_text in client_phone
                ):
                    continue

            # Фильтр по статусу
            if status is not None and order.status != status:
                continue

            # Фильтр по оплате
            if payment is not None and order.payment_status != payment:
                continue

            # Фильтр по дате доставки
            order_date = safe_datetime(order.delivery_date)
            if order_date:
                order_date = order_date.date()
                if order_date < date_from or order_date > date_to:
                    continue
            else:
                continue

            filtered_orders.append(order)

        self.display_orders(filtered_orders)
        self.update_stats(filtered_orders)

    def display_orders(self, orders):
        """Отобразить заказы в таблице"""
        self.table.setRowCount(len(orders))

        for row, order in enumerate(orders):
            # № заказа
            self.table.setItem(row, 0, QTableWidgetItem(order.order_number))

            # Дата доставки
            delivery_date = safe_datetime(order.delivery_date)
            date_str = format_datetime(delivery_date, "%d.%m.%Y %H:%M") if delivery_date else "-"
            self.table.setItem(row, 1, QTableWidgetItem(date_str))

            # Клиент
            try:
                client_name = order.client.name if order.client else "-"
            except:
                client_name = "-"
            self.table.setItem(row, 2, QTableWidgetItem(client_name))

            # Телефон
            try:
                client_phone = order.client.phone if order.client else "-"
            except:
                client_phone = "-"
            self.table.setItem(row, 3, QTableWidgetItem(client_phone))

            # Адрес
            self.table.setItem(row, 4, QTableWidgetItem(order.address_text[:50]))

            # Сумма
            self.table.setItem(row, 5, QTableWidgetItem(f"{order.total_amount:.2f} ₽"))

            # Статус
            status_item = QTableWidgetItem(self.get_status_text(order.status))
            status_item.setBackground(QColor(self.get_status_color(order.status)))
            self.table.setItem(row, 6, status_item)

            # Оплата
            payment_item = QTableWidgetItem(self.get_payment_text(order.payment_status))
            payment_item.setBackground(QColor(self.get_payment_color(order.payment_status)))
            self.table.setItem(row, 7, payment_item)

            # Менеджер
            try:
                manager_pin = order.manager.pin_code if order.manager else "-"
            except:
                manager_pin = "-"
            self.table.setItem(row, 8, QTableWidgetItem(manager_pin))

            # Создан
            created_date = safe_datetime(order.created_at)
            created_str = format_datetime(created_date, "%d.%m.%Y %H:%M") if created_date else "-"
            self.table.setItem(row, 9, QTableWidgetItem(created_str))

            # Сохраняем ID заказа
            self.table.item(row, 0).setData(Qt.ItemDataRole.UserRole, order.id)

    def update_stats(self, orders):
        """Обновить статистику"""
        total = len(orders)
        total_sum = sum(order.total_amount for order in orders)
        self.stats_label.setText(f"Всего заказов: {total} | Сумма: {total_sum:.2f} ₽")

    def get_status_text(self, status):
        """Получить текст статуса"""
        status_map = {
            OrderStatus.NEW: "Новый",
            OrderStatus.IN_PROGRESS: "В работе",
            OrderStatus.DELIVERED: "Доставлен",
            OrderStatus.CANCELED: "Отменен"
        }
        return status_map.get(status, "Неизвестно")

    def get_status_color(self, status):
        """Получить цвет статуса"""
        color_map = {
            OrderStatus.NEW: "#E3F2FD",
            OrderStatus.IN_PROGRESS: "#FFF9C4",
            OrderStatus.DELIVERED: "#C8E6C9",
            OrderStatus.CANCELED: "#FFCDD2"
        }
        return color_map.get(status, "#FFFFFF")

    def get_payment_text(self, payment):
        """Получить текст оплаты"""
        payment_map = {
            PaymentStatus.UNPAID: "Не оплачен",
            PaymentStatus.PARTIALLY_PAID: "Частично",
            PaymentStatus.PAID: "Оплачен"
        }
        return payment_map.get(payment, "Неизвестно")

    def get_payment_color(self, payment):
        """Получить цвет оплаты"""
        color_map = {
            PaymentStatus.UNPAID: "#FFCDD2",
            PaymentStatus.PARTIALLY_PAID: "#FFE0B2",
            PaymentStatus.PAID: "#C8E6C9"
        }
        return color_map.get(payment, "#FFFFFF")

    def reset_filters(self):
        """Сбросить фильтры"""
        self.search_input.clear()
        self.status_filter.setCurrentIndex(0)
        self.payment_filter.setCurrentIndex(0)
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_to.setDate(QDate.currentDate().addDays(1))

    def show_order_details(self):
        """Показать детали заказа"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        order_id = self.table.item(current_row, 0).data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            order = session.query(Order).filter(Order.id == order_id).first()
            if order:
                dialog = OrderDetailsDialog(order, self)
                dialog.exec()

    def on_column_resized(self):
        """Обработчик изменения ширины колонки"""
        self.table_settings.save_column_widths(self.table)
