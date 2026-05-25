package sync

import (
	"encoding/xml"
	"io/ioutil"
	"log"
	"path/filepath"
	"strconv"
	"strings"
)

// CommerceMLParser - парсер для формата CommerceML (обмен с 1С)
type CommerceMLParser struct{}

// ImportData - данные импорта
type ImportData struct {
	Categories []CategoryData `xml:"-"`
	Products   []ProductData  `xml:"-"`
}

// CategoryData - данные категории из XML
type CategoryData struct {
	ID       string
	Name     string
	ParentID string
}

// ProductData - данные товара из XML
type ProductData struct {
	ID          string
	Name        string
	Article     string
	Barcode     string
	Unit        string
	CategoryID  string
	Description string
	ImageURL    string
}

// OfferData - данные предложения (цены и остатки)
type OfferData struct {
	ID        string
	ProductID string
	Price     float64
	Quantity  float64
	IsActive  bool
}

// OrderData - данные заказа из XML
type OrderData struct {
	ID         string
	Number     string
	Date       string
	ClientID   string
	ClientName string
	Total      float64
	Status     string
	Items      []OrderItemData
}

// OrderItemData - данные позиции заказа
type OrderItemData struct {
	ProductID string
	Name      string
	Quantity  float64
	Price     float64
	Total     float64
}

// ParseImportXML - парсинг import.xml
func ParseImportXML(xmlPath string) (*ImportData, error) {
	data, err := ioutil.ReadFile(xmlPath)
	if err != nil {
		return nil, err
	}

	result := &ImportData{
		Categories: []CategoryData{},
		Products:   []ProductData{},
	}

	// Простой парсинг XML без namespace
	root := parseXML(string(data))
	
	// Парсим категории
	if groups := findElement(root, "Группы"); groups != nil {
		result.Categories = parseCategories(groups, "")
	}

	// Парсим товары
	if catalog := findElement(root, "Каталог"); catalog != nil {
		if products := findElement(catalog, "Товары"); products != nil {
			result.Products = parseProducts(products)
		}
	}

	log.Printf("Parsed import.xml: %d categories, %d products", len(result.Categories), len(result.Products))
	return result, nil
}

// parseCategories - рекурсивный парсинг категорий
func parseCategories(elem *xmlElement, parentID string) []CategoryData {
	var categories []CategoryData

	for _, group := range findElements(elem, "Группа") {
		category := CategoryData{
			ID:       getElementText(group, "Ид"),
			Name:     getElementText(group, "Наименование"),
			ParentID: parentID,
		}
		categories = append(categories, category)

		// Рекурсивно парсим подгруппы
		if subgroups := findElement(group, "Группы"); subgroups != nil {
			subCats := parseCategories(subgroups, category.ID)
			categories = append(categories, subCats...)
		}
	}

	return categories
}

// parseProducts - парсинг товаров
func parseProducts(elem *xmlElement) []ProductData {
	var products []ProductData

	for _, product := range findElements(elem, "Товар") {
		p := ProductData{
			ID:          getElementText(product, "Ид"),
			Name:        getElementText(product, "Наименование"),
			Article:     getElementText(product, "Артикул"),
			Unit:        "шт",
			Description: getElementText(product, "Описание"),
		}

		// Артикул из реквизитов
		if requisites := findElement(product, "ЗначенияРеквизитов"); requisites != nil {
			for _, req := range findElements(requisites, "ЗначениеРеквизита") {
				reqName := getElementText(req, "Наименование")
				if reqName == "Код" {
					if val := getElementText(req, "Значение"); val != "" {
						p.Article = val
					}
					break
				}
			}
		}

		// Штрихкод
		if barcode := findElement(product, "ШтрихКод"); barcode != nil {
			p.Barcode = barcode.CharData
		}

		// Единица измерения
		if unit := findElement(product, "БазоваяЕдиница"); unit != nil {
			if name := unit.GetAttribute("НаименованиеПолное"); name != "" {
				p.Unit = name
			}
		}

		// Категория
		if groups := findElement(product, "Группы"); groups != nil {
			if groupID := getElementText(groups, "Ид"); groupID != "" {
				p.CategoryID = groupID
			}
		}

		// Изображение
		if image := findElement(product, "Картинка"); image != nil {
			p.ImageURL = image.CharData
		}

		products = append(products, p)
	}

	return products
}

