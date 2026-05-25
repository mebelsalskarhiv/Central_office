"""
Тест парсинга артикула из XML
"""
import sys
sys.path.insert(0, 'src')

from sync.commerceml_parser import CommerceMLParser

# Парсим import.xml
import_data = CommerceMLParser.parse_import_xml('CommerceML/webdata/import0_1.xml')

# Ищем товар "Сок Вкусносок"
for product in import_data['products']:
    if 'Вкусносок' in product['name']:
        print(f"Товар: {product['name']}")
        print(f"ID: {product['id']}")
        print(f"Артикул: {product['article']}")
        print(f"Описание: {product['description']}")
        print()
        break
