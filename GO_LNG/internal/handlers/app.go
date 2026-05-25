package handlers

import (
	"context"
	"database/sql"
	"fmt"
	"log"
	"time"

	"github.com/ordermanager/central-office/internal/database"
	"github.com/ordermanager/central-office/internal/models"
	"github.com/ordermanager/central-office/internal/sync"
)

// App - основной обработчик приложения
type App struct {
	DB *database.Database
}

// NewApp - создание нового обработчика
func NewApp(db *database.Database) *App {
	return &App{DB: db}
}

// Startup - инициализация при запуске
func (a *App) Startup(ctx context.Context) error {
	log.Println("Application starting...")
	return nil
}

// Shutdown - очистка при закрытии
func (a *App) Shutdown(ctx context.Context) error {
	log.Println("Application shutting down...")
	if a.DB != nil {
		return a.DB.Close()
	}
	return nil
}

// GetOrders - получение списка заказов
func (a *App) GetOrders() ([]models.Order, error) {
	query := `
		SELECT o.id, o.external_id, o.order_number, o.manager_id, o.client_id,
		       COALESCE(o.address_id, 0), o.address_text, 
		       COALESCE(o.address_latitude, 0), COALESCE(o.address_longitude, 0),
		       o.delivery_date, o.delivery_time_slot, o.status, o.payment_status,
		       o.payment_type, o.total_amount, o.bonus_used, o.bonus_earned,
		       COALESCE(o.comment, ''), o.created_at, o.updated_at
		FROM orders o
		ORDER BY o.created_at DESC
	`

	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var orders []models.Order
	for rows.Next() {
		var order models.Order
		var addressID int64
		var lat, lon float64

		err := rows.Scan(
			&order.ID, &order.ExternalID, &order.OrderNumber, &order.ManagerID, &order.ClientID,
			&addressID, &order.AddressText, &lat, &lon,
			&order.DeliveryDate, &order.DeliveryTimeSlot, &order.Status, &order.PaymentStatus,
			&order.PaymentType, &order.TotalAmount, &order.BonusUsed, &order.BonusEarned,
			&order.Comment, &order.CreatedAt, &order.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}

		if addressID > 0 {
			order.AddressID = &addressID
		}
		if lat != 0 {
			order.AddressLatitude = &lat
		}
		if lon != 0 {
			order.AddressLongitude = &lon
		}

		orders = append(orders, order)
	}

	return orders, rows.Err()
}

// GetProducts - получение списка товаров
func (a *App) GetProducts() ([]models.Product, error) {
	query := `
		SELECT id, external_id, name, COALESCE(category, ''), 
		       category_id, price, unit, COALESCE(image_url, ''),
		       COALESCE(image_path, ''), COALESCE(article, ''),
		       COALESCE(barcode, ''), COALESCE(description, ''),
		       is_active, created_at, updated_at
		FROM products
		ORDER BY name
	`

	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var products []models.Product
	for rows.Next() {
		var product models.Product
		var categoryID sql.NullInt64

		err := rows.Scan(
			&product.ID, &product.ExternalID, &product.Name, &product.Category,
			&categoryID, &product.Price, &product.Unit, &product.ImageURL,
			&product.ImagePath, &product.Article, &product.Barcode,
			&product.Description, &product.IsActive, &product.CreatedAt, &product.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}

		if categoryID.Valid {
			product.CategoryID = &categoryID.Int64
		}

		products = append(products, product)
	}

	return products, rows.Err()
}

// GetClients - получение списка клиентов
func (a *App) GetClients() ([]models.Client, error) {
	query := `
		SELECT id, COALESCE(external_id, ''), phone, COALESCE(name, ''),
		       bonus_balance, total_orders, total_spent, last_order_date,
		       COALESCE(notes, ''), created_at, updated_at
		FROM clients
		ORDER BY name
	`

	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var clients []models.Client
	for rows.Next() {
		var client models.Client
		var lastOrderDate sql.NullTime

		err := rows.Scan(
			&client.ID, &client.ExternalID, &client.Phone, &client.Name,
			&client.BonusBalance, &client.TotalOrders, &client.TotalSpent,
			&lastOrderDate, &client.Notes, &client.CreatedAt, &client.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}

		if lastOrderDate.Valid {
			client.LastOrderDate = &lastOrderDate.Time
		}

		clients = append(clients, client)
	}

	return clients, rows.Err()
}

// GetManagers - получение списка менеджеров
func (a *App) GetManagers() ([]models.Manager, error) {
	query := `
		SELECT id, pin_code, name, COALESCE(phone, ''), COALESCE(email, ''),
		       status, last_sync_at, COALESCE(device_id, ''),
		       COALESCE(device_model, ''), COALESCE(app_version, ''),
		       created_at, updated_at
		FROM managers
		ORDER BY name
	`

	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var managers []models.Manager
	for rows.Next() {
		var manager models.Manager
		var lastSyncAt sql.NullTime

		err := rows.Scan(
			&manager.ID, &manager.PINCode, &manager.Name, &manager.Phone,
			&manager.Email, &manager.Status, &lastSyncAt, &manager.DeviceID,
			&manager.DeviceModel, &manager.AppVersion, &manager.CreatedAt,
			&manager.UpdatedAt,
		)
		if err != nil {
			return nil, err
		}

		if lastSyncAt.Valid {
			manager.LastSyncAt = &lastSyncAt.Time
		}

		managers = append(managers, manager)
	}

	return managers, rows.Err()
}

