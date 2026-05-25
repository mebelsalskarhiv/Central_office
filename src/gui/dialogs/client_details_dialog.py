"""
Диалог детального просмотра клиента
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QTableWidget, QTableWidgetItem, QPushButton, QTextEdit,
    QFormLayout, QScrollArea, QWidget, QTabWidget
)
from PyQt6.QtCore import Qt
from datetime import datetime
from sqlalchemy.orm import Session

from database.database import get_database
from database.models import Client, Order, Address, BonusTransaction
from utils.datetime_utils import safe_datetime, format_datetime


class ClientDetailsDialog(QDialog):
    """Диалог детального просмотра клиента"""

    def __init__(self, client, parent=None):
        super().__init__(parent)
        self.client = client
        self.db = get_database()
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle(f"Клиент: {self.client.name}")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout()

        # Основная информация
        info_group = QGroupBox("Основная информация")
        info_layout = QFormLayout()

        info_layout.addRow("Телефон:", QLabel(self.client.phone))
        info_layout.addRow("Имя:", QLabel(self.client.name))
        info_layout.addRow("Баланс бонусов:", QLabel(f"{self.client.bonus_balance:.0f}"))
        info_layout.addRow("Всего заказов:", QLabel(str(self.client.total_orders)))
        info_layout.addRow("Потрачено:", QLabel(f"{self.client.total_spent:.2f} ₽"))

        if self.client.last_order_date:
            last_order = safe_datetime(self.client.last_order_date)
            last_order_str = format_datetime(last_order, "%d.%m.%Y %H:%M") if last_order else "-"
            info_layout.addRow("Последний заказ:", QLabel(last_order_str))

        created_date = safe_datetime(self.client.created_at)
        created_str = format_datetime(created_date, "%d.%m.%Y %H:%M") if created_date else "-"
        info_layout.addRow("Создан:", QLabel(created_str))

        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Заметки
        if self.client.notes:
            notes_group = QGroupBox("Заметки")
            notes_layout = QVBoxLayout()

            notes_text = QTextEdit()
            notes_text.setPlainText(self.client.notes)
            notes_text.setReadOnly(True)
            notes_text.setMaximumHeight(80)
            notes_layout.addWidget(notes_text)

            notes_group.setLayout(notes_layout)
            layout.addWidget(notes_group)

        # Вкладки с детальной информацией
        tabs = QTabWidget()

        # Вкладка "Адреса"
        addresses_tab = self.create_addresses_tab()
        tabs.addTab(addresses_tab, "Адреса")

        # Вкладка "История заказов"
        orders_tab = self.create_orders_tab()
        tabs.addTab(orders_tab, "История заказов")

        # Вкладка "Бонусы"
        bonuses_tab = self.create_bonuses_tab()
        tabs.addTab(bonuses_tab, "Бонусы")

        layout.addWidget(tabs)

        # Кнопка закрытия
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_addresses_tab(self):
        """Создать вкладку адресов"""
        widget = QWidget()
        layout = QVBoxLayout()

        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(["Метка", "Адрес", "Координаты", "По умолчанию", "Создан"])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        with Session(self.db.engine) as session:
            addresses = session.query(Address).filter(
                Address.client_id == self.client.id
            ).all()

            table.setRowCount(len(addresses))

            for row, address in enumerate(addresses):
                # Метка
                table.setItem(row, 0, QTableWidgetItem(address.label or "-"))

                # Адрес
                addr_parts = []
                if address.street:
                    addr_parts.append(address.street)
                if address.house:
                    addr_parts.append(f"д. {address.house}")
                if address.apartment:
                    addr_parts.append(f"кв. {address.apartment}")

                full_address = ", ".join(addr_parts) if addr_parts else address.address_text
                table.setItem(row, 1, QTableWidgetItem(full_address))

                # Координаты
                if address.latitude and address.longitude:
                    coords = f"{address.latitude:.6f}, {address.longitude:.6f}"
                else:
                    coords = "-"
                table.setItem(row, 2, QTableWidgetItem(coords))

                # По умолчанию
                default_text = "Да" if address.is_default else "Нет"
                table.setItem(row, 3, QTableWidgetItem(default_text))

                # Создан
                created = safe_datetime(address.created_at)
                created_str = format_datetime(created, "%d.%m.%Y") if created else "-"
                table.setItem(row, 4, QTableWidgetItem(created_str))

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

    def create_orders_tab(self):
        """Создать вкладку истории заказов"""
        widget = QWidget()
        layout = QVBoxLayout()

        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels([
            "№ заказа", "Дата доставки", "Сумма", "Статус", "Оплата", "Создан"
        ])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        with Session(self.db.engine) as session:
            orders = session.query(Order).filter(
                Order.client_id == self.client.id
            ).order_by(Order.created_at.desc()).all()

            table.setRowCount(len(orders))

            for row, order in enumerate(orders):
                # № заказа
                table.setItem(row, 0, QTableWidgetItem(order.order_number))

                # Дата доставки
                delivery_date = safe_datetime(order.delivery_date)
                delivery_str = format_datetime(delivery_date, "%d.%m.%Y %H:%M") if delivery_date else "-"
                table.setItem(row, 1, QTableWidgetItem(delivery_str))

                # Сумма
                table.setItem(row, 2, QTableWidgetItem(f"{order.total_amount:.2f} ₽"))

                # Статус
                table.setItem(row, 3, QTableWidgetItem(self.get_status_text(order.status)))

                # Оплата
                table.setItem(row, 4, QTableWidgetItem(self.get_payment_text(order.payment_status)))

                # Создан
                created = safe_datetime(order.created_at)
                created_str = format_datetime(created, "%d.%m.%Y %H:%M") if created else "-"
                table.setItem(row, 5, QTableWidgetItem(created_str))

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

    def create_bonuses_tab(self):
        """Создать вкладку бонусов"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Текущий баланс
        balance_label = QLabel(f"Текущий баланс: {self.client.bonus_balance:.0f} бонусов")
        balance_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(balance_label)

        # История транзакций
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Дата", "Тип", "Сумма", "Заказ", "Описание"
        ])
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        with Session(self.db.engine) as session:
            transactions = session.query(BonusTransaction).filter(
                BonusTransaction.client_id == self.client.id
            ).order_by(BonusTransaction.created_at.desc()).all()

            table.setRowCount(len(transactions))

            for row, transaction in enumerate(transactions):
                # Дата
                created = safe_datetime(transaction.created_at)
                created_str = format_datetime(created, "%d.%m.%Y %H:%M") if created else "-"
                table.setItem(row, 0, QTableWidgetItem(created_str))

                # Тип
                type_text = "Начисление" if transaction.type.name == "EARNED" else "Списание"
                table.setItem(row, 1, QTableWidgetItem(type_text))

                # Сумма
                amount_text = f"+{transaction.amount:.0f}" if transaction.type.name == "EARNED" else f"-{transaction.amount:.0f}"
                table.setItem(row, 2, QTableWidgetItem(amount_text))

                # Заказ
                order_text = transaction.order_id or "-"
                table.setItem(row, 3, QTableWidgetItem(str(order_text)))

                # Описание
                table.setItem(row, 4, QTableWidgetItem(transaction.description or "-"))

        layout.addWidget(table)
        widget.setLayout(layout)
        return widget

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

    def get_payment_text(self, payment):
        """Получить текст оплаты"""
        from database.models import PaymentStatus
        payment_map = {
            PaymentStatus.UNPAID: "Не оплачен",
            PaymentStatus.PARTIALLY_PAID: "Частично",
            PaymentStatus.PAID: "Оплачен"
        }
        return payment_map.get(payment, "Неизвестно")
