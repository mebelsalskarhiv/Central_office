"""
Проверка что парсер возвращает и что попадает в БД
"""
import sys
sys.path.insert(0, 'src')

from sync.commerceml_parser import CommerceMLParser

# Парсим import.xml
print("Parsing import.xml...")
import_data = CommerceMLParser.parse_import_xml('CommerceML/webdata/import0_1.xml')

# Берем первый товар
first_product = import_data['products'][0]

print(f"\nFirst product from parser:")
print(f"  id: {first_product['id']}")
print(f"  name: {first_product['name']}")
print(f"  article: {first_product['article']}")
print(f"  barcode: {first_product['barcode']}")

# Парсим offers
print("\n\nParsing offers.xml...")
offers_list = CommerceMLParser.parse_offers_xml('CommerceML/webdata/offers0_1.xml')
print(f"Total offers: {len(offers_list)}")

if offers_list:
    first_offer = offers_list[0]
    print(f"\nFirst offer:")
    print(f"  id: {first_offer['id']}")
    print(f"  product_id: {first_offer['product_id']}")
    print(f"  price: {first_offer['price']}")
    print(f"  quantity: {first_offer['quantity']}")
