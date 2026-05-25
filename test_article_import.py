"""
Тест импорта артикула в БД
"""
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sync.commerceml_integrator import CommerceMLIntegrator
from sqlalchemy.orm import Session
from database.models import Product

db = get_database()
integrator = CommerceMLIntegrator(db.engine)

# Импортируем
print("Импорт товаров...")
stats = integrator.import_from_1c(
    'CommerceML/webdata/import0_1.xml',
    'CommerceML/webdata/offers0_1.xml'
)

print(f"Создано: {stats['products_created']}")
print(f"Обновлено: {stats['products_updated']}")
print(f"Ошибок: {len(stats['errors'])}")

# Проверяем артикулы в БД
with Session(db.engine) as session:
    products = session.query(Product).filter(Product.name.like('%Вкусносок%')).all()

    print("\nТовары с 'Вкусносок' в БД:")
    for p in products:
        print(f"  {p.name}")
        print(f"  Артикул: '{p.barcode}'")
        print(f"  External ID: {p.external_id}")
        print()
