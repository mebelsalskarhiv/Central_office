"""
Детальная проверка парсинга реквизитов
"""
import xml.etree.ElementTree as ET

xml_path = 'CommerceML/webdata/import0_1.xml'

tree = ET.parse(xml_path)
root = tree.getroot()

NS = {
    '': 'urn:1C.ru:commerceml_2',
    'xs': 'http://www.w3.org/2001/XMLSchema',
    'xsi': 'http://www.w3.org/2001/XMLSchema-instance'
}

# Находим каталог
catalog = root.find('.//Каталог', NS)
if catalog is not None:
    print("OK: Katalog found")

    products = catalog.find('.//Товары', NS)
    if products is not None:
        print("OK: Tovary found")

        # Берем первый товар
        product = products.find('.//Товар', NS)
        if product is not None:
            name = product.findtext('Наименование', '', NS)
            print(f"\nOK: Product: {name}")

            # Ищем реквизиты
            requisites = product.find('.//ЗначенияРеквизитов', NS)
            if requisites is not None:
                print("OK: ZnacheniyaRekvizitov found")

                for req in requisites.findall('.//ЗначениеРеквизита', NS):
                    req_name = req.findtext('Наименование', '', NS)
                    req_value = req.findtext('Значение', '', NS)
                    print(f"  - {req_name}: {req_value}")

                    if req_name == 'Код':
                        print(f"\n*** ARTICLE FOUND: {req_value}")
            else:
                print("ERROR: ZnacheniyaRekvizitov NOT found")
                print("\nTrying without namespace:")
                requisites_no_ns = product.find('.//ЗначенияРеквизитов')
                if requisites_no_ns is not None:
                    print("OK: ZnacheniyaRekvizitov found WITHOUT namespace")
