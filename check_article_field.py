"""
Проверка что попадает в поле article после импорта
"""
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sqlalchemy.orm import Session
from database.models import Product

db = get_database()

with Session(db.engine) as session:
    # Берем первые 5 товаров
    products = session.query(Product).limit(5).all()

    print("Первые 5 товаров в БД:\n")
    for p in products:
        print(f"Название: {p.name}")
        print(f"  external_id (Ид из XML): {p.external_id}")
        print(f"  article (должен быть код): {p.article}")
        print(f"  barcode (штрихкод): {p.barcode}")
        print()
