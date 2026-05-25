"""
Диалог ручной синхронизации данных
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QRadioButton, QButtonGroup
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
import json
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sync.sync_manager import SyncManager
from sync.real_webdav_client import WebDAVClient
from database.database import get_database
from utils.settings_manager import SettingsManager


class SyncWorker(QThread):
    """Рабочий поток для синхронизации"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, mode: str, webdav_enabled: bool, webdav_url: str,
                 webdav_username: str, webdav_password: str):
        super().__init__()
        self.mode = mode  # 'upload', 'download', 'full'
        self.webdav_enabled = webdav_enabled
        self.webdav_url = webdav_url
        self.webdav_username = webdav_username
        self.webdav_password = webdav_password
        self.db = get_database()

    def run(self):
        try:
            stats = {
                'uploaded': 0,
                'downloaded': 0,
                'processed': 0,
                'errors': []
            }

            # Создаем WebDAV клиент если включен
            webdav_client = None
            if self.webdav_enabled and self.webdav_url:
                self.progress.emit("Подключение к WebDAV серверу...")
                webdav_client = WebDAVClient(
                    self.webdav_url,
                    self.webdav_username,
                    self.webdav_password
                )

                if not webdav_client.test_connection():
                    raise Exception("Не удалось подключиться к WebDAV серверу")

                self.progress.emit("Подключение успешно!")

            # Создаем SyncManager
            sync_manager = SyncManager(self.db.engine)

            # Выгрузка данных
            if self.mode in ['upload', 'full']:
                self.progress.emit("\n=== Выгрузка данных ===")

                # Получаем список активных менеджеров из БД
                from sqlalchemy.orm import sessionmaker
                from database.models import Manager

                Session = sessionmaker(bind=self.db.engine)
                session = Session()

                try:
                    managers = session.query(Manager).filter_by(status='ACTIVE').all()

                    if not managers:
                        self.progress.emit("⚠ Нет активных менеджеров в БД")
                        session.close()
                        return

                    self.progress.emit(f"Найдено активных менеджеров: {len(managers)}")

                    for manager in managers:
                        manager_pin = manager.pin_code

                        try:
                            self.progress.emit(f"\n--- Менеджер: {manager.name} (PIN: {manager_pin}) ---")

                            # Генерируем products.json
                            products_path = Path(f"data/webdav/{manager_pin}/incoming/products.json")
                            products_path.parent.mkdir(parents=True, exist_ok=True)

                            sync_manager.generate_products_json(str(products_path))
                            self.progress.emit(f"  ✓ Создан products.json")

                            # Генерируем settings.json
                            settings_path = Path(f"data/webdav/{manager_pin}/incoming/settings.json")
                            sync_manager.generate_settings_json(str(settings_path))
                            self.progress.emit(f"  ✓ Создан settings.json")

                            # Копируем изображения товаров
                            images_copied = sync_manager.copy_product_images(manager_pin)
                            if images_copied > 0:
                                self.progress.emit(f"  ✓ Скопировано изображений: {images_copied}")

                            # Загружаем на WebDAV если включен
                            if webdav_client:
                                # Загружаем products.json
                                if webdav_client.upload_file(
                                    str(products_path),
                                    f"{manager_pin}/incoming/products.json"
                                ):
                                    stats['uploaded'] += 1
                                    self.progress.emit(f"  ✓ Загружен products.json на сервер")

                                # Загружаем settings.json
                                if webdav_client.upload_file(
                                    str(settings_path),
                                    f"{manager_pin}/incoming/settings.json"
                                ):
                                    stats['uploaded'] += 1
                                    self.progress.emit(f"  ✓ Загружен settings.json на сервер")

                                # Загружаем изображения
                                images_dir = Path(f"data/webdav/{manager_pin}/incoming/images")
                                if images_dir.exists():
                                    image_count = 0
                                    for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                                        for image_file in images_dir.glob(ext):
                                            if webdav_client.upload_file(
                                                str(image_file),
                                                f"{manager_pin}/incoming/images/{image_file.name}"
                                            ):
                                                stats['uploaded'] += 1
                                                image_count += 1

                                    if image_count > 0:
                                        self.progress.emit(f"  ✓ Загружено изображений на сервер: {image_count}")

                        except Exception as e:
                            error_msg = f"Ошибка выгрузки для {manager_pin}: {str(e)}"
                            self.progress.emit(f"  ✗ {error_msg}")
                            stats['errors'].append(error_msg)

                finally:
                    session.close()

            # Загрузка данных
            if self.mode in ['download', 'full']:
                self.progress.emit("\n=== Загрузка данных ===")

                # Получаем список активных менеджеров из БД
                from sqlalchemy.orm import sessionmaker
                from database.models import Manager
                from sync.webdav_client import LocalWebDAVManager

                Session = sessionmaker(bind=self.db.engine)
                session = Session()

                try:
                    managers = session.query(Manager).filter_by(status='ACTIVE').all()

                    if not managers:
                        self.progress.emit("⚠ Нет активных менеджеров в БД")
                        session.close()
                        return

                    self.progress.emit(f"Найдено активных менеджеров: {len(managers)}")

                    # Создаем LocalWebDAVManager для работы с локальными файлами
                    local_webdav = LocalWebDAVManager("data/webdav")

                    for manager in managers:
                        manager_pin = manager.pin_code

                        try:
                            self.progress.emit(f"\n--- Менеджер: {manager.name} (PIN: {manager_pin}) ---")

                            # Скачиваем файлы с WebDAV если включен
                            if webdav_client:
                                self.progress.emit(f"  Скачивание файлов с сервера...")

                                try:
                                    # Получаем список файлов в outgoing на сервере
                                    files = webdav_client.list_files(f"{manager_pin}/outgoing")

                                    if files:
                                        self.progress.emit(f"  Найдено файлов на сервере: {len(files)}")

                                        for file_name in files:
                                            remote_path = f"{manager_pin}/outgoing/{file_name}"
                                            local_path = Path(f"data/webdav/{manager_pin}/outgoing/{file_name}")
                                            local_path.parent.mkdir(parents=True, exist_ok=True)

                                            if webdav_client.download_file(remote_path, str(local_path)):
                                                stats['downloaded'] += 1
                                                self.progress.emit(f"  ✓ Скачан {file_name}")
                                            else:
                                                self.progress.emit(f"  ✗ Ошибка скачивания {file_name}")
                                    else:
                                        self.progress.emit(f"  Нет файлов на сервере")

                                except Exception as e:
                                    self.progress.emit(f"  ⚠ Ошибка скачивания: {str(e)}")

                            # Обрабатываем локальные файлы через SyncManager
                            outgoing_files = local_webdav.list_outgoing_files(manager_pin)

                            if outgoing_files:
                                self.progress.emit(f"  Найдено файлов: {len(outgoing_files)}")

                                for json_file in outgoing_files:
                                    try:
                                        # Читаем файл
                                        data = local_webdav.read_json_file(json_file)
                                        if not data:
                                            raise ValueError(f"Не удалось прочитать {json_file.name}")

                                        # Определяем тип файла и обрабатываем
                                        file_result = {'orders_processed': 0, 'clients_processed': 0, 'errors': []}

                                        if json_file.name.startswith("orders_"):
                                            sync_manager._process_orders(session, manager, data, file_result)
                                            self.progress.emit(f"  ✓ Обработан {json_file.name}")
                                            if file_result['orders_processed'] > 0:
                                                self.progress.emit(f"    - Заказов: {file_result['orders_processed']}")

                                        elif json_file.name.startswith("clients_"):
                                            sync_manager._process_clients(session, manager, data, file_result)
                                            self.progress.emit(f"  ✓ Обработан {json_file.name}")
                                            if file_result['clients_processed'] > 0:
                                                self.progress.emit(f"    - Клиентов: {file_result['clients_processed']}")

                                        else:
                                            self.progress.emit(f"  ⚠ Неизвестный тип файла: {json_file.name}")
                                            continue

                                        # Перемещаем в processed
                                        local_webdav.move_to_processed(json_file, manager_pin)
                                        stats['processed'] += 1

                                        if file_result['errors']:
                                            for error in file_result['errors']:
                                                self.progress.emit(f"    ⚠ {error}")
                                                stats['errors'].append(error)

                                    except Exception as e:
                                        error_msg = f"Ошибка обработки {json_file.name}: {str(e)}"
                                        self.progress.emit(f"  ✗ {error_msg}")
                                        stats['errors'].append(error_msg)
                            else:
                                self.progress.emit(f"  Нет новых файлов от {manager.name}")

                        except Exception as e:
                            error_msg = f"Ошибка загрузки для {manager_pin}: {str(e)}"
                            self.progress.emit(f"  ✗ {error_msg}")
                            stats['errors'].append(error_msg)

                finally:
                    session.close()

            self.progress.emit("\nСинхронизация завершена!")
            self.finished.emit(stats)

        except Exception as e:
            self.error.emit(str(e))


