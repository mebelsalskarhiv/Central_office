"""
Создание иконки для OrderManager Central Office
"""
from PIL import Image, ImageDraw, ImageFont

# Создаем изображение 256x256
size = 256
img = Image.new('RGB', (size, size), color='#1e3a8a')  # Темно-синий фон
draw = ImageDraw.Draw(img)

# Рисуем документ/заказ
doc_color = '#ffffff'
doc_x = size // 2 - 60
doc_y = size // 2 - 80
doc_width = 120
doc_height = 160

# Основной прямоугольник документа
draw.rectangle(
    [doc_x, doc_y, doc_x + doc_width, doc_y + doc_height],
    fill=doc_color,
    outline='#cbd5e1',
    width=3
)

# Загнутый уголок
corner_size = 30
draw.polygon([
    (doc_x + doc_width, doc_y),
    (doc_x + doc_width - corner_size, doc_y),
    (doc_x + doc_width, doc_y + corner_size)
], fill='#cbd5e1')

# Линии текста на документе
line_color = '#3b82f6'
line_y = doc_y + 40
for i in range(5):
    draw.rectangle(
        [doc_x + 15, line_y + i * 20, doc_x + doc_width - 15, line_y + i * 20 + 8],
        fill=line_color if i < 3 else '#94a3b8'
    )

# Галочка (checkmark) - символ выполненного заказа
check_color = '#10b981'  # Зеленый
check_x = doc_x + doc_width + 20
check_y = doc_y + doc_height - 50

# Круг для галочки
draw.ellipse(
    [check_x - 25, check_y - 25, check_x + 25, check_y + 25],
    fill=check_color,
    outline='#059669',
    width=3
)

# Галочка
draw.line([(check_x - 10, check_y), (check_x - 3, check_y + 10)], fill='white', width=5)
draw.line([(check_x - 3, check_y + 10), (check_x + 12, check_y - 8)], fill='white', width=5)

# Сохраняем в разных размерах для ICO
sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
icons = []
for icon_size in sizes:
    resized = img.resize(icon_size, Image.Resampling.LANCZOS)
    icons.append(resized)

# Сохраняем как ICO
icons[0].save('central_office.ico', format='ICO', sizes=[(s[0], s[1]) for s in sizes], append_images=icons[1:])
print("Icon created: central_office.ico")
