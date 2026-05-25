"""
Тест парсера CommerceML на большом файле
"""
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.insert(0, str(Path(__file__).parent / "src"))

from sync.commerceml_parser import CommerceMLParser

def test_parse_large_file():
    """Тест парсинга большого файла import.xml"""
    xml_path = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata - 4482bcd8-46ec-11f1-ac27-1063c8c9a4b2\import.xml"

    print(f"Parsing file: {xml_path}")
    print(f"File size: {Path(xml_path).stat().st_size / (1024*1024):.1f} MB")
    print()

    try:
        result = CommerceMLParser.parse_import_xml(xml_path)

        print(f"[OK] Parsing successful!")
        print(f"Categories found: {len(result['categories'])}")
        print(f"Products found: {len(result['products'])}")
        print()

        # Показываем первые 5 категорий
        if result['categories']:
            print("First 5 categories:")
            for cat in result['categories'][:5]:
                print(f"  - {cat['name']} (ID: {cat['id'][:20]}...)")
        print()

        # Показываем первые 5 товаров
        if result['products']:
            print("First 5 products:")
            for prod in result['products'][:5]:
                print(f"  - {prod['name']} (ID: {prod['id'][:20]}...)")
                print(f"    Category: {prod['category_id'][:20] if prod['category_id'] else 'None'}...")

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_parse_small_file():
    """Тест парсинга маленького файла import0_1.xml"""
    xml_path = r"E:\WORK_RUCHEEK\OrderManager\Central_office\CommerceML\webdata\import0_1.xml"

    print(f"Parsing file: {xml_path}")
    print(f"File size: {Path(xml_path).stat().st_size / (1024*1024):.1f} MB")
    print()

    try:
        result = CommerceMLParser.parse_import_xml(xml_path)

        print(f"[OK] Parsing successful!")
        print(f"Categories found: {len(result['categories'])}")
        print(f"Products found: {len(result['products'])}")
        print()

        return True

    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("="*60)
    print("Testing CommerceML Parser")
    print("="*60)
    print()

    print("Test 1: Small file (2.5 MB)")
    print("-"*60)
    test1 = test_parse_small_file()
    print()

    print("Test 2: Large file (21 MB)")
    print("-"*60)
    test2 = test_parse_large_file()
    print()

    print("="*60)
    if test1 and test2:
        print("[OK] All tests passed!")
    else:
        print("[ERROR] Some tests failed")
    print("="*60)
