# Формат обмена данными через WebDAV

## Структура папок на WebDAV

```
/webdav_root/
  /{PIN_CODE}/              # Папка менеджера (PIN = идентификатор)
    /incoming/              # Данные ОТ центральной системы К менеджеру
      products.json         # Товары с ценами и картинками
      settings.json         # Настройки (бонусы, проценты)
      sync_metadata.json    # Метаданные синхронизации
    /outgoing/              # Данные ОТ менеджера К центральной системе
      orders_{timestamp}.json       # Новые/измененные заказы
      clients_{timestamp}.json      # Новые/измененные клиенты
      payments_{timestamp}.json     # Координаты оплат
      sync_ack_{timestamp}.json     # Подтверждение получения данных
```

## Принципы обмена

1. **Инкрементальная синхронизация**: передаются только изменения с момента последней синхронизации
2. **Timestamp-based**: каждая запись имеет `updated_at` для определения актуальности
3. **Conflict resolution**: Last-Write-Wins по `updated_at`
4. **Batch processing**: данные передаются пакетами с timestamp в имени файла
5. **Acknowledgment**: после обработки файл перемещается в `/processed/`

## Формат данных

### 1. products.json (incoming)

Полный список активных товаров с ценами и картинками.

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "products": [
    {
      "id": "PROD-001",
      "name": "Молоко 3.2%",
      "category": "Молочные продукты",
      "price": 89.90,
      "unit": "шт",
      "image_url": "https://cdn.example.com/products/milk.jpg",
      "image_base64": null,
      "is_active": true,
      "barcode": "4607025392015",
      "description": "Молоко пастеризованное 3.2%, 1л",
      "updated_at": 1714521600000
    }
  ]
}
```

**Поля:**
- `id` (string): Уникальный ID товара (генерируется центральной системой)
- `name` (string): Название товара
- `category` (string): Категория
- `price` (float): Цена в рублях
- `unit` (string): Единица измерения (шт, кг, л)
- `image_url` (string, optional): URL картинки
- `image_base64` (string, optional): Base64 картинки (если нет URL)
- `is_active` (boolean): Активен ли товар (для стоп-листа)
- `barcode` (string, optional): Штрихкод
- `description` (string, optional): Описание
- `updated_at` (long): Timestamp последнего обновления

### 2. settings.json (incoming)

Настройки для менеджера.

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "bonus_settings": {
    "enabled": true,
    "earn_percentage": 5.0,
    "min_order_amount": 500.0,
    "max_bonus_per_order": 1000.0,
    "expiry_days": 365
  },
  "delivery_settings": {
    "default_time_slots": ["10:00-12:00", "12:00-14:00", "14:00-16:00", "16:00-18:00"],
    "min_order_amount": 300.0
  },
  "sync_settings": {
    "sync_interval_minutes": 10,
    "keep_orders_days": 1,
    "auto_cleanup": true
  }
}
```

**Секции:**
- `bonus_settings`: Настройки бонусной системы
  - `enabled`: Включена ли система бонусов
  - `earn_percentage`: Процент начисления бонусов от суммы заказа
  - `min_order_amount`: Минимальная сумма заказа для начисления бонусов
  - `max_bonus_per_order`: Максимум бонусов за один заказ
  - `expiry_days`: Срок действия бонусов (дни)
- `delivery_settings`: Настройки доставки
  - `default_time_slots`: Временные слоты по умолчанию
  - `min_order_amount`: Минимальная сумма заказа
- `sync_settings`: Настройки синхронизации
  - `sync_interval_minutes`: Интервал синхронизации
  - `keep_orders_days`: Сколько дней хранить заказы локально
  - `auto_cleanup`: Автоматическая очистка старых заказов

### 3. orders_{timestamp}.json (outgoing)

