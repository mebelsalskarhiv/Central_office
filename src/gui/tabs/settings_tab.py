"""
Вкладка настроек
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QLineEdit,
    QPushButton, QSpinBox, QDoubleSpinBox, QCheckBox, QFormLayout,
    QMessageBox, QFileDialog, QTabWidget
)
from PyQt6.QtCore import Qt

from utils.settings_manager import SettingsManager


class SettingsTab(QWidget):
    """Вкладка настроек"""

    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()

        # Создаем вкладки для разных категорий настроек
        self.tabs = QTabWidget()

        # Вкладка WebDAV
        self.webdav_tab = self.create_webdav_tab()
        self.tabs.addTab(self.webdav_tab, "WebDAV")

        # Вкладка синхронизации
        self.sync_tab = self.create_sync_tab()
        self.tabs.addTab(self.sync_tab, "Синхронизация")

        # Вкладка бонусной системы
        self.bonus_tab = self.create_bonus_tab()
        self.tabs.addTab(self.bonus_tab, "Бонусная система")

        # Вкладка CommerceML
        self.commerceml_tab = self.create_commerceml_tab()
        self.tabs.addTab(self.commerceml_tab, "CommerceML (1С)")

        layout.addWidget(self.tabs)

        # Кнопки внизу
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        reset_btn = QPushButton("Сбросить к умолчаниям")
        reset_btn.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(reset_btn)

        export_btn = QPushButton("Экспорт настроек")
        export_btn.clicked.connect(self.export_settings)
        button_layout.addWidget(export_btn)

        import_btn = QPushButton("Импорт настроек")
        import_btn.clicked.connect(self.import_settings)
        button_layout.addWidget(import_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_webdav_tab(self):
        """Создать вкладку настроек WebDAV"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Группа настроек WebDAV
        group = QGroupBox("Настройки WebDAV сервера")
        form_layout = QFormLayout()

        # Включить WebDAV
        self.webdav_enabled = QCheckBox("Использовать WebDAV для синхронизации")
        form_layout.addRow("", self.webdav_enabled)

        # URL сервера
        self.webdav_url = QLineEdit()
        self.webdav_url.setPlaceholderText("https://webdav.example.com/ordermanager")
        form_layout.addRow("URL сервера:", self.webdav_url)

        # Логин
        self.webdav_username = QLineEdit()
        self.webdav_username.setPlaceholderText("username")
        form_layout.addRow("Логин:", self.webdav_username)

        # Пароль
        self.webdav_password = QLineEdit()
        self.webdav_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.webdav_password.setPlaceholderText("password")
        form_layout.addRow("Пароль:", self.webdav_password)

        # Кнопка тестирования
        test_btn = QPushButton("Тест подключения")
        test_btn.clicked.connect(self.test_webdav_connection)
        form_layout.addRow("", test_btn)

        group.setLayout(form_layout)
        layout.addWidget(group)

        # Информация
        info_label = QLabel(
            "WebDAV используется для синхронизации данных между мобильными устройствами "
            "и центральной системой. Укажите URL WebDAV сервера и учетные данные."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_sync_tab(self):
        """Создать вкладку настроек синхронизации"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Группа настроек синхронизации
        group = QGroupBox("Настройки автоматической синхронизации")
        form_layout = QFormLayout()

        # Включить автосинхронизацию
        self.sync_enabled = QCheckBox("Включить автоматическую синхронизацию")
        form_layout.addRow("", self.sync_enabled)

        # Интервал синхронизации
        self.sync_interval = QSpinBox()
        self.sync_interval.setRange(1, 60)
        self.sync_interval.setSuffix(" мин")
        form_layout.addRow("Интервал синхронизации:", self.sync_interval)

        group.setLayout(form_layout)
        layout.addWidget(group)

        # Информация
        info_label = QLabel(
            "Автоматическая синхронизация проверяет новые данные от менеджеров "
            "и отправляет обновления товаров и настроек на устройства. "
            "Рекомендуемый интервал: 5-10 минут."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_bonus_tab(self):
        """Создать вкладку настроек бонусной системы"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Группа настроек бонусов
        group = QGroupBox("Настройки бонусной системы")
        form_layout = QFormLayout()

        # Включить бонусную систему
        self.bonus_enabled = QCheckBox("Включить бонусную систему")
        form_layout.addRow("", self.bonus_enabled)

        # Процент начисления
        self.bonus_percentage = QDoubleSpinBox()
        self.bonus_percentage.setRange(0, 100)
        self.bonus_percentage.setDecimals(1)
        self.bonus_percentage.setSuffix(" %")
        form_layout.addRow("Процент начисления бонусов:", self.bonus_percentage)

        # Максимальный процент оплаты
        self.bonus_max_payment = QDoubleSpinBox()
        self.bonus_max_payment.setRange(0, 100)
        self.bonus_max_payment.setDecimals(1)
        self.bonus_max_payment.setSuffix(" %")
        form_layout.addRow("Максимум оплаты бонусами:", self.bonus_max_payment)

        # Срок действия бонусов
        self.bonus_expiry = QSpinBox()
        self.bonus_expiry.setRange(0, 3650)
        self.bonus_expiry.setSuffix(" дней")
        self.bonus_expiry.setSpecialValueText("Бессрочно")
        form_layout.addRow("Срок действия бонусов:", self.bonus_expiry)

        group.setLayout(form_layout)
        layout.addWidget(group)

        # Информация
        info_label = QLabel(
            "Бонусная система начисляет клиентам баллы за покупки. "
            "Процент начисления определяет, сколько бонусов получит клиент от суммы заказа. "
            "Максимум оплаты бонусами ограничивает, какую часть заказа можно оплатить бонусами."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def create_commerceml_tab(self):
        """Создать вкладку настроек CommerceML"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Группа настроек CommerceML
        group = QGroupBox("Настройки обмена с 1С (CommerceML)")
        form_layout = QFormLayout()

        # Путь импорта
        import_layout = QHBoxLayout()
        self.commerceml_import_path = QLineEdit()
        self.commerceml_import_path.setPlaceholderText("C:\\1C\\exchange\\import")
        import_layout.addWidget(self.commerceml_import_path)
        import_browse_btn = QPushButton("Обзор...")
        import_browse_btn.clicked.connect(self.browse_import_path)
        import_layout.addWidget(import_browse_btn)
        form_layout.addRow("Папка импорта из 1С:", import_layout)

        # Путь экспорта
        export_layout = QHBoxLayout()
        self.commerceml_export_path = QLineEdit()
        self.commerceml_export_path.setPlaceholderText("C:\\1C\\exchange\\export")
        export_layout.addWidget(self.commerceml_export_path)
        export_browse_btn = QPushButton("Обзор...")
        export_browse_btn.clicked.connect(self.browse_export_path)
        export_layout.addWidget(export_browse_btn)
        form_layout.addRow("Папка экспорта в 1С:", export_layout)

        # Автоматический импорт
        self.commerceml_auto_import = QCheckBox("Автоматически импортировать товары из 1С")
        form_layout.addRow("", self.commerceml_auto_import)

        # Автоматический экспорт
        self.commerceml_auto_export = QCheckBox("Автоматически экспортировать заказы в 1С")
        form_layout.addRow("", self.commerceml_auto_export)

        group.setLayout(form_layout)
        layout.addWidget(group)

        # Информация
        info_label = QLabel(
            "CommerceML - стандартный формат обмена данными с 1С. "
            "Укажите папки для импорта товаров из 1С и экспорта заказов в 1С. "
            "При автоматическом режиме обмен происходит во время синхронизации."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def load_settings(self):
        """Загрузить настройки"""
        # WebDAV
        self.webdav_enabled.setChecked(self.settings_manager.get_webdav_enabled())
        self.webdav_url.setText(self.settings_manager.get_webdav_url())
        self.webdav_username.setText(self.settings_manager.get_webdav_username())
        self.webdav_password.setText(self.settings_manager.get_webdav_password())

        # Синхронизация
        self.sync_enabled.setChecked(self.settings_manager.get_sync_enabled())
        self.sync_interval.setValue(self.settings_manager.get_sync_interval())

        # Бонусы
        self.bonus_enabled.setChecked(self.settings_manager.get_bonus_enabled())
        self.bonus_percentage.setValue(self.settings_manager.get_bonus_percentage())
        self.bonus_max_payment.setValue(self.settings_manager.get_bonus_max_payment_percentage())
        self.bonus_expiry.setValue(self.settings_manager.get_bonus_expiry_days())

        # CommerceML
        self.commerceml_import_path.setText(self.settings_manager.get_commerceml_import_path())
        self.commerceml_export_path.setText(self.settings_manager.get_commerceml_export_path())
        self.commerceml_auto_import.setChecked(self.settings_manager.get_commerceml_auto_import())
        self.commerceml_auto_export.setChecked(self.settings_manager.get_commerceml_auto_export())

    def save_settings(self):
        """Сохранить настройки"""
        # WebDAV
        self.settings_manager.set_webdav_enabled(self.webdav_enabled.isChecked())
        self.settings_manager.set_webdav_url(self.webdav_url.text().strip())
        self.settings_manager.set_webdav_username(self.webdav_username.text().strip())
        self.settings_manager.set_webdav_password(self.webdav_password.text())

        # Синхронизация
        self.settings_manager.set_sync_enabled(self.sync_enabled.isChecked())
        self.settings_manager.set_sync_interval(self.sync_interval.value())

        # Бонусы
        self.settings_manager.set_bonus_enabled(self.bonus_enabled.isChecked())
        self.settings_manager.set_bonus_percentage(self.bonus_percentage.value())
        self.settings_manager.set_bonus_max_payment_percentage(self.bonus_max_payment.value())
        self.settings_manager.set_bonus_expiry_days(self.bonus_expiry.value())

        # CommerceML
        self.settings_manager.set_commerceml_import_path(self.commerceml_import_path.text().strip())
        self.settings_manager.set_commerceml_export_path(self.commerceml_export_path.text().strip())
        self.settings_manager.set_commerceml_auto_import(self.commerceml_auto_import.isChecked())
        self.settings_manager.set_commerceml_auto_export(self.commerceml_auto_export.isChecked())

        QMessageBox.information(self, "Успех", "Настройки сохранены")

    def reset_to_defaults(self):
        """Сбросить к значениям по умолчанию"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Сбросить все настройки к значениям по умолчанию?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_to_defaults()
            self.load_settings()
            QMessageBox.information(self, "Успех", "Настройки сброшены к значениям по умолчанию")

    def export_settings(self):
        """Экспорт настроек в файл"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Экспорт настроек",
            "config.json",
            "JSON файлы (*.json)"
        )

        if file_path:
            try:
                self.settings_manager.export_to_json(file_path)
                QMessageBox.information(self, "Успех", f"Настройки экспортированы в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка экспорта настроек: {str(e)}")

    def import_settings(self):
        """Импорт настроек из файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Импорт настроек",
            "",
            "JSON файлы (*.json)"
        )

        if file_path:
            try:
                self.settings_manager.import_from_json(file_path)
                self.load_settings()
                QMessageBox.information(self, "Успех", f"Настройки импортированы из {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка импорта настроек: {str(e)}")

    def test_webdav_connection(self):
        """Тест подключения к WebDAV"""
        url = self.webdav_url.text().strip()
        username = self.webdav_username.text().strip()
        password = self.webdav_password.text()

        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL WebDAV сервера")
            return

        # Тестируем подключение
        try:
            import requests
            from requests.auth import HTTPBasicAuth

            # Пробуем выполнить PROPFIND запрос
            response = requests.request(
                'PROPFIND',
                url,
                auth=HTTPBasicAuth(username, password) if username else None,
                timeout=5,
                headers={'Depth': '0'}
            )

            if response.status_code in [200, 207, 301, 302]:
                QMessageBox.information(
                    self,
                    "Успех",
                    f"Подключение к WebDAV серверу успешно!\n\n"
                    f"URL: {url}\n"
                    f"Статус: {response.status_code}\n"
                    f"Сервер: {response.headers.get('Server', 'Unknown')}"
                )
            elif response.status_code == 401:
                QMessageBox.warning(
                    self,
                    "Ошибка авторизации",
                    "Неверный логин или пароль.\n"
                    "Проверьте учетные данные."
                )
            elif response.status_code == 404:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"URL не найден: {url}\n"
                    "Проверьте правильность адреса."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    f"Ошибка подключения.\n\n"
                    f"Статус: {response.status_code}\n"
                    f"Ответ: {response.text[:200]}"
                )

        except requests.exceptions.ConnectionError:
            QMessageBox.critical(
                self,
                "Ошибка подключения",
                f"Не удалось подключиться к серверу.\n\n"
                f"URL: {url}\n\n"
                "Проверьте:\n"
                "- Правильность URL\n"
                "- Доступность сервера\n"
                "- Настройки сети/файрвола"
            )
        except requests.exceptions.Timeout:
            QMessageBox.critical(
                self,
                "Таймаут",
                f"Превышено время ожидания ответа от сервера.\n\n"
                f"URL: {url}"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Ошибка при тестировании подключения:\n\n{str(e)}"
            )

    def browse_import_path(self):
        """Выбор папки импорта"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку импорта из 1С",
            self.commerceml_import_path.text()
        )

        if path:
            self.commerceml_import_path.setText(path)

    def browse_export_path(self):
        """Выбор папки экспорта"""
        path = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку экспорта в 1С",
            self.commerceml_export_path.text()
        )

        if path:
            self.commerceml_export_path.setText(path)
