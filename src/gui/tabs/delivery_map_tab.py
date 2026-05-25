"""
Вкладка карты доставок с GPS-треками
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QComboBox, QLabel, QDateEdit, QCheckBox
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings
from PyQt6.QtCore import QDate, QUrl
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import folium
from folium import plugins
import tempfile
import os

from database.models import Order, DeliveryEvent, Manager, OrderStatus, DeliveryEventType
from database.database import get_database


class DeliveryMapTab(QWidget):
    """Вкладка карты доставок"""

    def __init__(self):
        super().__init__()
        self.session: Session = None
        self.temp_map_file = None
        self.db = get_database()
        self.init_ui()
        self.load_data()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Панель фильтров
        filter_layout = QHBoxLayout()

        # Фильтр по дате
        filter_layout.addWidget(QLabel("Дата:"))
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate())
        self.date_from.setCalendarPopup(True)
        filter_layout.addWidget(self.date_from)

        filter_layout.addWidget(QLabel("до"))
        self.date_to = QDateEdit()
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filter_layout.addWidget(self.date_to)

        # Фильтр по менеджеру
        filter_layout.addWidget(QLabel("Менеджер:"))
        self.manager_combo = QComboBox()
        self.manager_combo.addItem("Все", None)
        filter_layout.addWidget(self.manager_combo)

        # Фильтр по статусу
        filter_layout.addWidget(QLabel("Статус:"))
        self.status_combo = QComboBox()
        self.status_combo.addItem("Все", None)
        self.status_combo.addItem("Новые", OrderStatus.NEW)
        self.status_combo.addItem("В работе", OrderStatus.IN_PROGRESS)
        self.status_combo.addItem("Доставлены", OrderStatus.DELIVERED)
        self.status_combo.addItem("Отменены", OrderStatus.CANCELED)
        filter_layout.addWidget(self.status_combo)

        # Чекбокс для отображения треков
        self.show_tracks_checkbox = QCheckBox("Показать треки")
        self.show_tracks_checkbox.setChecked(True)
        filter_layout.addWidget(self.show_tracks_checkbox)

        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить карту")
        self.refresh_btn.clicked.connect(self.load_data)
        filter_layout.addWidget(self.refresh_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Карта (растягивается на все доступное пространство)
        self.map_view = QWebEngineView()

        # Настройки WebEngine для загрузки внешних ресурсов
        settings = self.map_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)

        layout.addWidget(self.map_view, stretch=1)  # stretch=1 для растягивания карты

        # Статистика (фиксированная высота)
        stats_layout = QHBoxLayout()
        self.stats_label = QLabel("Заказов: 0 | С GPS-треками: 0")
        stats_layout.addWidget(self.stats_label)
        stats_layout.addStretch()
        layout.addLayout(stats_layout, stretch=0)  # stretch=0 для фиксированной высоты

        self.setLayout(layout)

    def load_data(self):
        """Загрузить данные и отобразить на карте"""
        try:
            self.session = self.db.get_session()

            # Загружаем менеджеров для фильтра
            self.load_managers()

            # Получаем фильтры
            date_from = self.date_from.date().toPyDate()
            date_to = self.date_to.date().toPyDate()
            manager_id = self.manager_combo.currentData()
            status = self.status_combo.currentData()
            show_tracks = self.show_tracks_checkbox.isChecked()

            # Формируем запрос
            query = self.session.query(Order).filter(
                Order.delivery_date >= datetime.combine(date_from, datetime.min.time()),
                Order.delivery_date <= datetime.combine(date_to, datetime.max.time())
            )

            if manager_id:
                query = query.filter(Order.manager_id == manager_id)

            if status:
                query = query.filter(Order.status == status)

            orders = query.all()

            # Создаем карту
            self.create_map(orders, show_tracks)

            # Обновляем статистику
            orders_with_tracks = sum(1 for order in orders if order.delivery_events)
            self.stats_label.setText(
                f"Заказов: {len(orders)} | С GPS-треками: {orders_with_tracks}"
            )

        except Exception as e:
            print(f"Error loading map data: {e}")
        finally:
            if self.session:
                self.session.close()

    def load_managers(self):
        """Загрузить список менеджеров"""
        current_manager = self.manager_combo.currentData()
        self.manager_combo.clear()
        self.manager_combo.addItem("Все", None)

        managers = self.session.query(Manager).filter(
            Manager.status == "ACTIVE"
        ).all()

        for manager in managers:
            self.manager_combo.addItem(
                f"{manager.name} ({manager.pin_code})",
                manager.id
            )

        # Восстанавливаем выбор
        if current_manager:
            index = self.manager_combo.findData(current_manager)
            if index >= 0:
                self.manager_combo.setCurrentIndex(index)

    def create_map(self, orders, show_tracks=True):
        """Создать карту с заказами и треками"""
        # Центр карты (Москва по умолчанию)
        center_lat = 55.751244
        center_lon = 37.618423

        # Если есть заказы с координатами, центрируем по ним
        coords = []
        for order in orders:
            if order.address_latitude and order.address_longitude:
                coords.append([order.address_latitude, order.address_longitude])

        if coords:
            center_lat = sum(c[0] for c in coords) / len(coords)
            center_lon = sum(c[1] for c in coords) / len(coords)

        # Создаем карту
        m = folium.Map(
            location=[center_lat, center_lon],
            zoom_start=12,
            tiles='OpenStreetMap'
        )

        # Цвета для статусов
        status_colors = {
            OrderStatus.NEW: 'green',
            OrderStatus.IN_PROGRESS: 'orange',
            OrderStatus.DELIVERED: 'gray',
            OrderStatus.CANCELED: 'red'
        }

        # Добавляем маркеры и треки для каждого заказа
        for order in orders:
            if not order.address_latitude or not order.address_longitude:
                continue

            color = status_colors.get(order.status, 'blue')

            # Создаем popup с информацией о заказе
            popup_html = f"""
            <div style="width: 250px;">
                <h4>Заказ {order.order_number}</h4>
                <p><b>Клиент:</b> {order.client.name}<br>
                <b>Телефон:</b> {order.client.phone}<br>
                <b>Адрес:</b> {order.address_text}<br>
                <b>Статус:</b> {order.status.value}<br>
                <b>Сумма:</b> {order.total_amount:.2f} ₽<br>
                <b>Менеджер:</b> {order.manager.name}</p>
            </div>
            """

            # Маркер адреса доставки
            folium.Marker(
                location=[order.address_latitude, order.address_longitude],
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"Заказ {order.order_number}",
                icon=folium.Icon(color=color, icon='home', prefix='fa')
            ).add_to(m)

            # Отображаем GPS-трек если есть события и включен показ треков
            if show_tracks and order.delivery_events:
                events = sorted(order.delivery_events, key=lambda e: e.timestamp)

                if len(events) > 0:
                    # Координаты трека
                    track_coords = [
                        [event.latitude, event.longitude]
                        for event in events
                    ]

                    # Линия трека
                    folium.PolyLine(
                        locations=track_coords,
                        color=color,
                        weight=3,
                        opacity=0.7,
                        tooltip=f"Трек заказа {order.order_number}"
                    ).add_to(m)

                    # Маркеры для каждого события
                    event_icons = {
                        DeliveryEventType.STARTED: ('play', 'blue'),
                        DeliveryEventType.PAYMENT_RECEIVED: ('credit-card', 'purple'),
                        DeliveryEventType.DELIVERED: ('check', 'green')
                    }

                    for event in events:
                        icon_name, icon_color = event_icons.get(
                            event.event_type,
                            ('circle', 'gray')
                        )

                        event_popup = f"""
                        <div>
                            <b>{event.event_type.value}</b><br>
                            Время: {event.timestamp.strftime('%H:%M:%S')}<br>
                            Точность: {event.accuracy:.1f}м
                        </div>
                        """

                        folium.CircleMarker(
                            location=[event.latitude, event.longitude],
                            radius=6,
                            popup=folium.Popup(event_popup, max_width=200),
                            color=icon_color,
                            fill=True,
                            fillColor=icon_color,
                            fillOpacity=0.8
                        ).add_to(m)

        # Добавляем легенду
        legend_html = '''
        <div style="position: fixed;
                    top: 10px; right: 10px; width: 180px;
                    background-color: white; border:2px solid grey; z-index:9999;
                    font-size:14px; padding: 10px">
        <p><b>Статусы заказов:</b></p>
        <p><i class="fa fa-map-marker" style="color:green"></i> Новый</p>
        <p><i class="fa fa-map-marker" style="color:orange"></i> В работе</p>
        <p><i class="fa fa-map-marker" style="color:gray"></i> Доставлен</p>
        <p><i class="fa fa-map-marker" style="color:red"></i> Отменён</p>
        <hr>
        <p><b>GPS-события:</b></p>
        <p><i class="fa fa-circle" style="color:blue"></i> Старт</p>
        <p><i class="fa fa-circle" style="color:purple"></i> Оплата</p>
        <p><i class="fa fa-circle" style="color:green"></i> Завершение</p>
        </div>
        '''
        m.get_root().html.add_child(folium.Element(legend_html))

        # Сохраняем карту во временный файл
        if self.temp_map_file:
            try:
                os.remove(self.temp_map_file)
            except:
                pass

        self.temp_map_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.html',
            delete=False
        ).name

        m.save(self.temp_map_file)

        # Загружаем карту в WebView
        self.map_view.setUrl(QUrl.fromLocalFile(self.temp_map_file))

    def closeEvent(self, event):
        """Очистка при закрытии"""
        if self.temp_map_file and os.path.exists(self.temp_map_file):
            try:
                os.remove(self.temp_map_file)
            except:
                pass
        super().closeEvent(event)
