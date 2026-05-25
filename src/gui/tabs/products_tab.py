"""
Новая вкладка товаров с деревом категорий
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QLineEdit, QLabel, QComboBox, QHeaderView, QMessageBox,
    QTreeWidget, QTreeWidgetItem, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap
from sqlalchemy.orm import Session
from datetime import datetime
import os

from database.database import get_database
from database.models import Product
from gui.dialogs.product_edit_dialog import ProductEditDialog
from gui.utils.table_settings import TableSettings


class ProductsTab(QWidget):
    """Вкладка товаров с деревом категорий"""

    def __init__(self):
        super().__init__()
        self.db = get_database()
        self.table_settings = TableSettings("products_tab")
        self.current_category = None  # Текущая выбранная категория
        self.selected_categories = set()  # Выбранная категория + все подкатегории
        self.init_ui()
        self.load_products()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Панель фильтров (компактная)
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)

        # Поиск
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию, артикулу, штрихкоду...")
        self.search_input.textChanged.connect(self.filter_products)
        filter_layout.addWidget(QLabel("Поиск:"))
        filter_layout.addWidget(self.search_input)

        # Фильтр по активности
        self.active_filter = QComboBox()
        self.active_filter.addItem("Все", None)
        self.active_filter.addItem("Активные", True)
        self.active_filter.addItem("Неактивные", False)
        self.active_filter.currentIndexChanged.connect(self.filter_products)
        filter_layout.addWidget(QLabel("Статус:"))
        filter_layout.addWidget(self.active_filter)

        # Кнопка сброса
        reset_btn = QPushButton("Сбросить")
        reset_btn.clicked.connect(self.reset_filters)
        filter_layout.addWidget(reset_btn)

        filter_layout.addStretch()

        layout.addLayout(filter_layout)

        # Splitter для дерева категорий и таблицы
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Дерево категорий
        self.category_tree = QTreeWidget()
        self.category_tree.setHeaderLabel("Категории")
        self.category_tree.setMaximumWidth(300)
        self.category_tree.itemClicked.connect(self.on_category_selected)
        splitter.addWidget(self.category_tree)

        # Таблица товаров
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels([
            "☑", "Фото", "Артикул", "Название", "Категория", "Цена", "Единица",
            "Штрихкод", "Активен", "Обновлен"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.edit_product)

        # Устанавливаем вертикальный режим изменения размера строк
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setDefaultSectionSize(50)

        # Восстанавливаем ширину колонок
        self.table_settings.restore_column_widths(self.table)

        # Сохраняем ширину при изменении
        self.table.horizontalHeader().sectionResized.connect(self.on_column_resized)

        splitter.addWidget(self.table)

        # Устанавливаем пропорции: 1:3
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)

        # Устанавливаем минимальную высоту для splitter
        splitter.setMinimumHeight(400)

        layout.addWidget(splitter, stretch=1)  # Даем splitter максимальный приоритет

        # Панель кнопок (компактная)
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 5, 0, 0)

        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("Снять выбор")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)

        button_layout.addWidget(QLabel("|"))

        activate_selected_btn = QPushButton("Активировать выбранные")
        activate_selected_btn.clicked.connect(lambda: self.toggle_selected(True))
        button_layout.addWidget(activate_selected_btn)

        deactivate_selected_btn = QPushButton("Деактивировать выбранные")
        deactivate_selected_btn.clicked.connect(lambda: self.toggle_selected(False))
        button_layout.addWidget(deactivate_selected_btn)

        button_layout.addWidget(QLabel("|"))

        add_btn = QPushButton("Добавить")
        add_btn.clicked.connect(self.add_product)
        button_layout.addWidget(add_btn)

        edit_btn = QPushButton("Редактировать")
        edit_btn.clicked.connect(self.edit_product)
        button_layout.addWidget(edit_btn)

        toggle_active_btn = QPushButton("Вкл/Выкл")
        toggle_active_btn.clicked.connect(self.toggle_active)
        button_layout.addWidget(toggle_active_btn)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.clicked.connect(self.load_products)
        button_layout.addWidget(refresh_btn)

        button_layout.addStretch()

        # Статистика
        self.stats_label = QLabel()
        button_layout.addWidget(self.stats_label)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_products(self):
        """Загрузить товары из БД"""
        with Session(self.db.engine) as session:
            self.all_products = session.query(Product).all()

            # Detach from session
            session.expunge_all()

        # Строим дерево категорий
        self.build_category_tree()

        # Отображаем товары
        self.filter_products()

    def build_category_tree(self):
        """Построить дерево категорий"""
        self.category_tree.clear()

        # Добавляем корневой элемент "Все товары"
        all_item = QTreeWidgetItem(self.category_tree, ["Все товары"])
        all_item.setData(0, Qt.ItemDataRole.UserRole, None)
        total_count = len(self.all_products)
        all_item.setText(0, f"Все товары ({total_count})")

        try:
            # Загружаем категории из БД
            from database.database import get_database
            from database.models import Category

            db = get_database()
            session = db.get_session()

            # Получаем все категории
            categories = session.query(Category).all()

            if categories:
                # Строим иерархию из БД
                self.build_category_hierarchy_from_db(all_item, categories, None)
            else:
                # Fallback: простой список категорий из товаров (если категорий в БД нет)
                categories_dict = {}
                for product in self.all_products:
                    if product.category:
                        categories_dict[product.category] = categories_dict.get(product.category, 0) + 1

                for category, count in sorted(categories_dict.items()):
                    item = QTreeWidgetItem(all_item, [f"{category} ({count})"])
                    item.setData(0, Qt.ItemDataRole.UserRole, category)

            session.close()

        except Exception as e:
            print(f"Error loading categories from DB: {e}")
            # Fallback: простой список категорий из товаров
            categories_dict = {}
            for product in self.all_products:
                if product.category:
                    categories_dict[product.category] = categories_dict.get(product.category, 0) + 1

            for category, count in sorted(categories_dict.items()):
                item = QTreeWidgetItem(all_item, [f"{category} ({count})"])
                item.setData(0, Qt.ItemDataRole.UserRole, category)

        self.category_tree.expandAll()

    def build_category_hierarchy_from_db(self, parent_item, categories, parent_id):
        """Рекурсивно построить иерархию категорий из БД"""
        # Находим дочерние категории
        children = [c for c in categories if c.parent_id == parent_id]

        for category in children:
            # Считаем товары в этой категории
            count = sum(1 for p in self.all_products if p.category == category.name)

            # Создаем элемент дерева
            item = QTreeWidgetItem(parent_item, [f"{category.name} ({count})"])
            item.setData(0, Qt.ItemDataRole.UserRole, category.name)

            # Рекурсивно добавляем подкатегории
            self.build_category_hierarchy_from_db(item, categories, category.id)

    def load_categories_from_import(self):
        """Загрузить категории из последнего импорта"""
        import os
        from sync.commerceml_parser import CommerceMLParser

        # Ищем файл import.xml
        import_path = os.path.join('CommerceML', 'webdata', 'import0_1.xml')
        if not os.path.exists(import_path):
            return None

        try:
            import_data = CommerceMLParser.parse_import_xml(import_path)
            return import_data.get('categories', [])
        except Exception as e:
            print(f"Error loading categories: {e}")
            return None

    def build_category_hierarchy(self, parent_item, categories, parent_id):
        """Рекурсивно построить иерархию категорий"""
        # Находим дочерние категории
        children = [c for c in categories if c.get('parent_id') == parent_id]

        for category in children:
            # Считаем товары в этой категории
            count = sum(1 for p in self.all_products if p.category == category['name'])

            # Создаем элемент дерева
            item = QTreeWidgetItem(parent_item, [f"{category['name']} ({count})"])
            item.setData(0, Qt.ItemDataRole.UserRole, category['name'])

            # Рекурсивно добавляем подкатегории
            self.build_category_hierarchy(item, categories, category['id'])

    def on_category_selected(self, item, column):
        """Обработчик выбора категории"""
        self.current_category = item.data(0, Qt.ItemDataRole.UserRole)

        # Собираем все подкатегории выбранной категории
        self.selected_categories = set()
        if self.current_category is not None:
            self.selected_categories.add(self.current_category)
            self.collect_subcategories(item)

        self.filter_products()

    def collect_subcategories(self, item):
        """Рекурсивно собрать все подкатегории"""
        for i in range(item.childCount()):
            child = item.child(i)
            category = child.data(0, Qt.ItemDataRole.UserRole)
            if category:
                self.selected_categories.add(category)
            self.collect_subcategories(child)

    def filter_products(self):
        """Применить фильтры"""
        search_text = self.search_input.text().lower()
        is_active = self.active_filter.currentData()

        filtered_products = []

        for product in self.all_products:
            # Фильтр по категории (включая подкатегории)
            if self.current_category is not None:
                if product.category not in self.selected_categories:
                    continue

            # Фильтр по поиску
            if search_text:
                if not (
                    search_text in product.name.lower() or
                    search_text in (product.article or "").lower() or
                    search_text in (product.barcode or "").lower()
                ):
                    continue

            # Фильтр по активности
            if is_active is not None and product.is_active != is_active:
                continue

            filtered_products.append(product)

        self.display_products(filtered_products)
        self.update_stats(filtered_products)

    def display_products(self, products):
        """Отобразить товары в таблице"""
        self.table.setRowCount(len(products))

        for row, product in enumerate(products):
            # Чекбокс
            checkbox = QTableWidgetItem()
            checkbox.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            checkbox.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, checkbox)

            # Фото
            image_label = QLabel()
            image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # Используем image_path (абсолютный путь) или image_url
            image_source = product.image_path or product.image_url
            if image_source and os.path.exists(image_source):
                # Ищем миниатюру
                thumb_path = image_source.replace('.jpg', '_thumb.jpg').replace('.jpeg', '_thumb.jpeg').replace('.png', '_thumb.png')
                image_path = thumb_path if os.path.exists(thumb_path) else image_source

                pixmap = QPixmap(image_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        40, 40,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("—")
            else:
                image_label.setText("—")
            self.table.setCellWidget(row, 1, image_label)

            # Артикул
            self.table.setItem(row, 2, QTableWidgetItem(product.article or "-"))

            # Название
            name_item = QTableWidgetItem(product.name)
            if not product.is_active:
                name_item.setForeground(QColor("#999999"))
            self.table.setItem(row, 3, name_item)

            # Категория
            self.table.setItem(row, 4, QTableWidgetItem(product.category or "-"))

            # Цена
            price_item = QTableWidgetItem(f"{product.price:.2f} ₽")
            if not product.is_active:
                price_item.setForeground(QColor("#999999"))
            self.table.setItem(row, 5, price_item)

            # Единица
            self.table.setItem(row, 6, QTableWidgetItem(product.unit))

            # Штрихкод
            self.table.setItem(row, 7, QTableWidgetItem(product.barcode or "-"))

            # Активен
            active_item = QTableWidgetItem("Да" if product.is_active else "Нет")
            if product.is_active:
                active_item.setBackground(QColor("#C8E6C9"))
            else:
                active_item.setBackground(QColor("#FFCDD2"))
            self.table.setItem(row, 8, active_item)

            # Обновлен
            if isinstance(product.updated_at, datetime):
                updated = product.updated_at
            else:
                updated = datetime.fromtimestamp(product.updated_at / 1000)
            self.table.setItem(row, 9, QTableWidgetItem(updated.strftime("%d.%m.%Y")))

            # Сохраняем ID товара в артикуле
            self.table.item(row, 2).setData(Qt.ItemDataRole.UserRole, product.id)

    def update_stats(self, products):
        """Обновить статистику"""
        total = len(products)
        active = sum(1 for p in products if p.is_active)
        inactive = total - active
        self.stats_label.setText(
            f"Всего товаров: {total} | Активных: {active} | Неактивных: {inactive}"
        )

    def reset_filters(self):
        """Сбросить фильтры"""
        self.search_input.clear()
        self.active_filter.setCurrentIndex(0)
        self.current_category = None
        # Выбираем "Все товары" в дереве
        if self.category_tree.topLevelItemCount() > 0:
            self.category_tree.setCurrentItem(self.category_tree.topLevelItem(0))

    def add_product(self):
        """Добавить товар"""
        dialog = ProductEditDialog(None, self)
        if dialog.exec():
            self.load_products()

    def edit_product(self):
        """Редактировать товар"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        # product_id хранится в колонке 2 (Артикул)
        article_item = self.table.item(current_row, 2)
        if not article_item:
            return

        product_id = article_item.data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if product:
                dialog = ProductEditDialog(product, self)
                if dialog.exec():
                    self.load_products()

    def toggle_active(self):
        """Переключить активность товара"""
        current_row = self.table.currentRow()
        if current_row < 0:
            return

        # product_id хранится в колонке 2 (Артикул)
        article_item = self.table.item(current_row, 2)
        if not article_item:
            return

        product_id = article_item.data(Qt.ItemDataRole.UserRole)

        with Session(self.db.engine) as session:
            product = session.query(Product).filter(Product.id == product_id).first()
            if product:
                product.is_active = not product.is_active
                product.updated_at = datetime.utcnow()
                session.commit()

                action = "активирован" if product.is_active else "деактивирован"
                QMessageBox.information(self, "Успех", f"Товар {action}")

        self.load_products()

    def select_all(self):
        """Выбрать все товары"""
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Checked)

    def deselect_all(self):
        """Снять выбор со всех товаров"""
        for row in range(self.table.rowCount()):
            self.table.item(row, 0).setCheckState(Qt.CheckState.Unchecked)

    def toggle_selected(self, is_active):
        """Активировать/деактивировать выбранные товары"""
        selected_ids = []
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                product_id = self.table.item(row, 2).data(Qt.ItemDataRole.UserRole)
                selected_ids.append(product_id)

        if not selected_ids:
            QMessageBox.warning(self, "Предупреждение", "Не выбрано ни одного товара")
            return

        action = "активировать" if is_active else "деактивировать"
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            f"Вы уверены, что хотите {action} {len(selected_ids)} товаров?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                with Session(self.db.engine) as session:
                    session.query(Product).filter(Product.id.in_(selected_ids)).update(
                        {Product.is_active: is_active},
                        synchronize_session=False
                    )
                    session.commit()

                QMessageBox.information(
                    self,
                    "Успех",
                    f"Товаров {action}о: {len(selected_ids)}"
                )
                self.load_products()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при изменении статуса товаров:\n{str(e)}"
                )

    def on_column_resized(self):
        """Обработчик изменения ширины колонки"""
        self.table_settings.save_column_widths(self.table)

    def closeEvent(self, event):
        """Сохранить настройки при закрытии"""
        self.table_settings.save_column_widths(self.table)
        event.accept()
