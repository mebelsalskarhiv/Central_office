"""
Диалог детального просмотра заказа
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QTextEdit,
    QFormLayout, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from datetime import datetime

from database.models import Order
from utils.datetime_utils import safe_datetime, format_datetime


class OrderDetailsDialog(QDialog):
    """Диалог детального просмотра заказа"""

    def __init__(self, order, parent=None):
        super().__init__(parent)
        self.order = order
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(f"Заказ {self.order.order_number}")
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout()

        # Создаем прокручиваемую область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()

        # Основная информация
        main_group = QGroupBox("Основная информация")
        main_layout = QFormLayout()

        main_layout.addRow("Номер заказа:", QLabel(self.order.order_number))

        delivery_date = safe_datetime(self.order.delivery_date)
        delivery_str = format_datetime(delivery_date, "%d.%m.%Y %H:%M") if delivery_date else "-"
        main_layout.addRow("Дата доставки:", QLabel(delivery_str))

        main_layout.addRow("Временной слот:", QLabel(self.order.delivery_time_slot or "-"))

        status_text = self.get_status_text(self.order.status)
        main_layout.addRow("Статус:", QLabel(status_text))

        payment_status_text = self.get_payment_status_text(self.order.payment_status)
        main_layout.addRow("Статус оплаты:", QLabel(payment_status_text))

        payment_type_text = self.get_payment_type_text(self.order.payment_type)
        main_layout.addRow("Способ оплаты:", QLabel(payment_type_text))

        main_group.setLayout(main_layout)
        scroll_layout.addWidget(main_group)

        # Информация о клиенте
        client_group = QGroupBox("Клиент")
        client_layout = QFormLayout()

        try:
            client_name = self.order.client.name if self.order.client else "-"
            client_phone = self.order.client.phone if self.order.client else "-"
        except:
            client_name = "-"
            client_phone = "-"

        client_layout.addRow("Имя:", QLabel(client_name))
        client_layout.addRow("Телефон:", QLabel(client_phone))

        if self.order.client_id:
            client_layout.addRow("ID клиента:", QLabel(str(self.order.client_id)))

        client_group.setLayout(client_layout)
        scroll_layout.addWidget(client_group)

        # Адрес доставки
        address_group = QGroupBox("Адрес доставки")
        address_layout = QVBoxLayout()

        address_label = QLabel(self.order.address_text)
        address_label.setWordWrap(True)
        address_layout.addWidget(address_label)

        if self.order.address_latitude and self.order.address_longitude:
            coords_label = QLabel(f"Координаты: {self.order.address_latitude}, {self.order.address_longitude}")
            coords_label.setStyleSheet("color: gray; font-size: 10px;")
            address_layout.addWidget(coords_label)

        address_group.setLayout(address_layout)
        scroll_layout.addWidget(address_group)

        # Товары в заказе
        items_group = QGroupBox("Товары")
        items_layout = QVBoxLayout()

        items_table = QTableWidget()
        items_table.setColumnCount(5)
        items_table.setHorizontalHeaderLabels(["Товар", "Количество", "Цена", "Сумма", "ID товара"])
        items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        if self.order.items:
            items_table.setRowCount(len(self.order.items))
            for row, item in enumerate(self.order.items):
                items_table.setItem(row, 0, QTableWidgetItem(item.product_name))
                items_table.setItem(row, 1, QTableWidgetItem(str(item.quantity)))
                items_table.setItem(row, 2, QTableWidgetItem(f"{item.price_at_moment:.2f} ₽"))
                items_table.setItem(row, 3, QTableWidgetItem(f"{item.sum:.2f} ₽"))
                items_table.setItem(row, 4, QTableWidgetItem(item.product_id or "-"))

        items_layout.addWidget(items_table)
        items_group.setLayout(items_layout)
        scroll_layout.addWidget(items_group)

        # Финансовая информация
        finance_group = QGroupBox("Финансы")
        finance_layout = QFormLayout()

        finance_layout.addRow("Сумма заказа:", QLabel(f"{self.order.total_amount:.2f} ₽"))
        finance_layout.addRow("Использовано бонусов:", QLabel(f"{self.order.bonus_used:.2f}"))
        finance_layout.addRow("Начислено бонусов:", QLabel(f"{self.order.bonus_earned:.2f}"))

        finance_group.setLayout(finance_layout)
        scroll_layout.addWidget(finance_group)

        # Комментарий
        if self.order.comment:
            comment_group = QGroupBox("Комментарий")
            comment_layout = QVBoxLayout()

            comment_text = QTextEdit()
            comment_text.setPlainText(self.order.comment)
            comment_text.setReadOnly(True)
            comment_text.setMaximumHeight(100)
            comment_layout.addWidget(comment_text)

            comment_group.setLayout(comment_layout)
            scroll_layout.addWidget(comment_group)

        # Дополнительная информация
        extra_group = QGroupBox("Дополнительно")
        extra_layout = QFormLayout()

        try:
            manager_pin = self.order.manager.pin_code if self.order.manager else "-"
            device_id = self.order.manager.device_id if self.order.manager else "-"
        except:
            manager_pin = "-"
            device_id = "-"
        extra_layout.addRow("Менеджер (PIN):", QLabel(manager_pin))
        extra_layout.addRow("Устройство:", QLabel(device_id or "-"))

        created_date = safe_datetime(self.order.created_at)
        created_str = format_datetime(created_date, "%d.%m.%Y %H:%M:%S") if created_date else "-"
        extra_layout.addRow("Создан:", QLabel(created_str))

        updated_date = safe_datetime(self.order.updated_at)
        updated_str = format_datetime(updated_date, "%d.%m.%Y %H:%M:%S") if updated_date else "-"
        extra_layout.addRow("Обновлен:", QLabel(updated_str))

        extra_group.setLayout(extra_layout)
        scroll_layout.addWidget(extra_group)

        # Геолокация оплаты
        if self.order.payment_location:
            location_group = QGroupBox("Место оплаты")
            location_layout = QFormLayout()

            location_layout.addRow("Широта:", QLabel(str(self.order.payment_location.latitude)))
            location_layout.addRow("Долгота:", QLabel(str(self.order.payment_location.longitude)))
            location_layout.addRow("Точность:", QLabel(f"{self.order.payment_location.accuracy} м"))

            payment_time = safe_datetime(self.order.payment_location.timestamp)
            payment_str = format_datetime(payment_time, "%d.%m.%Y %H:%M:%S") if payment_time else "-"
            location_layout.addRow("Время:", QLabel(payment_str))

            location_group.setLayout(location_layout)
            scroll_layout.addWidget(location_group)

        scroll_widget.setLayout(scroll_layout)
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Кнопка закрытия
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_status_text(self, status):
        """Получить текст статуса"""
        from database.models import OrderStatus
        status_map = {
            OrderStatus.NEW: "Новый",
            OrderStatus.IN_PROGRESS: "В работе",
            OrderStatus.DELIVERED: "Доставлен",
            OrderStatus.CANCELED: "Отменен"
        }
        return status_map.get(status, "Неизвестно")

    def get_payment_status_text(self, status):
        """Получить текст статуса оплаты"""
        from database.models import PaymentStatus
        status_map = {
            PaymentStatus.UNPAID: "Не оплачен",
            PaymentStatus.PARTIALLY_PAID: "Частично оплачен",
            PaymentStatus.PAID: "Оплачен"
        }
        return status_map.get(status, "Неизвестно")

    def get_payment_type_text(self, payment_type):
        """Получить текст способа оплаты"""
        from database.models import PaymentType
        type_map = {
            PaymentType.CASH: "Наличные",
            PaymentType.CARD: "Карта",
            PaymentType.TRANSFER: "Перевод",
            PaymentType.MIXED: "Смешанный"
        }
        return type_map.get(payment_type, "Неизвестно")
