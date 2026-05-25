"""
Главная точка входа в приложение
"""
import sys
import argparse
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from database.database import init_database, get_database
from gui.main_window import MainWindow


def parse_args():
    """Парсинг аргументов командной строки"""
    parser = argparse.ArgumentParser(description='OrderManager Central Office')
    parser.add_argument('--init-db', action='store_true', help='Initialize database')
    parser.add_argument('--recreate-db', action='store_true', help='Recreate database (WARNING: deletes all data)')
    parser.add_argument('--db-path', type=str, help='Path to database file')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    return parser.parse_args()


def main():
    """Главная функция"""
    args = parse_args()

    # Инициализация базы данных
    if args.init_db or args.recreate_db:
        print("Initializing database...")
        db = init_database(db_path=args.db_path, recreate=args.recreate_db)
        print("Database initialized successfully!")
        if not args.init_db:
            db.close()
            return 0

    # Создаем приложение Qt
    # ВАЖНО: Устанавливаем атрибут перед созданием QApplication для QtWebEngine
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)

    app = QApplication(sys.argv)
    app.setApplicationName("OrderManager Central Office")
    app.setOrganizationName("OrderManager")

    # Устанавливаем стиль
    app.setStyle("Fusion")

    # Подключаемся к БД
    try:
        db = get_database()
        if args.db_path:
            db.db_path = args.db_path
            db.connect()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        print("Run with --init-db to initialize database")
        return 1

    # Создаем главное окно
    window = MainWindow(debug=args.debug)
    window.show()

    # Запускаем приложение
    exit_code = app.exec()

    # Закрываем БД
    db.close()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
