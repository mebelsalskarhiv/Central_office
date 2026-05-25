"""
Тест парсера CommerceML для множественных файлов
"""
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sync.commerceml_parser import CommerceMLParser

def test_parse_multiple_import_files():
    """Тест парсинга множественных import файлов"""
    directory = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata"

    print(f"Testing multiple import files in: {directory}")
    print()

    try:
        # Парсим все import*.xml файлы
        result = CommerceMLParser.parse_import_files(directory, "import*.xml")

        print(f"[OK] Parsing successful!")
        print(f"Total categories: {len(result['categories'])}")
        print(f"Total products: {len(result['products'])}")
        print()

        # Показываем первые 3 категории
        if result['categories']:
            print("First 3 categories:")
            for cat in result['categories'][:3]:
                print(f"  - {cat['name']}")
        print()

        # Показываем первые 3 товара
        if result['products']:
            print("First 3 products:")
            for prod in result['products'][:3]:
                print(f"  - {prod['name'][:60]}...")

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parse_multiple_offers_files():
    """Тест парсинга множественных offers файлов"""
    directory = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata"

    print(f"Testing multiple offers files in: {directory}")
    print()

    try:
        # Парсим все offers*.xml файлы
        offers = CommerceMLParser.parse_offers_files(directory, "offers*.xml")

        print(f"[OK] Parsing successful!")
        print(f"Total offers: {len(offers)}")
        print()

        # Показываем первые 3 предложения
        if offers:
            print("First 3 offers:")
            for offer in offers[:3]:
                print(f"  - Product ID: {offer['product_id'][:30]}... Price: {offer['price']} Qty: {offer['quantity']}")

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing CommerceML Parser - Multiple Files")
    print("="*60)
    print()

    print("Test 1: Multiple import*.xml files")
    print("-"*60)
    test1 = test_parse_multiple_import_files()
    print()

    print("Test 2: Multiple offers*.xml files")
    print("-"*60)
    test2 = test_parse_multiple_offers_files()
    print()

    print("="*60)
    if test1 and test2:
        print("[OK] All tests passed!")
    else:
        print("[ERROR] Some tests failed")
    print("="*60)
