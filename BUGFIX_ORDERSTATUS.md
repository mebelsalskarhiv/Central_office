# Исправление ошибки OrderStatus

## Проблема
```
AttributeError: type object 'OrderStatus' has no attribute 'IN_ASSEMBLY'
```

## Причина
В `reports_tab.py` использовались неправильные значения enum `OrderStatus`.

## Правильные значения в `models.py`
```python
class OrderStatus(enum.Enum):
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"
```

## Исправление в `reports_tab.py`
Заменено:
- `OrderStatus.IN_ASSEMBLY` → `OrderStatus.IN_PROGRESS`
- `OrderStatus.IN_TRANSIT` → удалено
- Добавлено: `OrderStatus.CANCELED`

## Статусы в комбобоксе
- Все
- Новые (NEW)
- В работе (IN_PROGRESS)
- Доставлено (DELIVERED)
- Отменено (CANCELED)

## Дата исправления
2026-05-03
