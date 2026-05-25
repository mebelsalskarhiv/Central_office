# Последнее исправление - 01.05.2026

## Проблема

При открытии диалога клиента в центральной системе возникала ошибка:

```
AttributeError: 'BonusTransaction' object has no attribute 'transaction_type'
```

## Причина

В модели `BonusTransaction` поле называется `type`, а не `transaction_type`.

**Модель (database/models.py, строка 285):**
```python
class BonusTransaction(Base):
    type = Column(Enum(BonusTransactionType), nullable=False)  # ✅ Правильное имя
```

**Код в диалоге использовал неправильное имя:**
```python
transaction.transaction_type.name  # ❌ Неправильно
```

## Исправление

**Файл:** `client_details_dialog.py` (строки 223-228)

**Было:**
```python
type_text = "Начисление" if transaction.transaction_type.name == "EARNED" else "Списание"
amount_text = f"+{transaction.amount:.0f}" if transaction.transaction_type.name == "EARNED" else f"-{transaction.amount:.0f}"
```

**Стало:**
```python
type_text = "Начисление" if transaction.type.name == "EARNED" else "Списание"
amount_text = f"+{transaction.amount:.0f}" if transaction.type.name == "EARNED" else f"-{transaction.amount:.0f}"
```

## Результат

✅ Диалог клиента открывается без ошибок
✅ Вкладка "Бонусы" отображает транзакции корректно
✅ Все три вкладки работают: Адреса, История заказов, Бонусы

## Тестирование

```bash
cd E:\WORK_RUCHEEK\OrderManager\Central_office
python src/main.py
```

1. Открыть вкладку "Клиенты"
2. Дважды кликнуть на клиента
3. Проверить все три вкладки:
   - ✅ Адреса
   - ✅ История заказов
   - ✅ Бонусы

---

**Дата:** 01.05.2026
**Время:** 14:37
**Статус:** ✅ Исправлено и протестировано