// ParseOffersXML - парсинг offers.xml
func ParseOffersXML(xmlPath string) ([]OfferData, error) {
	data, err := ioutil.ReadFile(xmlPath)
	if err != nil {
		return nil, err
	}

	var offers []OfferData
	root := parseXML(string(data))

	if packageElem := findElement(root, "ПакетПредложений"); packageElem != nil {
		if offersElem := findElement(packageElem, "Предложения"); offersElem != nil {
			for _, offer := range findElements(offersElem, "Предложение") {
				o := OfferData{
					ID:       getElementText(offer, "Ид"),
					IsActive: true,
				}

				// ID товара
				if productID := findElement(offer, "Ид"); productID != nil {
					o.ProductID = productID.CharData
				}

				// Цена
				if prices := findElement(offer, "Цены"); prices != nil {
					if priceElem := findElement(prices, "Цена"); priceElem != nil {
						if priceStr := getElementText(priceElem, "ЦенаЗаЕдиницу"); priceStr != "" {
							if price, err := strconv.ParseFloat(priceStr, 64); err == nil {
								o.Price = price
							}
						}
					}
				}

				// Количество
				if quantity := findElement(offer, "Количество"); quantity != nil {
					if qty, err := strconv.ParseFloat(quantity.CharData, 64); err == nil {
						o.Quantity = qty
					}
				}

				offers = append(offers, o)
			}
		}
	}

	log.Printf("Parsed offers.xml: %d offers", len(offers))
	return offers, nil
}

// ParseOrdersXML - парсинг orders.xml
func ParseOrdersXML(xmlPath string) ([]OrderData, error) {
	data, err := ioutil.ReadFile(xmlPath)
	if err != nil {
		return nil, err
	}

	var orders []OrderData
	root := parseXML(string(data))

	for _, doc := range findElements(root, "Документ") {
		order := OrderData{
			ID:     getElementText(doc, "Ид"),
			Number: getElementText(doc, "Номер"),
			Date:   getElementText(doc, "Дата"),
			Status: "new",
		}

		// Контрагент
		if contragent := findElement(doc, "Контрагент"); contragent != nil {
			order.ClientID = getElementText(contragent, "Ид")
			order.ClientName = getElementText(contragent, "Наименование")
		}

		// Сумма
		if total := findElement(doc, "Сумма"); total != nil {
			if sum, err := strconv.ParseFloat(total.CharData, 64); err == nil {
				order.Total = sum
			}
		}

		// Товары
		if products := findElement(doc, "Товары"); products != nil {
			for _, item := range findElements(products, "Товар") {
				orderItem := OrderItemData{
					ProductID: getElementText(item, "Ид"),
					Name:      getElementText(item, "Наименование"),
				}

				if quantity := findElement(item, "Количество"); quantity != nil {
					if qty, err := strconv.ParseFloat(quantity.CharData, 64); err == nil {
						orderItem.Quantity = qty
					}
				}

				if price := findElement(item, "ЦенаЗаЕдиницу"); price != nil {
					if p, err := strconv.ParseFloat(price.CharData, 64); err == nil {
						orderItem.Price = p
					}
				}

				if total := findElement(item, "Сумма"); total != nil {
					if t, err := strconv.ParseFloat(total.CharData, 64); err == nil {
						orderItem.Total = t
					}
				}

				order.Items = append(order.Items, orderItem)
			}
		}

		orders = append(orders, order)
	}

	log.Printf("Parsed orders.xml: %d orders", len(orders))
	return orders, nil
}

// Вспомогательные структуры и функции для простого XML парсинга

