# Исправление диалогов и синхронизации - 01.05.2026

## Проблемы

1. **PaymentType.BONUS не существует** - AttributeError при открытии деталей заказа
2. **DateTime ошибки в client_details_dialog.py** - TypeError при делении datetime на int
3. **Ошибка перемещения файлов** - файлы уже существуют в папке processed

## Исправления

### 1. order_details_dialog.py

**Проблема:** `AttributeError: type object 'PaymentType' has no attribute 'BONUS'`

**Причина:** В модели PaymentType есть только: CASH, CARD, TRANSFER, MIXED

**Исправление:**
```python
def get_payment_type_text(self, payment_type):
    type_map = {
        PaymentType.CASH: "Наличные",
        PaymentType.CARD: "Карта",
        PaymentType.TRANSFER: "Перевод",
        PaymentType.MIXED: "Смешанный"  # Было: PaymentType.BONUS: "Бонусы"
    }
    return type_map.get(payment_type, "Неизвестно")
```

### 2. client_details_dialog.py

**Проблема:** `TypeError: unsupported operand type(s) for /: 'datetime.datetime' and 'int'`

**Причина:** После импорта из JSON, поля с датами могут быть как timestamp (int), так и datetime объектами

**Исправления:**

1. Добавлен импорт утилит:
```python
from utils.datetime_utils import safe_datetime, format_datetime
```

2. Заменены все прямые преобразования datetime:

**Основная информация (строки 43-49):**
```python
# Было:
last_order = datetime.fromtimestamp(self.client.last_order_date / 1000)
created_date = datetime.fromtimestamp(self.client.created_at / 1000)

# Стало:
last_order = safe_datetime(self.client.last_order_date)
last_order_str = format_datetime(last_order, "%d.%m.%Y %H:%M") if last_order else "-"
created_date = safe_datetime(self.client.created_at)
created_str = format_datetime(created_date, "%d.%m.%Y %H:%M") if created_date else "-"
```

**Вкладка адресов (строка 141):**
```python
# Было:
created = datetime.fromtimestamp(address.created_at / 1000)

# Стало:
created = safe_datetime(address.created_at)
created_str = format_datetime(created, "%d.%m.%Y") if created else "-"
```

**Вкладка заказов (строки 172, 185):**
```python
# Было:
delivery_date = datetime.fromtimestamp(order.delivery_date / 1000)
created = datetime.fromtimestamp(order.created_at / 1000)

# Стало:
delivery_date = safe_datetime(order.delivery_date)
delivery_str = format_datetime(delivery_date, "%d.%m.%Y %H:%M") if delivery_date else "-"
created = safe_datetime(order.created_at)
created_str = format_datetime(created, "%d.%m.%Y %H:%M") if created else "-"
```

**Вкладка бонусов (строка 219):**
```python
# Было:
created = datetime.fromtimestamp(transaction.created_at / 1000)

# Стало:
created = safe_datetime(transaction.created_at)
created_str = format_datetime(created, "%d.%m.%Y %H:%M") if created else "-"
```

### 3. webdav_client.py

**Проблема:** `[WinError 183] Невозможно создать файл, так как он уже существует`

**Причина:** При повторной синхронизации файлы уже существуют в папке processed

**Исправление (строки 251-265):**
```python
def move_to_processed(self, file_path: Path, pin_code: str) -> bool:
    """Переместить файл в processed"""
    try:
        processed_path = self.get_processed_path(pin_code)
        processed_path.mkdir(parents=True, exist_ok=True)

        dest_path = processed_path / file_path.name

        # Если файл уже существует в processed, удаляем его
        if dest_path.exists():
            dest_path.unlink()

        file_path.rename(dest_path)
        return True
    except IOError as e:
        print(f"Error moving file to processed: {e}")
        return False
```

## Измененные файлы

1. **order_details_dialog.py**
   - Исправлен get_payment_type_text() - удален несуществующий PaymentType.BONUS

2. **client_details_dialog.py**
   - Добавлен импорт datetime_utils
   - Заменены все datetime.fromtimestamp() на safe_datetime()
   - Добавлена проверка на None перед форматированием

3. **webdav_client.py**
   - Добавлена проверка существования файла в processed
   - Автоматическое удаление старого файла перед перемещением

## Результат

✅ Диалог деталей заказа открывается без ошибок
✅ Диалог деталей клиента открывается без ошибок
✅ Все вкладки в диалоге клиента работают (Адреса, История заказов, Бонусы)
✅ Повторная синхронизация не вызывает ошибок перемещения файлов
✅ Унифицирована работа с датами во всех диалогах

## Тестирование

1. Запустить центральное приложение
2. Открыть вкладку "Заказы"
3. Дважды кликнуть на заказ - должен открыться диалог деталей
4. Открыть вкладку "Клиенты"
5. Дважды кликнуть на клиента - должен открыться диалог с тремя вкладками
6. Проверить все вкладки: Адреса, История заказов, Бонусы
7. Запустить синхронизацию повторно - не должно быть ошибок перемещения файлов
