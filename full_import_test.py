"""
Полный тест импорта с проверкой артикулов
"""
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sync.commerceml_integrator import CommerceMLIntegrator
from sqlalchemy.orm import Session
from database.models import Product

db = get_database()

# Очищаем товары
print("Clearing products...")
with Session(db.engine) as session:
    session.query(Product).delete()
    session.commit()

# Импортируем
print("\nImporting products...")
integrator = CommerceMLIntegrator(db.engine)
stats = integrator.import_from_1c(
    'CommerceML/webdata/import0_1.xml',
    'CommerceML/webdata/offers0_1.xml'
)

print(f"Created: {stats['products_created']}")
print(f"Updated: {stats['products_updated']}")
print(f"Errors: {len(stats['errors'])}")

# Проверяем первые 3 товара
print("\n\nFirst 3 products in DB:")
with Session(db.engine) as session:
    products = session.query(Product).limit(3).all()

    for p in products:
        print(f"\n{p.name}")
        print(f"  external_id: {p.external_id}")
        print(f"  article: {p.article}")
        print(f"  barcode: {p.barcode}")
        print(f"  price: {p.price}")
