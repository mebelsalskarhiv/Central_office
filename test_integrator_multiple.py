"""
Тест интегратора CommerceML с множественными файлами
"""
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "src"))

from database.database import Database
from sync.commerceml_integrator import CommerceMLIntegrator

def test_import_from_directory():
    """Тест импорта из директории с множественными файлами"""

    # Создаем тестовую БД в памяти
    db = Database(":memory:")
    db.connect()
    db.create_tables()

    print("Testing import from directory with multiple files")
    print("="*60)

    # Путь к директории с файлами
    directory = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata"

    try:
        integrator = CommerceMLIntegrator(db.engine)

        # Импортируем из директории (автоматически найдет все import*.xml и offers*.xml)
        print(f"Importing from directory: {directory}")
        print()

        stats = integrator.import_from_1c(
            import_xml_path=directory,
            offers_xml_path=directory
        )

        print("[OK] Import successful!")
        print(f"Products created: {stats['products_created']}")
        print(f"Products updated: {stats['products_updated']}")
        print(f"Errors: {len(stats['errors'])}")

        if stats['errors']:
            print("\nFirst 3 errors:")
            for error in stats['errors'][:3]:
                print(f"  - {error}")

        # Проверяем, что товары импортировались
        session = db.get_session()
        from database.models import Product
        product_count = session.query(Product).count()
        session.close()

        print(f"\nTotal products in database: {product_count}")

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

def test_import_from_single_file():
    """Тест импорта из одного файла (обратная совместимость)"""

    # Создаем тестовую БД в памяти
    db = Database(":memory:")
    db.connect()
    db.create_tables()

    print("\nTesting import from single file (backward compatibility)")
    print("="*60)

    # Путь к одному файлу
    import_file = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata\import0_1.xml"
    offers_file = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata\offers0_1.xml"

    try:
        integrator = CommerceMLIntegrator(db.engine)

        print(f"Importing from file: {Path(import_file).name}")
        print()

        stats = integrator.import_from_1c(
            import_xml_path=import_file,
            offers_xml_path=offers_file
        )

        print("[OK] Import successful!")
        print(f"Products created: {stats['products_created']}")
        print(f"Products updated: {stats['products_updated']}")
        print(f"Errors: {len(stats['errors'])}")

        # Проверяем, что товары импортировались
        session = db.get_session()
        from database.models import Product
        product_count = session.query(Product).count()
        session.close()

        print(f"\nTotal products in database: {product_count}")

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    print("="*60)
    print("Testing CommerceML Integrator - Multiple Files Support")
    print("="*60)
    print()

    test1 = test_import_from_directory()
    test2 = test_import_from_single_file()

    print()
    print("="*60)
    if test1 and test2:
        print("[OK] All tests passed!")
    else:
        print("[ERROR] Some tests failed")
    print("="*60)
