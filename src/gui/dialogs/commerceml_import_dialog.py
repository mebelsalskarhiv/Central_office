"""
Диалог импорта данных из 1С (CommerceML)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QProgressBar, QTextEdit,
    QFileDialog, QGroupBox, QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path

from sync.commerceml_integrator import CommerceMLIntegrator
from database.database import get_database


class ImportWorker(QThread):
    """Рабочий поток для импорта"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, import_xml, offers_xml):
        super().__init__()
        self.import_xml = import_xml
        self.offers_xml = offers_xml
        self.db = get_database()

    def run(self):
        try:
            integrator = CommerceMLIntegrator(self.db.engine)

            self.progress.emit("Начало импорта товаров из 1С...")

            # Импортируем товары
            stats = integrator.import_from_1c(self.import_xml, self.offers_xml)

            self.progress.emit("Импорт завершен!")
            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class CommerceMLImportDialog(QDialog):
    """Диалог импорта данных из 1С"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Импорт из 1С (CommerceML)")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Группа выбора файлов
        files_group = QGroupBox("Файлы для импорта")
        files_layout = QFormLayout()

        # import.xml
        import_layout = QHBoxLayout()
        self.import_xml_input = QLineEdit()
        self.import_xml_input.setPlaceholderText("Выберите файл import.xml или директорию с файлами")
        import_layout.addWidget(self.import_xml_input)
        import_browse_btn = QPushButton("Файл...")
        import_browse_btn.clicked.connect(self.browse_import_xml)
        import_layout.addWidget(import_browse_btn)
        import_dir_btn = QPushButton("Папка...")
        import_dir_btn.clicked.connect(self.browse_import_dir)
        import_layout.addWidget(import_dir_btn)
        files_layout.addRow("import.xml (товары):", import_layout)

        # offers.xml
        offers_layout = QHBoxLayout()
        self.offers_xml_input = QLineEdit()
        self.offers_xml_input.setPlaceholderText("Выберите файл offers.xml или директорию (опционально)")
        offers_layout.addWidget(self.offers_xml_input)
        offers_browse_btn = QPushButton("Файл...")
        offers_browse_btn.clicked.connect(self.browse_offers_xml)
        offers_layout.addWidget(offers_browse_btn)
        offers_dir_btn = QPushButton("Папка...")
        offers_dir_btn.clicked.connect(self.browse_offers_dir)
        offers_layout.addWidget(offers_dir_btn)
        files_layout.addRow("offers.xml (цены):", offers_layout)

        files_group.setLayout(files_layout)
        layout.addWidget(files_group)

        # Опции импорта
        options_group = QGroupBox("Опции импорта")
        options_layout = QVBoxLayout()

        self.update_prices_checkbox = QCheckBox("Обновить цены существующих товаров")
        self.update_prices_checkbox.setChecked(True)
        options_layout.addWidget(self.update_prices_checkbox)

        self.create_new_checkbox = QCheckBox("Создавать новые товары")
        self.create_new_checkbox.setChecked(True)
        options_layout.addWidget(self.create_new_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Лог
        log_label = QLabel("Лог импорта:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        layout.addWidget(self.log_text)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_btn = QPushButton("Отмена")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.import_btn = QPushButton("Импортировать")
        self.import_btn.clicked.connect(self.start_import)
        self.import_btn.setDefault(True)
        button_layout.addWidget(self.import_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def browse_import_xml(self):
        """Выбор файла import.xml"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл import.xml",
            "",
            "XML файлы (*.xml);;Все файлы (*.*)"
        )

        if file_path:
            self.import_xml_input.setText(file_path)

    def browse_import_dir(self):
        """Выбор директории с import*.xml файлами"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите директорию с файлами import*.xml",
            ""
        )

        if dir_path:
            self.import_xml_input.setText(dir_path)
            # Автоматически устанавливаем ту же директорию для offers
            if not self.offers_xml_input.text().strip():
                self.offers_xml_input.setText(dir_path)

    def browse_offers_xml(self):
        """Выбор файла offers.xml"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл offers.xml",
            "",
            "XML файлы (*.xml);;Все файлы (*.*)"
        )

        if file_path:
            self.offers_xml_input.setText(file_path)

    def browse_offers_dir(self):
        """Выбор директории с offers*.xml файлами"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Выберите директорию с файлами offers*.xml",
            ""
        )

        if dir_path:
            self.offers_xml_input.setText(dir_path)

    def start_import(self):
        """Начать импорт"""
        import_xml = self.import_xml_input.text().strip()

        if not import_xml:
            self.log("Ошибка: Выберите файл import.xml")
            return

        if not Path(import_xml).exists():
            self.log(f"Ошибка: Файл не найден: {import_xml}")
            return

        offers_xml = self.offers_xml_input.text().strip()
        if offers_xml and not Path(offers_xml).exists():
            self.log(f"Предупреждение: Файл offers.xml не найден: {offers_xml}")
            offers_xml = None

        # Отключаем кнопки
        self.import_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.log("Начало импорта...")

        # Запускаем импорт в отдельном потоке
        self.worker = ImportWorker(import_xml, offers_xml)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_import_finished)
        self.worker.error.connect(self.on_import_error)
        self.worker.start()

    def on_import_finished(self, stats):
        """Обработчик завершения импорта"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        # Выводим статистику
        self.log("\n=== Результаты импорта ===")
        self.log(f"Создано товаров: {stats['products_created']}")
        self.log(f"Обновлено товаров: {stats['products_updated']}")

        if stats['errors']:
            self.log(f"\nОшибок: {len(stats['errors'])}")
            for error in stats['errors'][:5]:  # Показываем первые 5 ошибок
                self.log(f"  - {error}")
            if len(stats['errors']) > 5:
                self.log(f"  ... и еще {len(stats['errors']) - 5} ошибок")
        else:
            self.log("\nИмпорт завершен успешно!")

    def on_import_error(self, error_msg):
        """Обработчик ошибки импорта"""
        self.progress_bar.setVisible(False)
        self.import_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        self.log(f"\nКритическая ошибка: {error_msg}")

    def log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.append(message)
        # Прокручиваем вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