// ImportFrom1C - импорт товаров из 1С
func (a *App) ImportFrom1C(importPath, offersPath string) (map[string]interface{}, error) {
	stats := map[string]interface{}{
		"products_created": 0,
		"products_updated": 0,
		"categories_created": 0,
		"errors":           []string{},
	}

	// Определяем, директория это или файл
	importData, err := sync.ParseImportFiles(importPath, "import*.xml")
	if err != nil {
		// Пробуем как один файл
		importData, err = sync.ParseImportXML(importPath)
		if err != nil {
			return stats, fmt.Errorf("error parsing import: %w", err)
		}
	}

	// Парсим offers если есть
	var offersMap map[string]sync.OfferData
	if offersPath != "" {
		offersList, err := sync.ParseOffersFiles(offersPath, "offers*.xml")
		if err != nil {
			offersList, err = sync.ParseOffersXML(offersPath)
			if err != nil {
				log.Printf("Warning: could not parse offers: %v", err)
			}
		}
		offersMap = make(map[string]sync.OfferData)
		for _, offer := range offersList {
			offersMap[offer.ProductID] = offer
		}
	}

	// Импортируем категории
	categoryMap := make(map[string]int64)
	for _, catData := range importData.Categories {
		var existingID int64
		err := a.DB.DB.QueryRow(
			"SELECT id FROM categories WHERE external_id = ?",
			catData.ID,
		).Scan(&existingID)

		if err == sql.ErrNoRows {
			// Создаем новую категорию
			result, err := a.DB.DB.Exec(
				"INSERT INTO categories (external_id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
				catData.ID, catData.Name, time.Now(), time.Now(),
			)
			if err != nil {
				log.Printf("Error importing category %s: %v", catData.ID, err)
				continue
			}
			id, _ := result.LastInsertId()
			categoryMap[catData.ID] = id
			stats["categories_created"] = stats["categories_created"].(int) + 1
		} else if err == nil {
			// Обновляем существующую
			_, err = a.DB.DB.Exec(
				"UPDATE categories SET name = ?, updated_at = ? WHERE external_id = ?",
				catData.Name, time.Now(), catData.ID,
			)
			categoryMap[catData.ID] = existingID
		}
	}

	// Второй проход - устанавливаем parent_id
	for _, catData := range importData.Categories {
		if catData.ParentID != "" {
			if parentID, ok := categoryMap[catData.ParentID]; ok {
				_, err = a.DB.DB.Exec(
					"UPDATE categories SET parent_id = ? WHERE external_id = ?",
					parentID, catData.ID,
				)
			}
		}
	}

	// Импортируем товары
	for _, productData := range importData.Products {
		// Получаем цену из offers
		price := 0.0
		isActive := true
		if offer, ok := offersMap[productData.ID]; ok {
			price = offer.Price
			isActive = offer.IsActive
		}

		var existingID int64
		err := a.DB.DB.QueryRow(
			"SELECT id FROM products WHERE external_id = ?",
			productData.ID,
		).Scan(&existingID)

		if err == sql.ErrNoRows {
			// Создаем новый товар
			categoryID := categoryMap[productData.CategoryID]
			_, err = a.DB.DB.Exec(
				`INSERT INTO products (external_id, name, category, category_id, price, unit, 
				      article, barcode, image_url, is_active, created_at, updated_at)
				 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
				productData.ID, productData.Name, "",
				func() interface{} {
					if categoryID > 0 {
						return categoryID
					}
					return nil
				}(),
				price, productData.Unit, productData.Article, productData.Barcode,
				productData.ImageURL, isActive, time.Now(), time.Now(),
			)
			if err != nil {
				log.Printf("Error importing product %s: %v", productData.ID, err)
				continue
			}
			stats["products_created"] = stats["products_created"].(int) + 1
		} else if err == nil {
			// Обновляем существующий
			_, err = a.DB.DB.Exec(
				`UPDATE products SET name = ?, price = ?, unit = ?, article = ?,
				       barcode = ?, image_url = ?, is_active = ?, updated_at = ?
				 WHERE external_id = ?`,
				productData.Name, price, productData.Unit, productData.Article,
				productData.Barcode, productData.ImageURL, isActive, time.Now(),
				productData.ID,
			)
			stats["products_updated"] = stats["products_updated"].(int) + 1
		}
	}

	return stats, nil
}

// GetSettings - получение всех настроек
func (a *App) GetSettings() ([]models.Settings, error) {
	query := `SELECT id, key, value, COALESCE(description, ''), updated_at FROM settings`

	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var settings []models.Settings
	for rows.Next() {
		var setting models.Settings
		err := rows.Scan(&setting.ID, &setting.Key, &setting.Value, &setting.Description, &setting.UpdatedAt)
		if err != nil {
			return nil, err
		}
		settings = append(settings, setting)
	}

	return settings, rows.Err()
}

// UpdateSetting - обновление настройки
func (a *App) UpdateSetting(key, value string) error {
	return a.DB.SetSetting(key, value)
}

// GetSetting - получение одной настройки
func (a *App) GetSetting(key string) (string, error) {
	return a.DB.GetSetting(key)
}
