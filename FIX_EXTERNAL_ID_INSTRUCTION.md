# Инструкция по исправлению конфликта external_id

## Проблема
При импорте заказов от нового менеджера возникает ошибка:
```
UNIQUE constraint failed: clients.external_id
```

## Решение применено ✅
Код исправлен, теперь `external_id` формируется как `{PIN}-{CLIENT_ID}`, что делает его уникальным для каждого менеджера.

## Что нужно сделать

### Вариант 1: Пересоздать базу данных (рекомендуется для тестирования)

1. **Закрыть центральное приложение** (если запущено)

2. **Создать резервную копию БД:**
```bash
cd E:\WORK_RUCHEEK\OrderManager\Central_office\data
copy central.db central.db.backup
```

3. **Удалить старую БД:**
```bash
del central.db
```

4. **Запустить центральное приложение:**
```bash
cd E:\WORK_RUCHEEK\OrderManager\Central_office
python src/main.py
```

5. **Система автоматически создаст новую БД** без конфликтов

6. **Повторить синхронизацию** с мобильных устройств

### Вариант 2: Исправить существующую БД (для продакшена с данными)

Если в БД есть важные данные, которые нельзя потерять:

1. **Закрыть центральное приложение**

2. **Запустить скрипт исправления:**
```bash
cd E:\WORK_RUCHEEK\OrderManager\Central_office
python fix_external_id.py
```

3. **Скрипт fix_external_id.py** (создать этот файл):
```python
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sqlalchemy.orm import Session
from database.models import Client

db = get_database()

with Session(db.engine) as session:
    # Находим всех клиентов с external_id
    clients = session.query(Client).filter(Client.external_id.isnot(None)).all()
    
    print(f"Found {len(clients)} clients with external_id")
    
    # Обнуляем external_id у всех клиентов
    # Он будет установлен заново при следующей синхронизации
    for client in clients:
        print(f"Clearing external_id for client {client.phone}: {client.external_id} -> None")
        client.external_id = None
    
    session.commit()
    print("Done! All external_id cleared.")
```

4. **Запустить центральное приложение**

5. **Повторить синхронизацию** - external_id будет установлен правильно

## Проверка

После исправления:

1. Запустить центральное приложение
2. Выполнить синхронизацию от обоих менеджеров
3. Проверить вкладку "Клиенты"
4. Не должно быть ошибок UNIQUE constraint

## Что изменилось

**Было:**
- Менеджер 1232 создает клиента → `external_id = "CLIENT-2"`
- Менеджер 5678 создает клиента → `external_id = "CLIENT-2"` ❌ КОНФЛИКТ!

**Стало:**
- Менеджер 1232 создает клиента → `external_id = "1232-CLIENT-2"` ✅
- Менеджер 5678 создает клиента → `external_id = "5678-CLIENT-2"` ✅

**Важно:** Один телефон = один клиент в системе. Если оба менеджера создают клиента с одним телефоном, в БД будет один клиент с данными от последней синхронизации.

---

**Дата:** 01.05.2026
**Время:** 15:29
**Рекомендация:** Использовать Вариант 1 (пересоздать БД) для тестирования