class ManualSyncDialog(QDialog):
    """Диалог ручной синхронизации"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker = None
        self.settings_manager = SettingsManager()
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("Ручная синхронизация")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)

        layout = QVBoxLayout()

        # Режим синхронизации
        mode_group = QGroupBox("Режим синхронизации")
        mode_layout = QVBoxLayout()

        self.mode_group = QButtonGroup()

        self.upload_radio = QRadioButton("Только выгрузка (отправить данные на устройства)")
        self.upload_radio.setToolTip("Генерирует products.json и settings.json для менеджеров")
        self.mode_group.addButton(self.upload_radio, 1)
        mode_layout.addWidget(self.upload_radio)

        self.download_radio = QRadioButton("Только загрузка (получить данные с устройств)")
        self.download_radio.setToolTip("Обрабатывает orders.json, clients.json, payments.json от менеджеров")
        self.mode_group.addButton(self.download_radio, 2)
        mode_layout.addWidget(self.download_radio)

        self.full_radio = QRadioButton("Полная синхронизация (выгрузка + загрузка)")
        self.full_radio.setChecked(True)
        self.mode_group.addButton(self.full_radio, 3)
        mode_layout.addWidget(self.full_radio)

        mode_group.setLayout(mode_layout)
        layout.addWidget(mode_group)

        # Информация о настройках
        info_group = QGroupBox("Настройки WebDAV")
        info_layout = QVBoxLayout()

        webdav_enabled = self.settings_manager.get_webdav_enabled()
        webdav_url = self.settings_manager.get_webdav_url()

        if webdav_enabled and webdav_url:
            info_label = QLabel(f"✓ WebDAV включен\nURL: {webdav_url}")
            info_label.setStyleSheet("color: green;")
        else:
            info_label = QLabel(
                "⚠ WebDAV не настроен\n"
                "Синхронизация будет работать только с локальными файлами.\n"
                "Настройте WebDAV во вкладке 'Настройки'."
            )
            info_label.setStyleSheet("color: orange;")

        info_layout.addWidget(info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        # Лог
        log_label = QLabel("Лог синхронизации:")
        layout.addWidget(log_label)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.close_btn)

        self.sync_btn = QPushButton("Начать синхронизацию")
        self.sync_btn.clicked.connect(self.start_sync)
        self.sync_btn.setDefault(True)
        button_layout.addWidget(self.sync_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def start_sync(self):
        """Начать синхронизацию"""
        # Определяем режим
        if self.upload_radio.isChecked():
            mode = 'upload'
        elif self.download_radio.isChecked():
            mode = 'download'
        else:
            mode = 'full'

        # Получаем настройки WebDAV
        webdav_enabled = self.settings_manager.get_webdav_enabled()
        webdav_url = self.settings_manager.get_webdav_url()
        webdav_username = self.settings_manager.get_webdav_username()
        webdav_password = self.settings_manager.get_webdav_password()

        # Отключаем кнопки
        self.sync_btn.setEnabled(False)
        self.close_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        self.log(f"Начало синхронизации в режиме: {mode}")
        self.log(f"WebDAV: {'включен' if webdav_enabled else 'выключен'}")

        # Запускаем синхронизацию в отдельном потоке
        self.worker = SyncWorker(
            mode,
            webdav_enabled,
            webdav_url,
            webdav_username,
            webdav_password
        )
        self.worker.progress.connect(self.log)
        self.worker.finished.connect(self.on_sync_finished)
        self.worker.error.connect(self.on_sync_error)
        self.worker.start()

    def on_sync_finished(self, stats):
        """Обработчик завершения синхронизации"""
        self.progress_bar.setVisible(False)
        self.sync_btn.setEnabled(True)
        self.close_btn.setEnabled(True)

        # Выводим статистику
        self.log("\n=== Результаты синхронизации ===")
        self.log(f"Выгружено файлов: {stats['uploaded']}")
        self.log(f"Обработано файлов: {stats['processed']}")

        if stats['errors']:
            self.log(f"\nОшибок: {len(stats['errors'])}")
            for error in stats['errors'][:5]:
                self.log(f"  - {error}")
            if len(stats['errors']) > 5:
                self.log(f"  ... и еще {len(stats['errors']) - 5} ошибок")
        else:
            self.log("\nСинхронизация завершена успешно!")

    def on_sync_error(self, error_msg):
        """Обработчик ошибки синхронизации"""
        self.progress_bar.setVisible(False)
        self.sync_btn.setEnabled(True)
        self.close_btn.setEnabled(True)

        self.log(f"\nКритическая ошибка: {error_msg}")

    def log(self, message):
        """Добавить сообщение в лог"""
        self.log_text.append(message)
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
