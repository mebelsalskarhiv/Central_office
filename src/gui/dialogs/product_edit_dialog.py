"""
Диалог редактирования товара
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QDoubleSpinBox, QCheckBox,
    QMessageBox, QTextEdit, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from sqlalchemy.orm import Session
from datetime import datetime
import os

from database.database import get_database
from database.models import Product
from gui.utils.image_utils import ImageUtils


class ProductEditDialog(QDialog):
    """Диалог редактирования товара"""

    def __init__(self, product, parent=None):
        super().__init__(parent)
        self.product = product
        self.db = get_database()
        self.is_new = product is None
        self.uploaded_image_path = None
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        title = "Добавить товар" if self.is_new else f"Редактировать: {self.product.name}"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Форма
        form_layout = QFormLayout()

        # Артикул
        self.sku_input = QLineEdit()
        if not self.is_new and self.product.external_id:
            self.sku_input.setText(self.product.external_id)
        form_layout.addRow("Артикул:", self.sku_input)

        # Название
        self.name_input = QLineEdit()
        if not self.is_new:
            self.name_input.setText(self.product.name)
        form_layout.addRow("Название*:", self.name_input)

        # Категория
        self.category_input = QLineEdit()
        if not self.is_new and self.product.category:
            self.category_input.setText(self.product.category)
        form_layout.addRow("Категория:", self.category_input)

        # Цена
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0, 999999.99)
        self.price_input.setDecimals(2)
        self.price_input.setSuffix(" ₽")
        if not self.is_new:
            self.price_input.setValue(self.product.price)
        form_layout.addRow("Цена*:", self.price_input)

        # Единица измерения
        self.unit_input = QLineEdit()
        if not self.is_new:
            self.unit_input.setText(self.product.unit)
        else:
            self.unit_input.setText("шт")
        form_layout.addRow("Единица:", self.unit_input)

        # Штрихкод
        self.barcode_input = QLineEdit()
        if not self.is_new and self.product.barcode:
            self.barcode_input.setText(self.product.barcode)
        form_layout.addRow("Штрихкод:", self.barcode_input)

        # Изображение
        image_layout = QHBoxLayout()

        self.image_url_input = QLineEdit()
        if not self.is_new:
            # Показываем image_path или image_url
            display_path = self.product.image_path or self.product.image_url
            if display_path:
                self.image_url_input.setText(display_path)
        image_layout.addWidget(self.image_url_input)

        upload_btn = QPushButton("Загрузить файл")
        upload_btn.clicked.connect(self.upload_image)
        image_layout.addWidget(upload_btn)

        form_layout.addRow("Изображение:", image_layout)

        # Превью изображения
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(200, 200)
        self.image_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_preview.setStyleSheet("border: 1px solid #ccc; background: #f5f5f5;")
        if not self.is_new:
            image_source = self.product.image_path or self.product.image_url
            if image_source and os.path.exists(image_source):
                self.load_image_preview(image_source)
            else:
                self.image_preview.setText("Нет изображения")
        else:
            self.image_preview.setText("Нет изображения")
        form_layout.addRow("", self.image_preview)

        # Активен
        self.is_active_checkbox = QCheckBox("Товар активен (доступен для заказа)")
        if not self.is_new:
            self.is_active_checkbox.setChecked(self.product.is_active)
        else:
            self.is_active_checkbox.setChecked(True)
        form_layout.addRow("", self.is_active_checkbox)

        layout.addLayout(form_layout)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_product)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def upload_image(self):
        """Загрузить изображение из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение",
            "",
            "Изображения (*.png *.jpg *.jpeg *.gif *.webp);;Все файлы (*.*)"
        )

        if file_path:
            self.uploaded_image_path = file_path
            self.image_url_input.setText(os.path.basename(file_path))
            self.load_image_preview(file_path)

    def load_image_preview(self, image_path):
        """Загрузить превью изображения"""
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(
                    200, 200,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.image_preview.setPixmap(scaled_pixmap)
            else:
                self.image_preview.setText("Ошибка загрузки")
        except Exception as e:
            self.image_preview.setText("Ошибка загрузки")
            print(f"Error loading image preview: {e}")

    def save_product(self):
        """Сохранить товар"""
        # Валидация
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите название товара")
            return

        price = self.price_input.value()
        if price <= 0:
            QMessageBox.warning(self, "Ошибка", "Цена должна быть больше 0")
            return

        # Обработка изображения
        image_url = None
        if self.uploaded_image_path:
            # Генерируем ID для нового товара
            product_id = f"PROD-{int(datetime.now().timestamp())}" if self.is_new else self.product.external_id

            # Сохраняем изображение
            full_path, thumb_path = ImageUtils.save_product_image(
                self.uploaded_image_path,
                product_id
            )

            if full_path:
                image_url = full_path
            else:
                QMessageBox.warning(
                    self,
                    "Предупреждение",
                    "Не удалось обработать изображение. Товар будет сохранен без изображения."
                )
        elif self.image_url_input.text().strip():
            # Используем URL из поля ввода
            image_url = self.image_url_input.text().strip()
        elif not self.is_new:
            # Оставляем старое изображение
            image_url = self.product.image_path or self.product.image_url

        # Определяем image_path (абсолютный путь) и image_url (может быть относительным)
        image_path = None
        if image_url and os.path.isabs(image_url):
            image_path = image_url

        # Сохранение
        with Session(self.db.engine) as session:
            if self.is_new:
                product = Product(
                    external_id=self.sku_input.text().strip() or f"PROD-{int(datetime.now().timestamp())}",
                    name=name,
                    category=self.category_input.text().strip() or None,
                    price=price,
                    unit=self.unit_input.text().strip() or "шт",
                    barcode=self.barcode_input.text().strip() or None,
                    image_url=image_url,
                    image_path=image_path,
                    is_active=self.is_active_checkbox.isChecked()
                )
                session.add(product)
            else:
                product = session.query(Product).filter(
                    Product.id == self.product.id
                ).first()

                if product:
                    product.external_id = self.sku_input.text().strip() or product.external_id
                    product.name = name
                    product.category = self.category_input.text().strip() or None
                    product.price = price
                    product.unit = self.unit_input.text().strip() or "шт"
                    product.barcode = self.barcode_input.text().strip() or None
                    product.image_url = image_url
                    product.image_path = image_path
                    product.is_active = self.is_active_checkbox.isChecked()
                    product.updated_at = datetime.utcnow()

            try:
                session.commit()
                QMessageBox.information(
                    self,
                    "Успех",
                    "Товар успешно сохранен"
                )
                self.accept()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка сохранения товара: {str(e)}"
                )
