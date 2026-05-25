"""
Утилиты для работы с датами и временем
"""
from datetime import datetime
from typing import Union, Optional


def safe_datetime(value: Union[int, float, datetime, None]) -> Optional[datetime]:
    """
    Безопасное преобразование timestamp в datetime

    Args:
        value: Timestamp в миллисекундах, datetime объект или None

    Returns:
        datetime объект или None
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        return value

    # Предполагаем, что это timestamp в миллисекундах
    try:
        return datetime.fromtimestamp(value / 1000)
    except (TypeError, ValueError, OSError):
        return None


def format_datetime(value: Union[int, float, datetime, None], format_str: str = "%d.%m.%Y %H:%M") -> str:
    """
    Форматирование даты/времени

    Args:
        value: Timestamp в миллисекундах, datetime объект или None
        format_str: Формат вывода

    Returns:
        Отформатированная строка или "-"
    """
    dt = safe_datetime(value)
    if dt is None:
        return "-"

    return dt.strftime(format_str)


def format_date(value: Union[int, float, datetime, None]) -> str:
    """
    Форматирование даты (без времени)

    Args:
        value: Timestamp в миллисекундах, datetime объект или None

    Returns:
        Отформатированная строка или "-"
    """
    return format_datetime(value, "%d.%m.%Y")
