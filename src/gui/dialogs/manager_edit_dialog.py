"""
Диалог редактирования менеджера
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFormLayout, QComboBox, QMessageBox
)
from PyQt6.QtCore import Qt
from sqlalchemy.orm import Session
from datetime import datetime

from database.database import get_database
from database.models import Manager, ManagerStatus


class ManagerEditDialog(QDialog):
    """Диалог редактирования менеджера"""

    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.db = get_database()
        self.is_new = manager is None
        self.init_ui()

    def init_ui(self):
        """Инициализация UI"""
        title = "Добавить менеджера" if self.is_new else f"Редактировать: {self.manager.name}"
        self.setWindowTitle(title)
        self.setMinimumWidth(500)

        layout = QVBoxLayout()

        # Форма
        form_layout = QFormLayout()

        # PIN-код
        self.pin_input = QLineEdit()
        if not self.is_new:
            self.pin_input.setText(self.manager.pin_code)
            self.pin_input.setEnabled(False)  # PIN нельзя менять
        else:
            self.pin_input.setMaxLength(10)
            self.pin_input.setPlaceholderText("4-10 цифр")
        form_layout.addRow("PIN-код*:", self.pin_input)

        # Имя
        self.name_input = QLineEdit()
        if not self.is_new:
            self.name_input.setText(self.manager.name)
        form_layout.addRow("Имя*:", self.name_input)

        # Телефон
        self.phone_input = QLineEdit()
        if not self.is_new and self.manager.phone:
            self.phone_input.setText(self.manager.phone)
        self.phone_input.setPlaceholderText("+7 (XXX) XXX-XX-XX")
        form_layout.addRow("Телефон:", self.phone_input)

        # Email
        self.email_input = QLineEdit()
        if not self.is_new and self.manager.email:
            self.email_input.setText(self.manager.email)
        self.email_input.setPlaceholderText("email@example.com")
        form_layout.addRow("Email:", self.email_input)

        # Статус
        self.status_combo = QComboBox()
        self.status_combo.addItem("Активен", ManagerStatus.ACTIVE)
        self.status_combo.addItem("Заблокирован", ManagerStatus.BLOCKED)
        self.status_combo.addItem("Неактивен", ManagerStatus.INACTIVE)

        if not self.is_new:
            # Устанавливаем текущий статус
            for i in range(self.status_combo.count()):
                if self.status_combo.itemData(i) == self.manager.status:
                    self.status_combo.setCurrentIndex(i)
                    break
        form_layout.addRow("Статус:", self.status_combo)

        # Информация об устройстве (только для просмотра)
        if not self.is_new:
            device_info = f"{self.manager.device_model or 'Неизвестно'} (ID: {self.manager.device_id or '-'})"
            device_label = QLabel(device_info)
            device_label.setStyleSheet("color: #666;")
            form_layout.addRow("Устройство:", device_label)

            version_label = QLabel(self.manager.app_version or "-")
            version_label.setStyleSheet("color: #666;")
            form_layout.addRow("Версия приложения:", version_label)

            if self.manager.last_sync_at:
                if isinstance(self.manager.last_sync_at, datetime):
                    last_sync = self.manager.last_sync_at
                else:
                    last_sync = datetime.fromtimestamp(self.manager.last_sync_at / 1000)
                last_sync_str = last_sync.strftime("%d.%m.%Y %H:%M")
            else:
                last_sync_str = "Никогда"
            sync_label = QLabel(last_sync_str)
            sync_label.setStyleSheet("color: #666;")
            form_layout.addRow("Последняя синхронизация:", sync_label)

        layout.addLayout(form_layout)

        # Подсказка
        hint_label = QLabel("* - обязательные поля")
        hint_label.setStyleSheet("color: #999; font-size: 10px;")
        layout.addWidget(hint_label)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.save_manager)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def save_manager(self):
        """Сохранить менеджера"""
        # Валидация
        pin = self.pin_input.text().strip()
        name = self.name_input.text().strip()

        if not pin:
            QMessageBox.warning(self, "Ошибка", "Введите PIN-код")
            return

        if not pin.isdigit() or len(pin) < 4:
            QMessageBox.warning(self, "Ошибка", "PIN-код должен содержать минимум 4 цифры")
            return

        if not name:
            QMessageBox.warning(self, "Ошибка", "Введите имя менеджера")
            return

        # Сохранение
        with Session(self.db.engine) as session:
            if self.is_new:
                # Проверяем уникальность PIN
                existing = session.query(Manager).filter(
                    Manager.pin_code == pin
                ).first()

                if existing:
                    QMessageBox.warning(
                        self,
                        "Ошибка",
                        f"Менеджер с PIN-кодом {pin} уже существует"
                    )
                    return

                manager = Manager(
                    pin_code=pin,
                    name=name,
                    phone=self.phone_input.text().strip() or None,
                    email=self.email_input.text().strip() or None,
                    status=self.status_combo.currentData()
                )
                session.add(manager)
            else:
                manager = session.query(Manager).filter(
                    Manager.id == self.manager.id
                ).first()

                if manager:
                    manager.name = name
                    manager.phone = self.phone_input.text().strip() or None
                    manager.email = self.email_input.text().strip() or None
                    manager.status = self.status_combo.currentData()
                    manager.updated_at = datetime.utcnow()

            try:
                session.commit()
                QMessageBox.information(
                    self,
                    "Успех",
                    "Менеджер успешно сохранен"
                )
                self.accept()
            except Exception as e:
                session.rollback()
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка сохранения менеджера: {str(e)}"
                )