type xmlElement struct {
	Name       string
	Attributes []xml.Attr
	Children   []*xmlElement
	CharData   string
}

func (e *xmlElement) GetAttribute(name string) string {
	for _, attr := range e.Attributes {
		if attr.Name.Local == name {
			return attr.Value
		}
	}
	return ""
}

func parseXML(data string) *xmlElement {
	decoder := xml.NewDecoder(strings.NewReader(data))
	var root *xmlElement
	var stack []*xmlElement

	for {
		token, err := decoder.Token()
		if err != nil {
			break
		}

		switch t := token.(type) {
		case xml.StartElement:
			elem := &xmlElement{
				Name:       t.Name.Local,
				Attributes: t.Attr,
			}
			if len(stack) > 0 {
				parent := stack[len(stack)-1]
				parent.Children = append(parent.Children, elem)
			} else {
				root = elem
			}
			stack = append(stack, elem)

		case xml.EndElement:
			if len(stack) > 0 {
				stack = stack[:len(stack)-1]
			}

		case xml.CharData:
			if len(stack) > 0 {
				current := stack[len(stack)-1]
				current.CharData += strings.TrimSpace(string(t))
			}
		}
	}

	return root
}

func findElement(parent *xmlElement, name string) *xmlElement {
	if parent == nil {
		return nil
	}
	for _, child := range parent.Children {
		if child.Name == name {
			return child
		}
		if found := findElement(child, name); found != nil {
			return found
		}
	}
	return nil
}

func findElements(parent *xmlElement, name string) []*xmlElement {
	var result []*xmlElement
	if parent == nil {
		return result
	}
	for _, child := range parent.Children {
		if child.Name == name {
			result = append(result, child)
		}
		result = append(result, findElements(child, name)...)
	}
	return result
}

func getElementText(parent *xmlElement, name string) string {
	if elem := findElement(parent, name); elem != nil {
		return elem.CharData
	}
	return ""
}

// ParseImportFiles - парсинг нескольких import файлов
func ParseImportFiles(directory, pattern string) (*ImportData, error) {
	files, err := filepath.Glob(filepath.Join(directory, pattern))
	if err != nil {
		return nil, err
	}

	result := &ImportData{
		Categories: []CategoryData{},
		Products:   []ProductData{},
	}

	categoryIDs := make(map[string]bool)
	productIDs := make(map[string]bool)

	for _, file := range files {
		log.Printf("Parsing %s...", filepath.Base(file))
		data, err := ParseImportXML(file)
		if err != nil {
			return nil, err
		}

		// Добавляем категории без дубликатов
		for _, cat := range data.Categories {
			if !categoryIDs[cat.ID] {
				result.Categories = append(result.Categories, cat)
				categoryIDs[cat.ID] = true
			}
		}

		// Добавляем товары без дубликатов
		for _, prod := range data.Products {
			if !productIDs[prod.ID] {
				result.Products = append(result.Products, prod)
				productIDs[prod.ID] = true
			}
		}
	}

	log.Printf("Total parsed: %d categories, %d products from %d files",
		len(result.Categories), len(result.Products), len(files))

	return result, nil
}

// ParseOffersFiles - парсинг нескольких offers файлов
func ParseOffersFiles(directory, pattern string) ([]OfferData, error) {
	files, err := filepath.Glob(filepath.Join(directory, pattern))
	if err != nil {
		return nil, err
	}

	var allOffers []OfferData
	offerIDs := make(map[string]bool)

	for _, file := range files {
		log.Printf("Parsing %s...", filepath.Base(file))
		offers, err := ParseOffersXML(file)
		if err != nil {
			return nil, err
		}

		for _, offer := range offers {
			if !offerIDs[offer.ID] {
				allOffers = append(allOffers, offer)
				offerIDs[offer.ID] = true
			}
		}
	}

	log.Printf("Total parsed: %d offers from %d files", len(allOffers), len(files))
	return allOffers, nil
}
