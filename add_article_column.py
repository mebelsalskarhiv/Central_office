"""
Добавить поле article в таблицу products
"""
import sqlite3

db_path = 'data/central.db'

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    # Проверяем, есть ли уже поле article
    cursor.execute("PRAGMA table_info(products)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'article' not in columns:
        print("Добавляем поле article...")
        cursor.execute("ALTER TABLE products ADD COLUMN article VARCHAR(50)")
        conn.commit()
        print("✅ Поле article добавлено")
    else:
        print("ℹ️ Поле article уже существует")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    conn.rollback()
finally:
    conn.close()

print("\nГотово! Теперь можно импортировать товары заново.")
