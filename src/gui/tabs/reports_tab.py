"""
Вкладка отчетов для сборки и доставки заказов
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QLabel,
    QDateEdit, QComboBox, QTabWidget, QTextEdit, QSplitter
)
from PyQt6.QtCore import QDate, Qt, QSizeF
from PyQt6.QtGui import QFont, QTextDocument
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict

from database.database import get_database
from database.models import Order, OrderItem, Client, Address, OrderStatus


class ReportsTab(QWidget):
    """Вкладка отчетов для сборки и доставки"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель фильтров
        filter_layout = QHBoxLayout()

        filter_layout.addWidget(QLabel("Дата:"))
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load_data)
        filter_layout.addWidget(self.date_edit)

        filter_layout.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Все", None)
        self.status_combo.addItem("Новые", OrderStatus.NEW)
        self.status_combo.addItem("В работе", OrderStatus.IN_PROGRESS)
        self.status_combo.addItem("Доставлено", OrderStatus.DELIVERED)
        self.status_combo.addItem("Отменено", OrderStatus.CANCELED)
        self.status_combo.currentIndexChanged.connect(self.load_data)
        filter_layout.addWidget(self.status_combo)

        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Вкладки для разных отчетов
        self.report_tabs = QTabWidget()

        # Отчет для кассира (сводка по товарам)
        self.cashier_widget = QWidget()
        self.init_cashier_report()
        self.report_tabs.addTab(self.cashier_widget, "Для кассира (сборка)")

        # Отчет для курьера (по адресам)
        self.courier_widget = QWidget()
        self.init_courier_report()
        self.report_tabs.addTab(self.courier_widget, "Для курьера (доставка)")

        layout.addWidget(self.report_tabs)

        self.setLayout(layout)

    def init_cashier_report(self):
        """Инициализация отчета для кассира"""
        layout = QVBoxLayout()

        # Кнопки действий
        actions_layout = QHBoxLayout()
        self.print_cashier_btn = QPushButton("Печать")
        self.print_cashier_btn.clicked.connect(self.print_cashier_report)
        actions_layout.addWidget(self.print_cashier_btn)

        self.export_cashier_btn = QPushButton("Экспорт в текст")
        self.export_cashier_btn.clicked.connect(self.export_cashier_report)
        actions_layout.addWidget(self.export_cashier_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Таблица сводки по товарам
        self.cashier_table = QTableWidget()
        self.cashier_table.setColumnCount(4)
        self.cashier_table.setHorizontalHeaderLabels([
            "Товар", "Количество", "Единица", "Заказов"
        ])
        self.cashier_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.cashier_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.cashier_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.cashier_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.cashier_table.setAlternatingRowColors(True)
        self.cashier_table.setSortingEnabled(True)

        layout.addWidget(self.cashier_table)

        # Итоговая информация
        self.cashier_summary = QLabel()
        self.cashier_summary.setStyleSheet("font-weight: bold; padding: 10px;")
        layout.addWidget(self.cashier_summary)

        self.cashier_widget.setLayout(layout)

    def init_courier_report(self):
        """Инициализация отчета для курьера"""
        layout = QVBoxLayout()

        # Кнопки действий
        actions_layout = QHBoxLayout()
        self.print_courier_btn = QPushButton("Печать")
        self.print_courier_btn.clicked.connect(self.print_courier_report)
        actions_layout.addWidget(self.print_courier_btn)

        self.export_courier_btn = QPushButton("Экспорт в текст")
        self.export_courier_btn.clicked.connect(self.export_courier_report)
        actions_layout.addWidget(self.export_courier_btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Текстовое поле для отчета курьера (удобнее для печати)
        self.courier_text = QTextEdit()
        self.courier_text.setReadOnly(True)
        font = QFont("Courier New", 10)
        self.courier_text.setFont(font)

        layout.addWidget(self.courier_text)

        self.courier_widget.setLayout(layout)

    def load_data(self):
        """Загрузить данные для отчетов"""
        try:
            session = self.db.get_session()

            selected_date = self.date_edit.date().toPyDate()
            date_from = datetime.combine(selected_date, datetime.min.time())
            date_to = datetime.combine(selected_date, datetime.max.time())

            status_filter = self.status_combo.currentData()

            # Получаем заказы за выбранную дату
            query = session.query(Order).filter(
                Order.delivery_date >= date_from,
                Order.delivery_date <= date_to
            )

            if status_filter:
                query = query.filter(Order.status == status_filter)

            orders = query.all()

            # Генерируем отчеты
            self.generate_cashier_report(session, orders)
            self.generate_courier_report(session, orders)

            session.close()

        except Exception as e:
            print(f"Error loading reports data: {e}")

    def generate_cashier_report(self, session, orders):
        """Генерировать отчет для кассира (сводка по товарам)"""
        # Собираем статистику по товарам
        product_stats = defaultdict(lambda: {"quantity": 0, "orders": set()})

        for order in orders:
            for item in order.items:
                product_name = item.product_name
                product_stats[product_name]["quantity"] += item.quantity
                product_stats[product_name]["orders"].add(order.id)

        # Заполняем таблицу
        self.cashier_table.setRowCount(0)
        self.cashier_table.setSortingEnabled(False)

        total_items = 0
        total_orders = len(orders)

        for product_name in sorted(product_stats.keys()):
            stats = product_stats[product_name]
            row = self.cashier_table.rowCount()
            self.cashier_table.insertRow(row)

            # Товар
            self.cashier_table.setItem(row, 0, QTableWidgetItem(product_name))

            # Количество
            quantity_item = QTableWidgetItem(str(stats["quantity"]))
            quantity_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cashier_table.setItem(row, 1, quantity_item)

            # Единица (пока "шт", можно расширить)
            unit_item = QTableWidgetItem("шт")
            unit_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cashier_table.setItem(row, 2, unit_item)

            # Количество заказов
            orders_count_item = QTableWidgetItem(str(len(stats["orders"])))
            orders_count_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.cashier_table.setItem(row, 3, orders_count_item)

            total_items += stats["quantity"]

        self.cashier_table.setSortingEnabled(True)

        # Обновляем итоговую информацию
        self.cashier_summary.setText(
            f"Всего товаров: {total_items} | "
            f"Наименований: {len(product_stats)} | "
            f"Заказов: {total_orders}"
        )

    def generate_courier_report(self, session, orders):
        """Генерировать отчет для курьера (по адресам)"""
        # Группируем заказы по клиентам и адресам
        client_orders = defaultdict(lambda: defaultdict(list))

        for order in orders:
            client_name = order.client.name if order.client else "Без имени"
            client_phone = order.client.phone if order.client else "Без телефона"
            address = order.address_text or "Адрес не указан"

            client_key = f"{client_name} ({client_phone})"
            client_orders[client_key][address].append(order)

        # Формируем текстовый отчет
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append(f"ОТЧЕТ ДЛЯ КУРЬЕРА - {self.date_edit.date().toString('dd.MM.yyyy')}")
        report_lines.append("=" * 80)
        report_lines.append("")

        total_orders = 0

        for client_key in sorted(client_orders.keys()):
            addresses = client_orders[client_key]

            report_lines.append(f"КЛИЕНТ: {client_key}")
            report_lines.append("-" * 80)

            for address in sorted(addresses.keys()):
                orders_list = addresses[address]
                report_lines.append(f"  Адрес: {address}")
                report_lines.append("")

                for order in orders_list:
                    total_orders += 1
                    report_lines.append(f"    Заказ №{order.order_number}")
                    report_lines.append(f"    Время: {order.delivery_time_slot or 'не указано'}")
                    report_lines.append(f"    Сумма: {order.total_amount:.2f} руб.")
                    report_lines.append(f"    Оплата: {order.payment_type.value if order.payment_type else 'не указано'}")
                    report_lines.append(f"    Статус: {order.payment_status.value if order.payment_status else 'не указано'}")
                    report_lines.append("")
                    report_lines.append("    Состав заказа:")

                    for item in order.items:
                        report_lines.append(f"      - {item.product_name}: {item.quantity} шт x {item.price_at_moment:.2f} = {item.sum:.2f} руб.")

                    if order.comment:
                        report_lines.append(f"    Комментарий: {order.comment}")

                    report_lines.append("")

                report_lines.append("")

            report_lines.append("")

        report_lines.append("=" * 80)
        report_lines.append(f"ИТОГО ЗАКАЗОВ: {total_orders}")
        report_lines.append("=" * 80)

        self.courier_text.setPlainText("\n".join(report_lines))

    def print_cashier_report(self):
        """Печать отчета для кассира"""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            # Формируем HTML для печати
            html = self.generate_cashier_html()

            # Создаем документ для печати
            document = QTextDocument()
            document.setHtml(html)
            document.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
            document.print(printer)

    def print_courier_report(self):
        """Печать отчета для курьера"""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)

        if dialog.exec() == QPrintDialog.DialogCode.Accepted:
            self.courier_text.print(printer)

    def export_cashier_report(self):
        """Экспорт отчета кассира в текст"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет",
            f"cashier_report_{self.date_edit.date().toString('yyyy-MM-dd')}.txt",
            "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(f"ОТЧЕТ ДЛЯ КАССИРА - {self.date_edit.date().toString('dd.MM.yyyy')}\n")
                    f.write("=" * 80 + "\n\n")

                    for row in range(self.cashier_table.rowCount()):
                        product = self.cashier_table.item(row, 0).text()
                        quantity = self.cashier_table.item(row, 1).text()
                        unit = self.cashier_table.item(row, 2).text()
                        orders = self.cashier_table.item(row, 3).text()

                        f.write(f"{product}: {quantity} {unit} (в {orders} заказах)\n")

                    f.write("\n" + "=" * 80 + "\n")
                    f.write(self.cashier_summary.text() + "\n")

                print(f"Отчет сохранен: {file_path}")

            except Exception as e:
                print(f"Error exporting cashier report: {e}")

    def export_courier_report(self):
        """Экспорт отчета курьера в текст"""
        from PyQt6.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет",
            f"courier_report_{self.date_edit.date().toString('yyyy-MM-dd')}.txt",
            "Text Files (*.txt)"
        )

        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.courier_text.toPlainText())

                print(f"Отчет сохранен: {file_path}")

            except Exception as e:
                print(f"Error exporting courier report: {e}")

    def generate_cashier_html(self):
        """Генерировать HTML для печати отчета кассира"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; }}
                h1 {{ text-align: center; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ border: 1px solid black; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Отчет для кассира - {self.date_edit.date().toString('dd.MM.yyyy')}</h1>
            <table>
                <tr>
                    <th>Товар</th>
                    <th>Количество</th>
                    <th>Единица</th>
                    <th>Заказов</th>
                </tr>
        """

        for row in range(self.cashier_table.rowCount()):
            product = self.cashier_table.item(row, 0).text()
            quantity = self.cashier_table.item(row, 1).text()
            unit = self.cashier_table.item(row, 2).text()
            orders = self.cashier_table.item(row, 3).text()

            html += f"""
                <tr>
                    <td>{product}</td>
                    <td>{quantity}</td>
                    <td>{unit}</td>
                    <td>{orders}</td>
                </tr>
            """

        html += """
            </table>
        </body>
        </html>
        """

        return html
