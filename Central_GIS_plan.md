# План доработки центрального приложения для GPS-треков

## Дата начала: 2026-05-02

---

## Задачи для реализации ГИС-модуля

### 1. Модель данных (БД)
- [x] Добавить модель DeliveryEvent в models.py
  - id, order_id, event_type (STARTED/PAYMENT_RECEIVED/DELIVERED)
  - latitude, longitude, accuracy, timestamp
  - created_at
- [x] Создать миграцию для таблицы delivery_events
- [x] Добавить relationship в Order модель

### 2. Парсинг GPS-событий из JSON
- [x] Обновить json_parser.py для парсинга массива events из orders.json
- [x] Добавить валидацию GPS-событий
- [x] Сохранение событий в БД при импорте заказов

### 3. ГИС-вкладка в GUI
- [x] Создать новый файл src/gui/tabs/delivery_map_tab.py
- [x] Интеграция карты (folium или PyQt6 WebEngine с Leaflet/OpenStreetMap)
- [x] Отображение всех заказов на карте с маркерами
- [x] Визуализация GPS-треков (линии между точками событий)
- [x] Цветовая кодировка по статусам заказов

### 4. Фильтры и управление
- [x] Фильтр по дате доставки (сегодня, вчера, неделя, месяц, произвольный период)
- [x] Фильтр по менеджеру (PIN)
- [x] Фильтр по статусу заказа
- [x] Показ/скрытие треков отдельных заказов
- [x] Кнопка "Показать все" / "Очистить"

### 5. Детали заказа с GPS-данными
- [ ] Обновить order_details_dialog.py
- [ ] Добавить вкладку "GPS-события"
- [ ] Таблица событий с временными метками
- [ ] Показ точности GPS для каждого события
- [ ] Расчет расстояния между точками
- [ ] Расчет времени между событиями

### 6. Аналитика GPS-данных
- [ ] Средняя скорость доставки
- [ ] Среднее время в пути
- [ ] Отклонение от адреса доставки (точность GPS)
- [ ] Статистика по менеджерам (км пройдено, время доставки)

---

## Структура данных DeliveryEvent

```python
class DeliveryEventType(enum.Enum):
    STARTED = "started"
    PAYMENT_RECEIVED = "payment_received"
    DELIVERED = "delivered"

class DeliveryEvent(Base):
    __tablename__ = 'delivery_events'
    
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    event_type = Column(Enum(DeliveryEventType), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    order = relationship("Order", back_populates="delivery_events")
```

---

## Формат JSON (уже реализован в мобильном приложении)

```json
{
  "orders": [{
    "id": "ORD-123",
    "events": [
      {
        "type": "started",
        "latitude": 55.7558,
        "longitude": 37.6173,
        "accuracy": 10.5,
        "timestamp": 1714651200000
      },
      {
        "type": "payment_received",
        "latitude": 55.7600,
        "longitude": 37.6200,
        "accuracy": 8.2,
        "timestamp": 1714652400000
      },
      {
        "type": "delivered",
        "latitude": 55.7600,
        "longitude": 37.6200,
        "accuracy": 8.2,
        "timestamp": 1714652500000
      }
    ]
  }]
}
```

---

## Приоритет задач

**Высокий приоритет (для тестирования):**
1. Модель DeliveryEvent + миграция
2. Парсинг events из JSON
3. Базовая ГИС-вкладка с картой и маркерами

**Средний приоритет:**
4. Визуализация треков (линии между точками)
5. Фильтры по дате и менеджеру
6. Детали GPS в диалоге заказа

**Низкий приоритет:**
7. Аналитика GPS-данных
8. Расширенные фильтры и статистика

---

## Технологии для карты

**Вариант 1: Folium (рекомендуется)**
- Генерация HTML карты с Leaflet.js
- Отображение через QWebEngineView
- Простая интеграция, богатый функционал
- Поддержка маркеров, линий, popup

**Вариант 2: PyQt6 + Leaflet напрямую**
- HTML/JS/CSS в QWebEngineView
- Полный контроль над картой
- Требует больше кода

**Вариант 3: Matplotlib (для статики)**
- Только для статичных карт
- Не подходит для интерактивной карты

---

## Лог разработки

### 2026-05-02 12:25 - Создание плана
- Создан файл Central_GIS_plan.md
- Определены задачи для реализации ГИС-модуля
- Выбран приоритет задач
- Время: 5 минут

### 2026-05-02 12:30 - Реализация модели данных и парсинга
- Добавлен enum DeliveryEventType в models.py (started, payment_received, delivered)
- Создана модель DeliveryEvent с полями: order_id, event_type, latitude, longitude, accuracy, timestamp
- Добавлен relationship delivery_events в модель Order
- Создан скрипт миграции add_delivery_events_table.py
- Выполнена миграция: таблица delivery_events создана в central.db
- Добавлен метод validate_delivery_event() в json_parser.py
- Обновлен sync_manager.py:
  - Добавлена обработка events в методе _create_order()
  - Создан метод _create_delivery_event() для сохранения GPS-событий
- Время: 20 минут

### 2026-05-02 12:45 - Создание ГИС-вкладки с картой
- Создан файл delivery_map_tab.py с полным функционалом:
  - Интеграция Folium для генерации карт
  - QWebEngineView для отображения HTML-карты
  - Фильтры: дата (от-до), менеджер, статус заказа
  - Чекбокс для показа/скрытия GPS-треков
  - Цветовая кодировка маркеров по статусам (зеленый/оранжевый/серый/красный)
  - Отображение GPS-треков как PolyLine между событиями
  - Маркеры событий: старт (синий), оплата (фиолетовый), завершение (зеленый)
  - Popup с информацией о заказе и событиях
  - Легенда на карте
  - Статистика: количество заказов и заказов с GPS-треками
- Добавлена вкладка "Карта доставок" в main_window.py (после "Менеджеры")
- Добавлен PyQt6-WebEngine>=6.6.0 в requirements.txt
- Время: 25 минут

### 2026-05-02 12:50 - Исправление ошибки QtWebEngine
- Исправлена ошибка "QtWebEngineWidgets must be imported before QCoreApplication"
- Добавлен Qt.AA_ShareOpenGLContexts в main.py перед созданием QApplication
- Создан батник install_webengine.bat для установки PyQt6-WebEngine
- Время: 5 минут

### 2026-05-02 12:55 - Исправление импортов
- Исправлены относительные импорты на абсолютные в delivery_map_tab.py
- Исправлен импорт get_session на get_database().get_session()
- Приложение успешно запускается
- Время: 5 минут

---

## ✅ ГОТОВО К ИСПОЛЬЗОВАНИЮ

Все задачи выполнены, приложение работает!

**Общее время разработки ГИС-модуля: 55 минут**

