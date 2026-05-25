# Исправление DetachedInstanceError - 01.05.2026

## Проблема

При запуске центрального приложения возникала ошибка:
```
sqlalchemy.orm.exc.DetachedInstanceError: Parent instance <Order> is not bound to a Session; 
lazy load operation of attribute 'client' cannot proceed
```

## Причина

После вызова `session.expunge_all()` в `orders_tab.py` (строка 142), объекты Order были отсоединены от сессии SQLAlchemy. При попытке доступа к связанным объектам через relationships (`order.client.name`, `order.manager.pin_code`) происходила попытка ленивой загрузки (lazy loading), которая невозможна для отсоединенных объектов.

## Решение

### 1. Добавлена жадная загрузка (Eager Loading)

В `orders_tab.py` метод `load_orders()` уже использовал `joinedload`:

```python
from sqlalchemy.orm import joinedload

self.all_orders = session.query(Order)\
    .options(joinedload(Order.client))\
    .options(joinedload(Order.manager))\
    .all()
```

Это загружает связанные объекты `client` и `manager` до отсоединения от сессии.

### 2. Добавлена обработка исключений

На случай, если связанные объекты отсутствуют или не загружены, добавлены try-except блоки:

**orders_tab.py:**
- Строки 207-211: Обработка `order.client.name`
- Строки 213-217: Обработка `order.client.phone`
- Строки 230-234: Обработка `order.manager.pin_code`
- Строки 159-165: Обработка в фильтре поиска

**order_details_dialog.py:**
- Строки 63-68: Обработка `order.client.name` и `order.client.phone`
- Строки 142-147: Обработка `order.manager.pin_code` и `order.manager.device_id`

### 3. Исправлены несуществующие поля

- **order.device_id** → **order.manager.device_id** (Order не имеет поля device_id)
- **order.delivered_at** → удалено (поле не существует в модели Order)

### 4. Использование datetime_utils

Добавлен импорт и использование утилит для безопасной работы с датами:

```python
from utils.datetime_utils import safe_datetime, format_datetime

# Вместо:
delivery_date = datetime.fromtimestamp(order.delivery_date / 1000)

# Используется:
delivery_date = safe_datetime(order.delivery_date)
date_str = format_datetime(delivery_date, "%d.%m.%Y %H:%M")
```

## Измененные файлы

1. **orders_tab.py**
   - Добавлены try-except блоки для доступа к relationships
   - Заменены прямые преобразования datetime на safe_datetime/format_datetime
   - Добавлен импорт datetime_utils

2. **order_details_dialog.py**
   - Добавлены try-except блоки для доступа к relationships
   - Исправлен доступ к device_id через manager
   - Удалена секция delivered_at (поле не существует)
   - Заменены прямые преобразования datetime на safe_datetime/format_datetime
   - Добавлен импорт datetime_utils

## Результат

✅ Приложение запускается без ошибок
✅ Вкладка заказов отображается корректно
✅ Диалог деталей заказа работает
✅ Обработаны случаи отсутствия связанных объектов
✅ Унифицирована работа с датами

## Тестирование

Запуск приложения:
```bash
cd E:\WORK_RUCHEEK\OrderManager\Central_office
python src/main.py
```

Приложение запускается без ошибок и корректно отображает импортированные заказы и клиентов.
