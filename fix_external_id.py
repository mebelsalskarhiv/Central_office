"""
Скрипт для исправления конфликтов external_id в базе данных
Обнуляет все external_id, они будут установлены заново при следующей синхронизации
"""
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sqlalchemy.orm import Session
from database.models import Client

def fix_external_ids():
    """Исправить конфликты external_id"""
    db = get_database()

    with Session(db.engine) as session:
        # Находим всех клиентов с external_id
        clients = session.query(Client).filter(Client.external_id.isnot(None)).all()

        print(f"Найдено клиентов с external_id: {len(clients)}")

        if not clients:
            print("Нет клиентов с external_id. Исправление не требуется.")
            return

        # Показываем текущие external_id
        print("\nТекущие external_id:")
        for client in clients:
            print(f"  {client.phone}: {client.external_id}")

        # Спрашиваем подтверждение
        response = input("\nОбнулить все external_id? (yes/no): ")
        if response.lower() != 'yes':
            print("Отменено.")
            return

        # Обнуляем external_id у всех клиентов
        count = 0
        for client in clients:
            print(f"Обнуление external_id для {client.phone}: {client.external_id} -> None")
            client.external_id = None
            count += 1

        session.commit()
        print(f"\nГотово! Обнулено external_id у {count} клиентов.")
        print("При следующей синхронизации external_id будет установлен в формате PIN-CLIENT_ID")

if __name__ == "__main__":
    print("=" * 60)
    print("  Исправление конфликтов external_id")
    print("=" * 60)
    print()

    try:
        fix_external_ids()
    except Exception as e:
        print(f"\nОшибка: {e}")
        sys.exit(1)
