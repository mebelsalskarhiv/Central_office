"""
Утилиты для работы с изображениями
"""
from PIL import Image
import os
from pathlib import Path


class ImageUtils:
    """Утилиты для обработки изображений"""

    @staticmethod
    def resize_and_crop(image_path: str, output_path: str, size: tuple = (800, 800), quality: int = 85):
        """
        Изменить размер и обрезать изображение с сохранением пропорций

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения результата
            size: Целевой размер (ширина, высота)
            quality: Качество JPEG (1-100)
        """
        try:
            # Открываем изображение
            img = Image.open(image_path)

            # Конвертируем в RGB если нужно
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background

            # Вычисляем пропорции
            img_ratio = img.width / img.height
            target_ratio = size[0] / size[1]

            if img_ratio > target_ratio:
                # Изображение шире целевого - обрезаем по ширине
                new_height = size[1]
                new_width = int(new_height * img_ratio)
            else:
                # Изображение выше целевого - обрезаем по высоте
                new_width = size[0]
                new_height = int(new_width / img_ratio)

            # Изменяем размер
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Обрезаем до целевого размера (центрируем)
            left = (new_width - size[0]) // 2
            top = (new_height - size[1]) // 2
            right = left + size[0]
            bottom = top + size[1]

            img = img.crop((left, top, right, bottom))

            # Создаем папку если не существует
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Сохраняем
            img.save(output_path, 'JPEG', quality=quality, optimize=True)

            return True

        except Exception as e:
            print(f"Error processing image: {e}")
            return False

    @staticmethod
    def create_thumbnail(image_path: str, output_path: str, size: tuple = (200, 200)):
        """
        Создать миниатюру изображения

        Args:
            image_path: Путь к исходному изображению
            output_path: Путь для сохранения миниатюры
            size: Размер миниатюры
        """
        return ImageUtils.resize_and_crop(image_path, output_path, size, quality=80)

    @staticmethod
    def get_image_storage_path(base_dir: str = None) -> Path:
        """
        Получить путь к папке хранения изображений

        Args:
            base_dir: Базовая директория (если None, используется data/images)

        Returns:
            Path: Путь к папке изображений
        """
        if base_dir is None:
            base_dir = Path(__file__).parent.parent.parent.parent / "data" / "images"
        else:
            base_dir = Path(base_dir)

        base_dir.mkdir(parents=True, exist_ok=True)
        return base_dir

    @staticmethod
    def save_product_image(source_path: str, product_id: str) -> tuple:
        """
        Сохранить изображение товара

        Args:
            source_path: Путь к исходному файлу
            product_id: ID товара

        Returns:
            tuple: (путь к полному изображению, путь к миниатюре) или (None, None) при ошибке
        """
        try:
            storage_path = ImageUtils.get_image_storage_path()

            # Создаем имена файлов
            ext = os.path.splitext(source_path)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                ext = '.jpg'

            full_filename = f"product_{product_id}{ext}"
            thumb_filename = f"product_{product_id}_thumb{ext}"

            full_path = storage_path / full_filename
            thumb_path = storage_path / thumb_filename

            # Обрабатываем изображения
            if ImageUtils.resize_and_crop(source_path, str(full_path), size=(800, 800)):
                ImageUtils.create_thumbnail(source_path, str(thumb_path), size=(200, 200))
                return (str(full_path), str(thumb_path))

            return (None, None)

        except Exception as e:
            print(f"Error saving product image: {e}")
            return (None, None)
