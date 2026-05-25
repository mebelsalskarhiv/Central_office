"""
Тест создания товара с артикулом напрямую
"""
import sys
sys.path.insert(0, 'src')

from database.database import get_database
from sqlalchemy.orm import Session
from database.models import Product

db = get_database()

# Создаем тестовый товар
with Session(db.engine) as session:
    test_product = Product(
        external_id='TEST-123',
        name='Test Product',
        category='Test',
        price=100.0,
        unit='шт',
        article='TEST-ARTICLE-456',
        barcode='1234567890',
        is_active=True
    )

    session.add(test_product)
    session.commit()

    print("Test product created")

    # Читаем обратно
    saved = session.query(Product).filter_by(external_id='TEST-123').first()

    print(f"\nSaved product:")
    print(f"  external_id: {saved.external_id}")
    print(f"  name: {saved.name}")
    print(f"  article: {saved.article}")
    print(f"  barcode: {saved.barcode}")

    # Удаляем тестовый товар
    session.delete(saved)
    session.commit()
    print("\nTest product deleted")
