"""
Вкладка аналитики
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QDateEdit, QComboBox, QGridLayout, QScrollArea
)
from PyQt6.QtCore import Qt, QDate
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

from database.database import get_database
from database.models import Order, OrderStatus, Client, Product, OrderItem, Manager


class AnalyticsTab(QWidget):
    """Вкладка аналитики"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.init_ui()
        self.load_analytics()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель фильтров
        filter_layout = QHBoxLayout()

        # Период
        filter_layout.addWidget(QLabel("Период:"))

        self.period_combo = QComboBox()
        self.period_combo.addItem("Сегодня", 0)
        self.period_combo.addItem("Вчера", 1)
        self.period_combo.addItem("Последние 7 дней", 7)
        self.period_combo.addItem("Последние 30 дней", 30)
        self.period_combo.addItem("Этот месяц", -1)
        self.period_combo.addItem("Произвольный", -2)
        self.period_combo.currentIndexChanged.connect(self.on_period_changed)
        filter_layout.addWidget(self.period_combo)

        # Даты (скрыты по умолчанию)
        filter_layout.addWidget(QLabel("С:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        self.date_from.dateChanged.connect(self.load_analytics)
        self.date_from.setVisible(False)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("По:"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        self.date_to.dateChanged.connect(self.load_analytics)
        self.date_to.setVisible(False)
        filter_layout.addWidget(self.date_to)

        # Кнопка обновления
        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_analytics)
        filter_layout.addWidget(refresh_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Скроллируемая область для графиков
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.charts_layout = QVBoxLayout()
        scroll_widget.setLayout(self.charts_layout)
        scroll.setWidget(scroll_widget)

        layout.addWidget(scroll)

        self.setLayout(layout)

    def on_period_changed(self):
        """Обработчик изменения периода"""
        period = self.period_combo.currentData()

        if period == -2:  # Произвольный
            self.date_from.setVisible(True)
            self.date_to.setVisible(True)
        else:
            self.date_from.setVisible(False)
            self.date_to.setVisible(False)

        self.load_analytics()

    def get_date_range(self):
        """Получить диапазон дат"""
        period = self.period_combo.currentData()
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        if period == 0:  # Сегодня
            return today, datetime.now()
        elif period == 1:  # Вчера
            yesterday = today - timedelta(days=1)
            return yesterday, today
        elif period == -1:  # Этот месяц
            first_day = today.replace(day=1)
            return first_day, datetime.now()
        elif period == -2:  # Произвольный
            date_from = self.date_from.date().toPyDate()
            date_to = self.date_to.date().toPyDate()
            return datetime.combine(date_from, datetime.min.time()), datetime.combine(date_to, datetime.max.time())
        else:  # Последние N дней
            date_from = today - timedelta(days=period)
            return date_from, datetime.now()

    def load_analytics(self):
        """Загрузить аналитику"""
        # Очищаем предыдущие графики
        for i in reversed(range(self.charts_layout.count())):
            widget = self.charts_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        date_from, date_to = self.get_date_range()

        with Session(self.db.engine) as session:
            # Общая статистика
            self.add_summary_stats(session, date_from, date_to)

            # График продаж по дням
            self.add_sales_chart(session, date_from, date_to)

            # ТОП товаров
            self.add_top_products(session, date_from, date_to)

            # ТОП клиентов
            self.add_top_clients(session, date_from, date_to)

            # Статистика по менеджерам
            self.add_managers_stats(session, date_from, date_to)

    def add_summary_stats(self, session, date_from, date_to):
        """Добавить общую статистику"""
        # Получаем данные
        orders = session.query(Order).filter(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to
            )
        ).all()

        total_orders = len(orders)
        total_revenue = sum(order.total_amount for order in orders)
        avg_check = total_revenue / total_orders if total_orders > 0 else 0

        delivered = sum(1 for order in orders if order.status == OrderStatus.DELIVERED)
        canceled = sum(1 for order in orders if order.status == OrderStatus.CANCELED)

        # Создаем виджет статистики
        stats_group = QGroupBox("Общая статистика")
        stats_layout = QGridLayout()

        stats_layout.addWidget(QLabel("Всего заказов:"), 0, 0)
        stats_layout.addWidget(QLabel(f"<b>{total_orders}</b>"), 0, 1)

        stats_layout.addWidget(QLabel("Выручка:"), 0, 2)
        stats_layout.addWidget(QLabel(f"<b>{total_revenue:,.2f} ₽</b>"), 0, 3)

        stats_layout.addWidget(QLabel("Средний чек:"), 1, 0)
        stats_layout.addWidget(QLabel(f"<b>{avg_check:,.2f} ₽</b>"), 1, 1)

        stats_layout.addWidget(QLabel("Доставлено:"), 1, 2)
        stats_layout.addWidget(QLabel(f"<b>{delivered}</b>"), 1, 3)

        stats_layout.addWidget(QLabel("Отменено:"), 2, 0)
        stats_layout.addWidget(QLabel(f"<b>{canceled}</b>"), 2, 1)

        conversion = (delivered / total_orders * 100) if total_orders > 0 else 0
        stats_layout.addWidget(QLabel("Конверсия:"), 2, 2)
        stats_layout.addWidget(QLabel(f"<b>{conversion:.1f}%</b>"), 2, 3)

        stats_group.setLayout(stats_layout)
        self.charts_layout.addWidget(stats_group)

    def add_sales_chart(self, session, date_from, date_to):
        """Добавить график продаж по дням"""
        # Получаем данные по дням
        days_data = {}
        orders = session.query(Order).filter(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to,
                Order.status == OrderStatus.DELIVERED
            )
        ).all()

        for order in orders:
            if isinstance(order.created_at, datetime):
                date = order.created_at.date()
            else:
                date = datetime.fromtimestamp(order.created_at / 1000).date()

            if date not in days_data:
                days_data[date] = {'count': 0, 'revenue': 0}

            days_data[date]['count'] += 1
            days_data[date]['revenue'] += order.total_amount

        # Сортируем по датам
        sorted_dates = sorted(days_data.keys())
        counts = [days_data[date]['count'] for date in sorted_dates]
        revenues = [days_data[date]['revenue'] for date in sorted_dates]
        date_labels = [date.strftime('%d.%m') for date in sorted_dates]

        # Создаем график
        fig = Figure(figsize=(10, 4))
        ax1 = fig.add_subplot(111)

        ax1.bar(date_labels, counts, alpha=0.7, label='Количество заказов', color='#4CAF50')
        ax1.set_xlabel('Дата')
        ax1.set_ylabel('Количество заказов', color='#4CAF50')
        ax1.tick_params(axis='y', labelcolor='#4CAF50')
        ax1.legend(loc='upper left')
        ax1.grid(True, alpha=0.3)

        ax2 = ax1.twinx()
        ax2.plot(date_labels, revenues, 'o-', color='#2196F3', linewidth=2, label='Выручка')
        ax2.set_ylabel('Выручка (₽)', color='#2196F3')
        ax2.tick_params(axis='y', labelcolor='#2196F3')
        ax2.legend(loc='upper right')

        fig.tight_layout()
        fig.suptitle('Продажи по дням', fontsize=14, y=1.02)

        canvas = FigureCanvas(fig)
        self.charts_layout.addWidget(canvas)

    def add_top_products(self, session, date_from, date_to):
        """Добавить ТОП товаров"""
        # Получаем данные
        top_products = session.query(
            Product.name,
            func.sum(OrderItem.quantity).label('total_quantity'),
            func.sum(OrderItem.quantity * OrderItem.price_at_moment).label('total_revenue')
        ).join(OrderItem).join(Order).filter(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to,
                Order.status == OrderStatus.DELIVERED
            )
        ).group_by(Product.id, Product.name).order_by(
            func.sum(OrderItem.quantity * OrderItem.price_at_moment).desc()
        ).limit(10).all()

        if not top_products:
            return

        # Создаем график
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        names = [p.name[:30] for p in top_products]
        revenues = [float(p.total_revenue) for p in top_products]

        ax.barh(names, revenues, color='#FF9800')
        ax.set_xlabel('Выручка (₽)')
        ax.set_title('ТОП-10 товаров по выручке')
        ax.grid(True, alpha=0.3, axis='x')

        fig.tight_layout()

        canvas = FigureCanvas(fig)
        self.charts_layout.addWidget(canvas)

    def add_top_clients(self, session, date_from, date_to):
        """Добавить ТОП клиентов"""
        # Получаем данные
        top_clients = session.query(
            Client.name,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_spent')
        ).join(Order).filter(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to,
                Order.status == OrderStatus.DELIVERED
            )
        ).group_by(Client.id, Client.name).order_by(
            func.sum(Order.total_amount).desc()
        ).limit(10).all()

        if not top_clients:
            return

        # Создаем график
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        names = [c.name[:30] for c in top_clients]
        spent = [float(c.total_spent) for c in top_clients]

        ax.barh(names, spent, color='#9C27B0')
        ax.set_xlabel('Сумма покупок (₽)')
        ax.set_title('ТОП-10 клиентов по сумме покупок')
        ax.grid(True, alpha=0.3, axis='x')

        fig.tight_layout()

        canvas = FigureCanvas(fig)
        self.charts_layout.addWidget(canvas)

    def add_managers_stats(self, session, date_from, date_to):
        """Добавить статистику по менеджерам"""
        # Получаем данные
        managers_stats = session.query(
            Manager.name,
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_revenue'),
            func.avg(Order.total_amount).label('avg_check')
        ).join(Order).filter(
            and_(
                Order.created_at >= date_from,
                Order.created_at <= date_to
            )
        ).group_by(Manager.id, Manager.name).order_by(
            func.count(Order.id).desc()
        ).all()

        if not managers_stats:
            return

        # Создаем график
        fig = Figure(figsize=(10, 5))
        ax = fig.add_subplot(111)

        names = [m.name for m in managers_stats]
        counts = [m.order_count for m in managers_stats]

        ax.bar(names, counts, color='#00BCD4')
        ax.set_ylabel('Количество заказов')
        ax.set_title('Статистика по менеджерам')
        ax.grid(True, alpha=0.3, axis='y')

        fig.tight_layout()

        canvas = FigureCanvas(fig)
        self.charts_layout.addWidget(canvas)
