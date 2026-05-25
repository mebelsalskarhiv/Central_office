"""
Миграция: Добавление таблицы delivery_events для GPS-треков доставки

Дата: 2026-05-02
"""

import sqlite3
import os
from datetime import datetime

def migrate():
    """Добавить таблицу delivery_events в БД"""

    db_path = os.path.join(os.path.dirname(__file__), 'data', 'central.db')

    if not os.path.exists(db_path):
        print(f"[ERROR] Database not found: {db_path}")
        return False

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем, существует ли таблица
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='delivery_events'
        """)

        if cursor.fetchone():
            print("[OK] Table delivery_events already exists")
            conn.close()
            return True

        # Создаем таблицу delivery_events
        cursor.execute("""
            CREATE TABLE delivery_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                latitude REAL NOT NULL,
                longitude REAL NOT NULL,
                accuracy REAL,
                timestamp DATETIME NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE
            )
        """)

        # Создаем индексы
        cursor.execute("""
            CREATE INDEX idx_delivery_event_order
            ON delivery_events(order_id)
        """)

        cursor.execute("""
            CREATE INDEX idx_delivery_event_type
            ON delivery_events(event_type)
        """)

        cursor.execute("""
            CREATE INDEX idx_delivery_event_timestamp
            ON delivery_events(timestamp)
        """)

        conn.commit()
        conn.close()

        print("[OK] Table delivery_events created successfully")
        print("[OK] Indexes created")
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("Migration: Add delivery_events table")
    print("=" * 60)

    success = migrate()

    if success:
        print("\n[SUCCESS] Migration completed!")
    else:
        print("\n[FAILED] Migration failed")
