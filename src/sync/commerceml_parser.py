"""
Парсер CommerceML для импорта данных из 1С
"""
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime
import logging
from pathlib import Path
import glob

logger = logging.getLogger(__name__)


class CommerceMLParser:
    """Парсер для формата CommerceML (обмен с 1С)"""

    @staticmethod
    def _detect_namespace(root) -> Dict:
        """
        Автоматическое определение namespace из корневого элемента

        Args:
            root: Корневой элемент XML

        Returns:
            Dict с namespace для поиска элементов
        """
        # Получаем namespace из тега корневого элемента
        ns_match = root.tag.split('}')[0].strip('{') if '}' in root.tag else ''

        if ns_match:
            return {'': ns_match}
        else:
            # Если namespace не найден, пробуем без него
            return {}

    @staticmethod
    def parse_import_xml(xml_path: str) -> Dict:
        """
        Парсинг import.xml - товары и категории

        Args:
            xml_path: Путь к файлу import.xml

        Returns:
            Dict с ключами: categories, products
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Автоматически определяем namespace
            ns = CommerceMLParser._detect_namespace(root)
            logger.info(f"Detected namespace: {ns.get('', 'no namespace')}")

            result = {
                'categories': [],
                'products': []
            }

            # Парсим классификатор (категории)
            classifier = root.find('.//Классификатор', ns) if ns else root.find('.//Классификатор')
            if classifier is not None:
                groups = classifier.find('.//Группы', ns) if ns else classifier.find('.//Группы')
                if groups is not None:
                    result['categories'] = CommerceMLParser._parse_categories(groups, ns)

            # Парсим каталог (товары)
            catalog = root.find('.//Каталог', ns) if ns else root.find('.//Каталог')
            if catalog is not None:
                products = catalog.find('.//Товары', ns) if ns else catalog.find('.//Товары')
                if products is not None:
                    result['products'] = CommerceMLParser._parse_products(products, ns)

            logger.info(f"Parsed import.xml: {len(result['categories'])} categories, {len(result['products'])} products")
            return result

        except Exception as e:
            logger.error(f"Error parsing import.xml: {e}")
            raise

    @staticmethod
    def parse_import_files(directory: str, pattern: str = "import*.xml") -> Dict:
        """
        Парсинг множественных import файлов по маске

        Args:
            directory: Директория с файлами
            pattern: Маска файлов (например "import*.xml")

        Returns:
            Dict с объединенными категориями и товарами из всех файлов
        """
        try:
            dir_path = Path(directory)
            files = sorted(dir_path.glob(pattern))

            if not files:
                logger.warning(f"No files found matching {pattern} in {directory}")
                return {'categories': [], 'products': []}

            logger.info(f"Found {len(files)} import files to parse")

            # Объединяем результаты из всех файлов
            all_categories = []
            all_products = []
            category_ids = set()  # Для избежания дубликатов категорий
            product_ids = set()   # Для избежания дубликатов товаров

            for file_path in files:
                logger.info(f"Parsing {file_path.name}...")
                result = CommerceMLParser.parse_import_xml(str(file_path))

                # Добавляем категории (избегая дубликатов)
                for cat in result['categories']:
                    if cat['id'] not in category_ids:
                        all_categories.append(cat)
                        category_ids.add(cat['id'])

                # Добавляем товары (избегая дубликатов)
                for prod in result['products']:
                    if prod['id'] not in product_ids:
                        all_products.append(prod)
                        product_ids.add(prod['id'])

            logger.info(f"Total parsed: {len(all_categories)} categories, {len(all_products)} products from {len(files)} files")

            return {
                'categories': all_categories,
                'products': all_products
            }

        except Exception as e:
            logger.error(f"Error parsing import files: {e}")
            raise

    @staticmethod
    def _parse_categories(groups_element, ns: Dict) -> List[Dict]:
        """Парсинг категорий товаров"""
        categories = []

        def parse_group(group_elem, parent_id=None):
            """Рекурсивный парсинг группы и её подгрупп"""
            category = {
                'id': group_elem.findtext('Ид', '', ns) if ns else group_elem.findtext('Ид', ''),
                'name': group_elem.findtext('Наименование', '', ns) if ns else group_elem.findtext('Наименование', ''),
                'parent_id': parent_id
            }
            categories.append(category)

            # Парсим подгруппы
            subgroups = group_elem.find('Группы', ns) if ns else group_elem.find('Группы')
            if subgroups is not None:
                for subgroup in (subgroups.findall('Группа', ns) if ns else subgroups.findall('Группа')):
                    parse_group(subgroup, category['id'])

        # Парсим все группы верхнего уровня
        for group in (groups_element.findall('Группа', ns) if ns else groups_element.findall('Группа')):
            parse_group(group)

        return categories

    @staticmethod
    def _parse_products(products_element, ns: Dict) -> List[Dict]:
        """Парсинг товаров"""
        products = []

        for product_elem in (products_element.findall('.//Товар', ns) if ns else products_element.findall('.//Товар')):
            product = {
                'id': product_elem.findtext('Ид', '', ns) if ns else product_elem.findtext('Ид', ''),
                'name': product_elem.findtext('Наименование', '', ns) if ns else product_elem.findtext('Наименование', ''),
                'article': product_elem.findtext('Артикул', '', ns) if ns else product_elem.findtext('Артикул', ''),
                'barcode': None,
                'unit': 'шт',
                'category_id': None,
                'description': product_elem.findtext('Описание', '', ns) if ns else product_elem.findtext('Описание', ''),
                'image_url': None
            }

            # Артикул из реквизитов (приоритет над стандартным полем)
            requisites = product_elem.find('.//ЗначенияРеквизитов', ns) if ns else product_elem.find('.//ЗначенияРеквизитов')
            if requisites is not None:
                for req in (requisites.findall('.//ЗначениеРеквизита', ns) if ns else requisites.findall('.//ЗначениеРеквизита')):
                    req_name = req.findtext('Наименование', '', ns) if ns else req.findtext('Наименование', '')
                    if req_name == 'Код':
                        req_value = req.findtext('Значение', '', ns) if ns else req.findtext('Значение', '')
                        if req_value:
                            product['article'] = req_value
                        break

            # Штрихкод
            barcode_elem = product_elem.find('.//ШтрихКод', ns) if ns else product_elem.find('.//ШтрихКод')
            if barcode_elem is not None:
                product['barcode'] = barcode_elem.text

            # Единица измерения
            unit_elem = product_elem.find('.//БазоваяЕдиница', ns) if ns else product_elem.find('.//БазоваяЕдиница')
            if unit_elem is not None:
                unit_name = unit_elem.get('НаименованиеПолное', '')
                if unit_name:
                    product['unit'] = unit_name

            # Категория
            groups = product_elem.find('.//Группы', ns) if ns else product_elem.find('.//Группы')
            if groups is not None:
                group_id = groups.findtext('Ид', '', ns) if ns else groups.findtext('Ид', '')
                if group_id:
                    product['category_id'] = group_id

            # Изображение
            images = product_elem.find('.//Картинка', ns) if ns else product_elem.find('.//Картинка')
            if images is not None:
                product['image_url'] = images.text

            products.append(product)

        return products

    @staticmethod
    def parse_offers_xml(xml_path: str) -> List[Dict]:
        """
        Парсинг offers.xml - цены и остатки

        Args:
            xml_path: Путь к файлу offers.xml

        Returns:
            List[Dict] с ценами и остатками
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Автоматически определяем namespace
            ns = CommerceMLParser._detect_namespace(root)

            offers = []

            # Парсим предложения из ПакетПредложений
            package = root.find('.//ПакетПредложений', ns) if ns else root.find('.//ПакетПредложений')
            if package is not None:
                offers_elem = package.find('.//Предложения', ns) if ns else package.find('.//Предложения')
                if offers_elem is not None:
                    for offer_elem in (offers_elem.findall('.//Предложение', ns) if ns else offers_elem.findall('.//Предложение')):
                        offer = {
                            'id': offer_elem.findtext('Ид', '', ns) if ns else offer_elem.findtext('Ид', ''),
                            'product_id': None,
                            'price': 0.0,
                            'quantity': 0.0,
                            'is_active': True
                        }

                        # ID товара
                        product_id_elem = offer_elem.find('.//Ид', ns) if ns else offer_elem.find('.//Ид')
                        if product_id_elem is not None:
                            offer['product_id'] = product_id_elem.text

                        # Цены
                        prices = offer_elem.find('.//Цены', ns) if ns else offer_elem.find('.//Цены')
                        if prices is not None:
                            price_elem = prices.find('.//Цена', ns) if ns else prices.find('.//Цена')
                            if price_elem is not None:
                                price_value = price_elem.findtext('ЦенаЗаЕдиницу', '0', ns) if ns else price_elem.findtext('ЦенаЗаЕдиницу', '0')
                                try:
                                    offer['price'] = float(price_value)
                                except ValueError:
                                    offer['price'] = 0.0

                        # Остатки
                        quantity_elem = offer_elem.find('.//Количество', ns) if ns else offer_elem.find('.//Количество')
                        if quantity_elem is not None:
                            try:
                                offer['quantity'] = float(quantity_elem.text)
                            except (ValueError, TypeError):
                                offer['quantity'] = 0.0

                        offers.append(offer)

            logger.info(f"Parsed offers.xml: {len(offers)} offers")
            return offers

        except Exception as e:
            logger.error(f"Error parsing offers.xml: {e}")
            raise

    @staticmethod
    def parse_offers_files(directory: str, pattern: str = "offers*.xml") -> List[Dict]:
        """
        Парсинг множественных offers файлов по маске

        Args:
            directory: Директория с файлами
            pattern: Маска файлов (например "offers*.xml")

        Returns:
            List[Dict] с объединенными предложениями из всех файлов
        """
        try:
            dir_path = Path(directory)
            files = sorted(dir_path.glob(pattern))

            if not files:
                logger.warning(f"No files found matching {pattern} in {directory}")
                return []

            logger.info(f"Found {len(files)} offers files to parse")

            # Объединяем результаты из всех файлов
            all_offers = []
            offer_ids = set()  # Для избежания дубликатов

            for file_path in files:
                logger.info(f"Parsing {file_path.name}...")
                offers = CommerceMLParser.parse_offers_xml(str(file_path))

                # Добавляем предложения (избегая дубликатов)
                for offer in offers:
                    if offer['id'] not in offer_ids:
                        all_offers.append(offer)
                        offer_ids.add(offer['id'])

            logger.info(f"Total parsed: {len(all_offers)} offers from {len(files)} files")
            return all_offers

        except Exception as e:
            logger.error(f"Error parsing offers files: {e}")
            raise

    @staticmethod
    def parse_orders_xml(xml_path: str) -> List[Dict]:
        """
        Парсинг orders.xml - заказы из 1С

        Args:
            xml_path: Путь к файлу orders.xml

        Returns:
            List[Dict] с заказами
        """
        try:
            tree = ET.parse(xml_path)
            root = tree.getroot()

            # Автоматически определяем namespace
            ns = CommerceMLParser._detect_namespace(root)

            orders = []

            # Парсим документы (заказы)
            for doc_elem in (root.findall('.//Документ', ns) if ns else root.findall('.//Документ')):
                order = {
                    'id': doc_elem.findtext('Ид', '', ns) if ns else doc_elem.findtext('Ид', ''),
                    'number': doc_elem.findtext('Номер', '', ns) if ns else doc_elem.findtext('Номер', ''),
                    'date': doc_elem.findtext('Дата', '', ns) if ns else doc_elem.findtext('Дата', ''),
                    'client_id': None,
                    'client_name': None,
                    'total': 0.0,
                    'status': 'new',
                    'items': []
                }

                # Контрагент
                contragent = doc_elem.find('.//Контрагент', ns) if ns else doc_elem.find('.//Контрагент')
                if contragent is not None:
                    order['client_id'] = contragent.findtext('Ид', '', ns) if ns else contragent.findtext('Ид', '')
                    order['client_name'] = contragent.findtext('Наименование', '', ns) if ns else contragent.findtext('Наименование', '')

                # Сумма
                total_elem = doc_elem.find('.//Сумма', ns) if ns else doc_elem.find('.//Сумма')
                if total_elem is not None:
                    try:
                        order['total'] = float(total_elem.text)
                    except (ValueError, TypeError):
                        order['total'] = 0.0

                # Товары
                products = doc_elem.find('.//Товары', ns) if ns else doc_elem.find('.//Товары')
                if products is not None:
                    for item_elem in (products.findall('.//Товар', ns) if ns else products.findall('.//Товар')):
                        item = {
                            'product_id': item_elem.findtext('Ид', '', ns) if ns else item_elem.findtext('Ид', ''),
                            'name': item_elem.findtext('Наименование', '', ns) if ns else item_elem.findtext('Наименование', ''),
                            'quantity': 0.0,
                            'price': 0.0,
                            'total': 0.0
                        }

                        # Количество
                        quantity_elem = item_elem.find('.//Количество', ns) if ns else item_elem.find('.//Количество')
                        if quantity_elem is not None:
                            try:
                                item['quantity'] = float(quantity_elem.text)
                            except (ValueError, TypeError):
                                item['quantity'] = 0.0

                        # Цена
                        price_elem = item_elem.find('.//ЦенаЗаЕдиницу', ns) if ns else item_elem.find('.//ЦенаЗаЕдиницу')
                        if price_elem is not None:
                            try:
                                item['price'] = float(price_elem.text)
                            except (ValueError, TypeError):
                                item['price'] = 0.0

                        # Сумма
                        total_elem = item_elem.find('.//Сумма', ns) if ns else item_elem.find('.//Сумма')
                        if total_elem is not None:
                            try:
                                item['total'] = float(total_elem.text)
                            except (ValueError, TypeError):
                                item['total'] = item['quantity'] * item['price']

                        order['items'].append(item)

                orders.append(order)

            logger.info(f"Parsed orders.xml: {len(orders)} orders")
            return orders

        except Exception as e:
            logger.error(f"Error parsing orders.xml: {e}")
            raise

    @staticmethod
    def generate_orders_xml(orders: List[Dict], output_path: str):
        """
        Генерация orders.xml для выгрузки в 1С

        Args:
            orders: Список заказов для выгрузки
            output_path: Путь для сохранения XML
        """
        try:
            # Создаем корневой элемент
            root = ET.Element('КоммерческаяИнформация')
            root.set('ВерсияСхемы', '2.10')
            root.set('ДатаФормирования', datetime.now().isoformat())

            for order in orders:
                doc = ET.SubElement(root, 'Документ')

                ET.SubElement(doc, 'Ид').text = str(order.get('id', ''))
                ET.SubElement(doc, 'Номер').text = order.get('number', '')
                ET.SubElement(doc, 'Дата').text = order.get('date', datetime.now().isoformat())
                ET.SubElement(doc, 'ХозОперация').text = 'Заказ товара'
                ET.SubElement(doc, 'Роль').text = 'Продавец'
                ET.SubElement(doc, 'Валюта').text = 'RUB'
                ET.SubElement(doc, 'Курс').text = '1'

                # Контрагенты
                contragents = ET.SubElement(doc, 'Контрагенты')
                contragent = ET.SubElement(contragents, 'Контрагент')
                ET.SubElement(contragent, 'Ид').text = str(order.get('client_id', ''))
                ET.SubElement(contragent, 'Наименование').text = order.get('client_name', '')
                ET.SubElement(contragent, 'Роль').text = 'Покупатель'
                ET.SubElement(contragent, 'ПолноеНаименование').text = order.get('client_name', '')

                # Телефон контрагента в контактах
                if order.get('client_phone'):
                    contacts = ET.SubElement(contragent, 'Контакты')
                    contact = ET.SubElement(contacts, 'Контакт')
                    ET.SubElement(contact, 'Тип').text = 'Телефон'
                    ET.SubElement(contact, 'Значение').text = order.get('client_phone', '')

                # Адрес доставки
                if order.get('address'):
                    ET.SubElement(doc, 'АдресДоставки').text = order.get('address', '')

                # Дата доставки
                if order.get('delivery_date'):
                    ET.SubElement(doc, 'ДатаДоставки').text = order.get('delivery_date', '')

                # Время доставки
                if order.get('delivery_time_slot'):
                    ET.SubElement(doc, 'ВремяДоставки').text = order.get('delivery_time_slot', '')

                # Комментарий
                if order.get('comment'):
                    ET.SubElement(doc, 'Комментарий').text = order.get('comment', '')

                # Реквизиты документа
                requisites = ET.SubElement(doc, 'ЗначенияРеквизитов')

                # Статус заказа
                req_status = ET.SubElement(requisites, 'ЗначениеРеквизита')
                ET.SubElement(req_status, 'Наименование').text = 'Статус'
                ET.SubElement(req_status, 'Значение').text = order.get('status', 'new')

                # Статус оплаты
                req_payment_status = ET.SubElement(requisites, 'ЗначениеРеквизита')
                ET.SubElement(req_payment_status, 'Наименование').text = 'СтатусОплаты'
                ET.SubElement(req_payment_status, 'Значение').text = order.get('payment_status', 'unpaid')

                # Способ оплаты
                req_payment_type = ET.SubElement(requisites, 'ЗначениеРеквизита')
                ET.SubElement(req_payment_type, 'Наименование').text = 'СпособОплаты'
                ET.SubElement(req_payment_type, 'Значение').text = order.get('payment_type', 'cash')

                # Использовано бонусов
                if order.get('bonus_used', 0) > 0:
                    req_bonus = ET.SubElement(requisites, 'ЗначениеРеквизита')
                    ET.SubElement(req_bonus, 'Наименование').text = 'ИспользованоБонусов'
                    ET.SubElement(req_bonus, 'Значение').text = str(order.get('bonus_used', 0))

                # Товары
                products = ET.SubElement(doc, 'Товары')
                for item in order.get('items', []):
                    product = ET.SubElement(products, 'Товар')
                    ET.SubElement(product, 'Ид').text = str(item.get('product_id', ''))
                    ET.SubElement(product, 'Наименование').text = item.get('name', '')

                    # Базовая единица измерения
                    base_unit = ET.SubElement(product, 'БазоваяЕдиница')
                    base_unit.set('Код', item.get('unit_code', '796'))
                    base_unit.set('НаименованиеПолное', 'Штука')
                    base_unit.set('МеждународноеСокращение', 'PCE')
                    base_unit.text = item.get('unit', 'шт')

                    ET.SubElement(product, 'ЦенаЗаЕдиницу').text = str(item.get('price', 0))
                    ET.SubElement(product, 'Количество').text = str(item.get('quantity', 0))
                    ET.SubElement(product, 'Сумма').text = str(item.get('total', 0))

                # Сумма документа
                ET.SubElement(doc, 'Сумма').text = str(order.get('total', 0))

            # Сохраняем в файл
            tree = ET.ElementTree(root)
            ET.indent(tree, space='  ')
            tree.write(output_path, encoding='utf-8', xml_declaration=True)

            logger.info(f"Generated orders.xml: {len(orders)} orders")

        except Exception as e:
            logger.error(f"Error generating orders.xml: {e}")
            raise
