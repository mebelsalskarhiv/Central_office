# Исправление печати отчета для кассира

## Проблема
```
AttributeError: 'QTableWidget' object has no attribute 'document'
```

## Причина
`QTableWidget` не имеет метода `document()`. Для печати нужно использовать `QTextDocument` с HTML.

## Решение

### 1. Добавлены импорты
```python
from PyQt6.QtCore import QDate, Qt, QSizeF
from PyQt6.QtGui import QFont, QTextDocument
```

### 2. Исправлен метод `print_cashier_report`
```python
def print_cashier_report(self):
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    dialog = QPrintDialog(printer, self)

    if dialog.exec() == QPrintDialog.DialogCode.Accepted:
        # Формируем HTML для печати
        html = self.generate_cashier_html()

        # Создаем документ для печати
        document = QTextDocument()
        document.setHtml(html)
        document.setPageSize(QSizeF(printer.pageRect(QPrinter.Unit.Point).size()))
        document.print(printer)
```

## Как работает
1. Генерируется HTML-таблица с данными отчета
2. Создается `QTextDocument` и загружается HTML
3. Устанавливается размер страницы принтера
4. Документ отправляется на печать

## Дата исправления
2026-05-03
