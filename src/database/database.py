"""
Подключение к базе данных SQLite
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path

from .models import Base


class Database:
    """Менеджер базы данных"""

    def __init__(self, db_path: str = None):
        """
        Инициализация подключения к БД

        Args:
            db_path: Путь к файлу БД. Если None, используется data/central.db
        """
        if db_path is None:
            # Путь по умолчанию: Central_office/data/central.db
            base_dir = Path(__file__).parent.parent.parent
            data_dir = base_dir / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "central.db")

        self.db_path = db_path
        self.engine = None
        self.session_factory = None
        self.Session = None

    def connect(self):
        """Создать подключение к БД"""
        # SQLite connection string
        connection_string = f"sqlite:///{self.db_path}"

        # Создаем engine с настройками для SQLite
        self.engine = create_engine(
            connection_string,
            connect_args={"check_same_thread": False},  # Для многопоточности
            poolclass=StaticPool,  # Для SQLite
            echo=False  # Установить True для отладки SQL запросов
        )

        # Создаем фабрику сессий
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

        print(f"Connected to database: {self.db_path}")

    def create_tables(self):
        """Создать все таблицы"""
        if self.engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        Base.metadata.create_all(self.engine)
        print("Database tables created successfully")

    def drop_tables(self):
        """Удалить все таблицы (осторожно!)"""
        if self.engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        Base.metadata.drop_all(self.engine)
        print("Database tables dropped")

    def get_session(self):
        """Получить новую сессию БД"""
        if self.Session is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        return self.Session()

    def close(self):
        """Закрыть подключение"""
        if self.Session:
            self.Session.remove()
        if self.engine:
            self.engine.dispose()
        print("Database connection closed")


# Глобальный экземпляр БД
_db_instance = None


def get_database() -> Database:
    """Получить глобальный экземпляр БД"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
        _db_instance.connect()
        _db_instance.create_tables()  # Создаем таблицы при первом подключении
    return _db_instance


def init_database(db_path: str = None, recreate: bool = False):
    """
    Инициализировать базу данных

    Args:
        db_path: Путь к файлу БД
        recreate: Если True, пересоздать все таблицы
    """
    db = Database(db_path)
    db.connect()

    if recreate:
        print("Recreating database tables...")
        db.drop_tables()

    db.create_tables()

    # Создаем начальные настройки
    session = db.get_session()
    try:
        from .models import Settings

        default_settings = [
            ("bonus_enabled", "true", "Включена ли бонусная система"),
            ("bonus_earn_percentage", "5.0", "Процент начисления бонусов"),
            ("bonus_min_order_amount", "500.0", "Минимальная сумма заказа для бонусов"),
            ("bonus_max_per_order", "1000.0", "Максимум бонусов за заказ"),
            ("bonus_expiry_days", "365", "Срок действия бонусов (дни)"),
            ("delivery_min_amount", "300.0", "Минимальная сумма заказа"),
            ("sync_interval_minutes", "10", "Интервал синхронизации (минуты)"),
            ("keep_orders_days", "1", "Сколько дней хранить заказы на устройстве"),
            ("auto_cleanup", "true", "Автоматическая очистка старых данных"),
        ]

        for key, value, description in default_settings:
            existing = session.query(Settings).filter_by(key=key).first()
            if not existing:
                setting = Settings(key=key, value=value, description=description)
                session.add(setting)

        session.commit()
        print("Default settings created")

    except Exception as e:
        session.rollback()
        print(f"Error creating default settings: {e}")
    finally:
        session.close()

    return db


if __name__ == "__main__":
    # Тест подключения
    print("Testing database connection...")
    db = init_database(recreate=True)
    print("Database initialized successfully!")
    db.close()