Новые или измененные заказы от менеджера.

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "manager_pin": "1234",
  "device_id": "android-abc123",
  "orders": [
    {
      "id": "ORD-20260430-123456",
      "order_number": "ORD-20260430-123456",
      "client_id": "CLIENT-001",
      "client_phone": "+79281680946",
      "client_name": "Иван Иванов",
      "address_id": "ADDR-001",
      "address_text": "ул. Ленина, д. 10, кв. 5",
      "address_latitude": 47.2147415,
      "address_longitude": 39.7189647,
      "delivery_date": 1714521600000,
      "delivery_time_slot": "10:00-12:00",
      "status": "DELIVERED",
      "payment_status": "PAID",
      "payment_type": "CASH",
      "total_amount": 1250.50,
      "bonus_used": 50.0,
      "bonus_earned": 60.0,
      "comment": "Позвонить за 30 минут",
      "items": [
        {
          "product_id": "PROD-001",
          "product_name": "Молоко 3.2%",
          "quantity": 2.0,
          "price_at_moment": 89.90,
          "sum": 179.80
        }
      ],
      "payment_location": {
        "latitude": 47.2147415,
        "longitude": 39.7189647,
        "accuracy": 10.5,
        "timestamp": 1714525200000
      },
      "created_at": 1714521600000,
      "updated_at": 1714525200000,
      "sync_status": "NOT_SYNCED"
    }
  ]
}
```

**Поля заказа:**
- `id` (string): Уникальный ID заказа (генерируется на устройстве)
- `order_number` (string): Номер заказа (для отображения)
- `client_id` (string): ID клиента
- `client_phone` (string): Телефон клиента (нормализованный)
- `client_name` (string): Имя клиента
- `address_id` (string, optional): ID адреса из справочника клиента
- `address_text` (string): Текст адреса
- `address_latitude` (float, optional): Широта адреса доставки
- `address_longitude` (float, optional): Долгота адреса доставки
- `delivery_date` (long): Дата доставки (timestamp)
- `delivery_time_slot` (string): Временной слот
- `status` (enum): NEW, IN_PROGRESS, DELIVERED, CANCELED
- `payment_status` (enum): UNPAID, PAID, PARTIALLY_PAID
- `payment_type` (enum): CASH, CARD, TRANSFER, MIXED
- `total_amount` (float): Итоговая сумма (после вычета бонусов)
- `bonus_used` (float): Использовано бонусов
- `bonus_earned` (float): Начислено бонусов
- `comment` (string, optional): Комментарий к заказу
- `items` (array): Позиции заказа
- `payment_location` (object, optional): Координаты места оплаты
  - `latitude` (float): Широта
  - `longitude` (float): Долгота
  - `accuracy` (float): Точность в метрах
  - `timestamp` (long): Время фиксации координат
- `created_at` (long): Время создания
- `updated_at` (long): Время последнего обновления
- `sync_status` (enum): NOT_SYNCED, SYNCED, CONFLICT

### 4. clients_{timestamp}.json (outgoing)

Новые или измененные клиенты от менеджера.

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "manager_pin": "1234",
  "device_id": "android-abc123",
  "clients": [
    {
      "id": "CLIENT-001",
      "phone": "+79281680946",
      "name": "Иван Иванов",
      "bonus_balance": 150.50,
      "total_orders": 5,
      "total_spent": 5000.00,
      "last_order_date": 1714521600000,
      "notes": "Постоянный клиент",
      "addresses": [
        {
          "id": "ADDR-001",
          "address_text": "ул. Ленина, д. 10, кв. 5",
          "street": "ул. Ленина",
          "house": "10",
          "apartment": "5",
          "latitude": 47.2147415,
          "longitude": 39.7189647,
          "is_default": true,
          "label": "Дом",
          "created_at": 1714521600000,
          "updated_at": 1714521600000
        }
      ],
      "created_at": 1714521600000,
      "updated_at": 1714525200000
    }
  ]
}
```

**Поля клиента:**
- `id` (string): Уникальный ID клиента
- `phone` (string): Телефон (нормализованный, уникальный ключ)
- `name` (string): Имя клиента
- `bonus_balance` (float): Текущий баланс бонусов
- `total_orders` (int): Всего заказов
- `total_spent` (float): Всего потрачено
- `last_order_date` (long, optional): Дата последнего заказа
- `notes` (string, optional): Примечания
- `addresses` (array): Адреса клиента
- `created_at` (long): Время создания
- `updated_at` (long): Время последнего обновления

**Поля адреса:**
- `id` (string): Уникальный ID адреса
- `address_text` (string): Полный текст адреса
- `street` (string, optional): Улица
- `house` (string, optional): Дом
- `apartment` (string, optional): Квартира
- `latitude` (float, optional): Широта
- `longitude` (float, optional): Долгота
- `is_default` (boolean): Адрес по умолчанию
- `label` (string, optional): Метка (Дом, Работа, и т.д.)
- `created_at` (long): Время создания
- `updated_at` (long): Время последнего обновления

