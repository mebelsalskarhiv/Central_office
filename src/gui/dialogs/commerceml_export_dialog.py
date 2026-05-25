"""
Диалог экспорта заказов в 1С (CommerceML)
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QProgressBar, QTextEdit,
    QFileDialog, QGroupBox, QCheckBox, QDateEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate
from pathlib import Path
from datetime import datetime, timedelta

from sync.commerceml_integrator import CommerceMLIntegrator
from database.database import get_database


class ExportWorker(QThread):
    """Рабочий поток для экспорта"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(int)
    error = pyqtSignal(str)

    def __init__(self, output_path, date_from):
        super().__init__()
        self.output_path = output_path
        self.date_from = date_from
        self.db = get_database()

    def run(self):
        try:
            integrator = CommerceMLIntegrator(self.db.engine)

            self.progress.emit("Начало экспорта заказов в 1С...")

            # Экспортируем заказы
            count = integrator.export_orders_to_1c(self.output_path, self.date_from)

            self.progress.emit("Экспорт завершен!")
            self.finished.emit(count)

        except Exception as e:
            self.error.emit(str(e))


class CommerceMLExportDialog(QDialog):
    """Диалог экспорта заказов в 1С"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Экспорт в 1С (CommerceML)")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)

        layout = QVBoxLayout()

        # Группа выбора файла
        file_group = QGroupBox("Файл для экспорта")
        file_layout = QFormLayout()

        # orders.xml
        output_layout = QHBoxLayout()
        self.output_path_input = QLineEdit()
        self.output_path_input.setPlaceholderText("Выберите путь для сохранения orders.xml")
        output_layout.addWidget(self.output_path_input)
        output_browse_btn = QPushButton("Обзор...")
        output_browse_btn.clicked.connect(self.browse_output_path)
        output_layout.addWidget(output_browse_btn)
        file_layout.addRow("Сохранить как:", output_layout)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Фильтры
        filters_group = QGroupBox("Фильтры")
        filters_layout = QFormLayout()

        # Период
        period_layout = QHBoxLayout()

        self.period_combo = QSpinBox()
        self.period_combo.setRange(1, 365)
        self.period_combo.setValue(7)
        self.period_combo.setSuffix(" дней")
        period_layout.addWidget(QLabel("Последние"))
        period_layout.addWidget(self.period_combo)
        period_layout.addStretch()

        filters_layout.addRow("Период:", period_layout)

        # Или конкретная дата
        self.date_from = QDateEdit()
        self.date_from.setDate(QDate.currentDate().addDays(-7))
        self.date_from.setCalendarPopup(True)
        self.date_from.setEnabled(False)
        filters_layout.addRow("Или с даты:", self.date_from)

        self.use_custom_date = QCheckBox("Использовать конкретную дату")
        self.use_custom_date.stateChanged.connect(self.on_custom_date_changed)
        filters_layout.addRow("", self.use_custom_date)

        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)

        # Опции экспорта
        options_group = QGroupBox("Опции экспорта")
        options_layout = QVBoxLayout()

        self.include_new_checkbox = QCheckBox("Включить новые заказы")
        self.include_new_checkbox.setChecked(True)
        options_layout.addWidget(self.include_new_checkbox)

        self.include_in_progress_checkbox = QCheckBox("Включить заказы в работе")
        self.include_in_progress_checkbox.setChecked(True)
        options_layout.addWidget(self.include_in_progress_checkbox)

        self.include_delivered_checkbox = QCheckBox("Включить доставленные заказы")
        self.include_delivered_checkbox.setChecked(False)
        options_layout.addWidget(self.include_delivered_checkbox)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Лог
        log_label = QLabel("Лог экспорта:")
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

        self.export_btn = QPushButton("Экспортировать")
        self.export_btn.clicked.connect(self.start_export)
        self.export_btn.setDefault(True)
        button_layout.addWidget(self.export_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def on_custom_date_changed(self, state):
        """Обработчик изменения чекбокса конкретной даты"""
        use_custom = state == Qt.CheckState.Checked.value
        self.date_from.setEnabled(use_custom)
        self.period_combo.setEnabled(not use_custom)

    def browse_output_path(self):
        """Выбор пути для сохранения"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить orders.xml",
            "orders.xml",
            "XML файлы (*.xml);;Все файлы (*.*)"
        )

        if file_path:
            self.output_path_input.setText(file_path)

    def start_export(self):
        """Начать экспорт"""
        output_path = self.output_path_input.text().strip()

        if not output_path:
            self.log("Ошибка: Выберите путь для сохранения файла")
            return

        # Определяем дату начала
        if self.use_custom_date.isChecked():
            date_from = datetime.combine(
                self.date_from.date().toPyDate(),
                datetime.min.time()
            )
        else:
            days = self.period_combo.value()
            date_from = datetime.now() - timedelta(days=days)

        # Отключаем кнопки
        self.export_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.log(f"Начало экспорта заказов с {date_from.strftime('%d.%m.%Y')}...")

        # Запускаем экспорт в отдельном потоке
        self.worker = ExportWorker(output_path, date_from)
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_export_finished)
        self.worker.error.connect(self.on_export_error)
        self.worker.start()

    def on_export_finished(self, count):
        """Обработчик завершения экспорта"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        # Выводим статистику
        self.log("\n=== Результаты экспорта ===")
        self.log(f"Экспортировано заказов: {count}")
        self.log(f"Файл сохранен: {self.output_path_input.text()}")
        self.log("\nЭкспорт завершен успешно!")

    def on_export_error(self, error_msg):
        """Обработчик ошибки экспорта"""
        self.progress_bar.setVisible(False)
        self.export_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        self.log(f"\nКритическая ошибка: {error_msg}")

    def log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.append(message)
        # Прокручиваем вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
