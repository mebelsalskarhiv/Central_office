"""
Главное окно приложения
"""
from PyQt6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QMenuBar,
    QMenu, QToolBar, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QIcon

from database.database import get_database


class MainWindow(QMainWindow):
    """Главное окно приложения"""

    def __init__(self, debug=False):
        super().__init__()
        self.debug = debug
        self.db = get_database()

        self.init_ui()
        self.setup_sync_timer()

    def init_ui(self):
        """Инициализация UI"""
        self.setWindowTitle("OrderManager - Центральная система")
        self.setGeometry(100, 100, 1400, 900)

        # Создаем меню
        self.create_menu()

        # Создаем панель инструментов
        self.create_toolbar()

        # Создаем вкладки
        self.create_tabs()

        # Создаем статус-бар
        self.create_statusbar()

    def create_menu(self):
        """Создать меню"""
        menubar = self.menuBar()

        # Меню "Файл"
        file_menu = menubar.addMenu("&Файл")

        export_action = QAction("&Экспорт данных...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self.export_data)
        file_menu.addAction(export_action)

        backup_action = QAction("&Резервная копия...", self)
        backup_action.setShortcut("Ctrl+B")
        backup_action.triggered.connect(self.create_backup)
        file_menu.addAction(backup_action)

        file_menu.addSeparator()

        exit_action = QAction("&Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню "Синхронизация"
        sync_menu = menubar.addMenu("&Синхронизация")

        sync_now_action = QAction("&Синхронизировать сейчас", self)
        sync_now_action.setShortcut("F5")
        sync_now_action.triggered.connect(self.sync_now)
        sync_menu.addAction(sync_now_action)

        sync_log_action = QAction("&Лог синхронизации...", self)
        sync_log_action.triggered.connect(self.show_sync_log)
        sync_menu.addAction(sync_log_action)

        # Меню "1С (CommerceML)"
        commerceml_menu = menubar.addMenu("&1С (CommerceML)")

        import_1c_action = QAction("&Импорт товаров из 1С...", self)
        import_1c_action.setShortcut("Ctrl+I")
        import_1c_action.triggered.connect(self.import_from_1c)
        commerceml_menu.addAction(import_1c_action)

        export_1c_action = QAction("&Экспорт заказов в 1С...", self)
        export_1c_action.setShortcut("Ctrl+Shift+E")
        export_1c_action.triggered.connect(self.export_to_1c)
        commerceml_menu.addAction(export_1c_action)

        # Меню "Обслуживание БД"
        maintenance_menu = menubar.addMenu("&Обслуживание БД")

        clear_products_action = QAction("Очистить &товары...", self)
        clear_products_action.triggered.connect(self.clear_products)
        maintenance_menu.addAction(clear_products_action)

        clear_categories_action = QAction("Очистить &категории товаров...", self)
        clear_categories_action.triggered.connect(self.clear_categories)
        maintenance_menu.addAction(clear_categories_action)

        clear_all_products_action = QAction("Очистить товары И категории (всё)...", self)
        clear_all_products_action.triggered.connect(self.clear_products_and_categories)
        maintenance_menu.addAction(clear_all_products_action)

        maintenance_menu.addSeparator()

        clear_clients_action = QAction("Очистить &клиентов...", self)
        clear_clients_action.triggered.connect(self.clear_clients)
        maintenance_menu.addAction(clear_clients_action)

        clear_orders_action = QAction("Очистить &заказы...", self)
        clear_orders_action.triggered.connect(self.clear_orders)
        maintenance_menu.addAction(clear_orders_action)

        maintenance_menu.addSeparator()

        clear_all_action = QAction("Очистить &всё...", self)
        clear_all_action.triggered.connect(self.clear_all_data)
        maintenance_menu.addAction(clear_all_action)

        # Меню "Настройки"
        settings_menu = menubar.addMenu("&Настройки")

        preferences_action = QAction("&Параметры...", self)
        preferences_action.setShortcut("Ctrl+,")
        preferences_action.triggered.connect(self.show_preferences)
        settings_menu.addAction(preferences_action)

        # Меню "Помощь"
        help_menu = menubar.addMenu("&Помощь")

        about_action = QAction("&О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Создать панель инструментов"""
        toolbar = QToolBar("Главная панель")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Кнопка синхронизации
        sync_action = QAction("Синхронизировать", self)
        sync_action.triggered.connect(self.sync_now)
        toolbar.addAction(sync_action)

        toolbar.addSeparator()

        # Кнопка обновления
        refresh_action = QAction("Обновить", self)
        refresh_action.triggered.connect(self.refresh_data)
        toolbar.addAction(refresh_action)

    def create_tabs(self):
        """Создать вкладки"""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Вкладка "Заказы"
        from gui.tabs.orders_tab import OrdersTab
        self.orders_tab = OrdersTab()
        self.tabs.addTab(self.orders_tab, "Заказы")

        # Вкладка "Отчеты" (для кассира и курьера)
        from gui.tabs.reports_tab import ReportsTab
        self.reports_tab = ReportsTab()
        self.tabs.addTab(self.reports_tab, "Отчеты")

        # Вкладка "Клиенты"
        from gui.tabs.clients_tab import ClientsTab
        self.clients_tab = ClientsTab()
        self.tabs.addTab(self.clients_tab, "Клиенты")

        # Вкладка "Товары"
        from gui.tabs.products_tab import ProductsTab
        self.products_tab = ProductsTab()
        self.tabs.addTab(self.products_tab, "Товары")

        # Вкладка "Менеджеры"
        from gui.tabs.managers_tab import ManagersTab
        self.managers_tab = ManagersTab()
        self.tabs.addTab(self.managers_tab, "Менеджеры")

        # Вкладка "Карта доставок"
        from gui.tabs.delivery_map_tab import DeliveryMapTab
        self.delivery_map_tab = DeliveryMapTab()
        self.tabs.addTab(self.delivery_map_tab, "Карта доставок")

        # Вкладка "Аналитика"
        from gui.tabs.analytics_tab import AnalyticsTab
        self.analytics_tab = AnalyticsTab()
        self.tabs.addTab(self.analytics_tab, "Аналитика")

        # Вкладка "Настройки"
        from gui.tabs.settings_tab import SettingsTab
        self.settings_tab = SettingsTab()
        self.tabs.addTab(self.settings_tab, "Настройки")

    def create_statusbar(self):
        """Создать статус-бар"""
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)

        self.statusbar.showMessage("Готов")

    def setup_sync_timer(self):
        """Настроить таймер автоматической синхронизации"""
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self.auto_sync)

        # Синхронизация каждые 5 минут
        self.sync_timer.start(5 * 60 * 1000)

    def sync_now(self):
        """Синхронизировать сейчас"""
        from gui.dialogs.manual_sync_dialog import ManualSyncDialog
        dialog = ManualSyncDialog(self)
        dialog.exec()

    def auto_sync(self):
        """Автоматическая синхронизация"""
        if self.debug:
            print("Auto sync triggered")
        # TODO: Реализовать автоматическую синхронизацию

    def refresh_data(self):
        """Обновить данные"""
        self.statusbar.showMessage("Обновление данных...")

        # Обновляем данные на текущей вкладке
        current_widget = self.tabs.currentWidget()
        if hasattr(current_widget, 'load_orders'):
            current_widget.load_orders()
        elif hasattr(current_widget, 'load_clients'):
            current_widget.load_clients()
        elif hasattr(current_widget, 'load_products'):
            current_widget.load_products()
        elif hasattr(current_widget, 'load_managers'):
            current_widget.load_managers()
        elif hasattr(current_widget, 'load_data'):
            current_widget.load_data()

        self.statusbar.showMessage("Готов")

    def export_data(self):
        """Экспорт данных"""
        QMessageBox.information(self, "Экспорт", "Экспорт данных будет реализован позже")

    def create_backup(self):
        """Создать резервную копию"""
        QMessageBox.information(self, "Резервная копия", "Создание резервной копии будет реализовано позже")

    def show_sync_log(self):
        """Показать лог синхронизации"""
        QMessageBox.information(self, "Лог синхронизации", "Лог синхронизации будет реализован позже")

    def show_preferences(self):
        """Показать настройки"""
        QMessageBox.information(self, "Настройки", "Настройки будут реализованы позже")

    def show_about(self):
        """Показать информацию о программе"""
        QMessageBox.about(
            self,
            "О программе",
            "<h3>OrderManager - Центральная система</h3>"
            "<p>Версия 1.0.0</p>"
            "<p>Система управления заказами, клиентами и товарами</p>"
            "<p>© 2026 OrderManager</p>"
        )

    def import_from_1c(self):
        """Импорт товаров из 1С"""
        from gui.dialogs.commerceml_import_dialog import CommerceMLImportDialog
        dialog = CommerceMLImportDialog(self)
        if dialog.exec():
            # Обновляем вкладку товаров
            if hasattr(self, 'products_tab'):
                self.products_tab.load_products()

    def export_to_1c(self):
        """Экспорт заказов в 1С"""
        from gui.dialogs.commerceml_export_dialog import CommerceMLExportDialog
        dialog = CommerceMLExportDialog(self)
        dialog.exec()

    def clear_products(self):
        """Очистить товары"""
        reply = QMessageBox.question(
            self,
            "Очистка товаров",
            "Вы уверены, что хотите удалить ВСЕ товары из базы данных?\n\n"
            "Это действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from sqlalchemy.orm import Session
                from database.models import Product

                with Session(self.db.engine) as session:
                    count = session.query(Product).count()
                    session.query(Product).delete()
                    session.commit()

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Удалено товаров: {count}"
                )

                # Обновляем вкладку товаров
                if hasattr(self, 'products_tab'):
                    self.products_tab.load_products()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при очистке товаров:\n{str(e)}"
                )

    def clear_categories(self):
        """Очистить категории товаров (установить category=NULL для всех товаров)"""
        reply = QMessageBox.question(
            self,
            "Очистка категорий",
            "Вы уверены, что хотите удалить ВСЕ категории товаров?\n\n"
            "Товары останутся, но у них будет удалена привязка к категориям.\n"
            "Это действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from sqlalchemy.orm import Session
                from database.models import Product

                with Session(self.db.engine) as session:
                    # Обнуляем категории у всех товаров
                    count = session.query(Product).filter(Product.category.isnot(None)).count()
                    session.query(Product).update({Product.category: None})
                    session.commit()

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Категории удалены у {count} товаров"
                )

                # Обновляем вкладку товаров
                if hasattr(self, 'products_tab'):
                    self.products_tab.load_products()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при очистке категорий:\n{str(e)}"
                )

    def clear_products_and_categories(self):
        """Полностью удалить все товары И все категории из БД"""
        reply = QMessageBox.question(
            self,
            "Полная очистка товаров и категорий",
            "⚠️ ВНИМАНИЕ! Вы уверены, что хотите удалить:\n\n"
            "• ВСЕ товары из базы данных\n"
            "• ВСЕ категории товаров\n\n"
            "Это действие ПОЛНОСТЬЮ удалит все данные о товарах и категориях!\n"
            "Это действие НЕЛЬЗЯ отменить!\n\n"
            "Продолжить?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from sqlalchemy.orm import Session
                from database.models import Product, Category

                with Session(self.db.engine) as session:
                    # Считаем количество перед удалением
                    products_count = session.query(Product).count()
                    categories_count = session.query(Category).count()

                    # Удаляем все товары (это автоматически обнулит category_id из-за foreign key)
                    session.query(Product).delete()

                    # Удаляем все категории
                    session.query(Category).delete()

                    session.commit()

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Удалено:\n"
                    f"• Товаров: {products_count}\n"
                    f"• Категорий: {categories_count}"
                )

                # Обновляем вкладку товаров
                if hasattr(self, 'products_tab'):
                    self.products_tab.load_products()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при очистке товаров и категорий:\n{str(e)}"
                )

    def clear_clients(self):
        """Очистить клиентов"""
        reply = QMessageBox.question(
            self,
            "Очистка клиентов",
            "Вы уверены, что хотите удалить ВСЕХ клиентов из базы данных?\n\n"
            "Это действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from sqlalchemy.orm import Session
                from database.models import Client, Address, BonusTransaction

                with Session(self.db.engine) as session:
                    # Удаляем связанные данные
                    bonus_count = session.query(BonusTransaction).delete()
                    address_count = session.query(Address).delete()
                    client_count = session.query(Client).delete()
                    session.commit()

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Удалено:\n"
                    f"- Клиентов: {client_count}\n"
                    f"- Адресов: {address_count}\n"
                    f"- Бонусных транзакций: {bonus_count}"
                )

                # Обновляем вкладку клиентов
                if hasattr(self, 'clients_tab'):
                    self.clients_tab.load_clients()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при очистке клиентов:\n{str(e)}"
                )

    def clear_orders(self):
        """Очистить заказы"""
        reply = QMessageBox.question(
            self,
            "Очистка заказов",
            "Вы уверены, что хотите удалить ВСЕ заказы из базы данных?\n\n"
            "Это действие нельзя отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                from sqlalchemy.orm import Session
                from database.models import Order, OrderItem

                with Session(self.db.engine) as session:
                    # Удаляем позиции заказов
                    items_count = session.query(OrderItem).delete()
                    # Удаляем заказы
                    orders_count = session.query(Order).delete()
                    session.commit()

                QMessageBox.information(
                    self,
                    "Успешно",
                    f"Удалено:\n"
                    f"- Заказов: {orders_count}\n"
                    f"- Позиций: {items_count}"
                )

                # Обновляем вкладку заказов
                if hasattr(self, 'orders_tab'):
                    self.orders_tab.load_orders()

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Ошибка",
                    f"Ошибка при очистке заказов:\n{str(e)}"
                )

    def clear_all_data(self):
        """Очистить все данные"""
        reply = QMessageBox.question(
            self,
            "Очистка ВСЕХ данных",
            "⚠️ ВНИМАНИЕ! ⚠️\n\n"
            "Вы уверены, что хотите удалить ВСЕ данные из базы данных?\n"
            "- Все товары\n"
            "- Всех клиентов\n"
            "- Все заказы\n"
            "- Все адреса\n"
            "- Все бонусные транзакции\n\n"
            "Это действие НЕЛЬЗЯ отменить!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Двойное подтверждение
            confirm = QMessageBox.question(
                self,
                "Подтверждение",
                "Вы ДЕЙСТВИТЕЛЬНО уверены?\n\nВсе данные будут безвозвратно удалены!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if confirm == QMessageBox.StandardButton.Yes:
                try:
                    from sqlalchemy.orm import Session
                    from database.models import (
                        Order, OrderItem, Client, Address,
                        BonusTransaction, Product
                    )

                    with Session(self.db.engine) as session:
                        # Удаляем в правильном порядке (сначала зависимые таблицы)
                        items_count = session.query(OrderItem).delete()
                        orders_count = session.query(Order).delete()
                        bonus_count = session.query(BonusTransaction).delete()
                        address_count = session.query(Address).delete()
                        client_count = session.query(Client).delete()
                        product_count = session.query(Product).delete()
                        session.commit()

                    QMessageBox.information(
                        self,
                        "Успешно",
                        f"База данных очищена:\n\n"
                        f"- Товаров: {product_count}\n"
                        f"- Клиентов: {client_count}\n"
                        f"- Адресов: {address_count}\n"
                        f"- Заказов: {orders_count}\n"
                        f"- Позиций заказов: {items_count}\n"
                        f"- Бонусных транзакций: {bonus_count}"
                    )

                    # Обновляем все вкладки
                    self.refresh_data()

                except Exception as e:
                    QMessageBox.critical(
                        self,
                        "Ошибка",
                        f"Ошибка при очистке базы данных:\n{str(e)}"
                    )

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Сохраняем настройки таблиц перед закрытием
        if hasattr(self, 'products_tab'):
            self.products_tab.table_settings.save_column_widths(self.products_tab.table)
        if hasattr(self, 'orders_tab') and hasattr(self.orders_tab, 'table_settings'):
            self.orders_tab.table_settings.save_column_widths(self.orders_tab.table)
        if hasattr(self, 'clients_tab') and hasattr(self.clients_tab, 'table_settings'):
            self.clients_tab.table_settings.save_column_widths(self.clients_tab.table)

        reply = QMessageBox.question(
            self,
            "Выход",
            "Вы уверены, что хотите выйти?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()