### 5. payments_{timestamp}.json (outgoing)

Координаты мест оплаты (для аналитики и контроля).

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "manager_pin": "1234",
  "device_id": "android-abc123",
  "payments": [
    {
      "order_id": "ORD-20260430-123456",
      "order_number": "ORD-20260430-123456",
      "amount": 1250.50,
      "payment_type": "CASH",
      "location": {
        "latitude": 47.2147415,
        "longitude": 39.7189647,
        "accuracy": 10.5,
        "altitude": 50.0,
        "speed": 0.0
      },
      "timestamp": 1714525200000,
      "device_info": {
        "model": "Samsung Galaxy S21",
        "os_version": "Android 12",
        "app_version": "1.0.0"
      }
    }
  ]
}
```

**Поля оплаты:**
- `order_id` (string): ID заказа
- `order_number` (string): Номер заказа
- `amount` (float): Сумма оплаты
- `payment_type` (enum): Тип оплаты
- `location` (object): Координаты места оплаты
  - `latitude` (float): Широта
  - `longitude` (float): Долгота
  - `accuracy` (float): Точность в метрах
  - `altitude` (float, optional): Высота над уровнем моря
  - `speed` (float, optional): Скорость движения
- `timestamp` (long): Время оплаты
- `device_info` (object, optional): Информация об устройстве

### 6. sync_metadata.json (incoming)

Метаданные синхронизации для клиента.

```json
{
  "version": 1,
  "timestamp": 1714521600000,
  "last_sync": {
    "products": 1714521600000,
    "settings": 1714521600000,
    "orders_processed": 1714525200000
  },
  "server_info": {
    "version": "1.0.0",
    "timezone": "Europe/Moscow"
  }
}
```

### 7. sync_ack_{timestamp}.json (outgoing)

Подтверждение получения данных от центральной системы.

```json
{
  "version": 1,
  "timestamp": 1714525200000,
  "manager_pin": "1234",
  "device_id": "android-abc123",
  "acknowledged": {
    "products": 1714521600000,
    "settings": 1714521600000
  },
  "errors": []
}
```

## Алгоритм синхронизации

### Загрузка данных (Download)

1. Проверить наличие файлов в `/incoming/`
2. Прочитать `sync_metadata.json` для определения версий
3. Загрузить `products.json` если версия новее локальной
4. Загрузить `settings.json` если версия новее локальной
5. Применить изменения к локальной БД
6. Отправить `sync_ack_{timestamp}.json` в `/outgoing/`

### Выгрузка данных (Upload)

1. Выбрать записи с `sync_status = NOT_SYNCED` или `updated_at > last_sync`
2. Сформировать JSON файлы:
   - `orders_{timestamp}.json` - новые/измененные заказы
   - `clients_{timestamp}.json` - новые/измененные клиенты
   - `payments_{timestamp}.json` - координаты оплат
3. Загрузить файлы в `/outgoing/`
4. Пометить записи как `sync_status = SYNCED`

### Очистка старых данных

1. Удалить заказы старше `keep_orders_days` (кроме статуса IN_PROGRESS)
2. Удалить обработанные файлы из `/outgoing/` старше 7 дней
3. Архивировать старые данные на центральной системе

## Обработка конфликтов

**Стратегия: Last-Write-Wins**

1. Сравнить `updated_at` локальной и серверной записи
2. Если серверная запись новее - применить изменения с сервера
3. Если локальная запись новее - отправить на сервер
4. При равных timestamp - приоритет у сервера

**Исключения:**
- Заказы со статусом DELIVERED не перезаписываются
- Баланс бонусов клиента рассчитывается на сервере (авторитетный источник)

## Безопасность

1. **Аутентификация**: PIN-код = имя папки на WebDAV
2. **Шифрование**: HTTPS для WebDAV
3. **Валидация**: JSON Schema для всех форматов
4. **Логирование**: Все операции синхронизации логируются
5. **Backup**: Автоматическое резервное копирование перед применением изменений

## Производительность

1. **Batch size**: Максимум 100 заказов/клиентов в одном файле
2. **Compression**: Опционально gzip для больших файлов
3. **Incremental**: Только изменения, не полные дампы
4. **Cleanup**: Автоматическая очистка старых файлов
5. **Retry**: Повтор при ошибках с экспоненциальной задержкой
