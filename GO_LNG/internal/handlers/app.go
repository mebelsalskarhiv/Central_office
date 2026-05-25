package handlers

import (
	"context"
	"database/sql"
	"fmt"
	"io"
	"os"
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

// GetOrderDetails - получение деталей заказа с позициями
func (a *App) GetOrderDetails(orderID int64) (map[string]interface{}, error) {
	result := make(map[string]interface{})
	
	// Получаем заказ
	var order models.Order
	var addressID sql.NullInt64
	var lat, lon sql.NullFloat64
	
	err := a.DB.DB.QueryRow(`
		SELECT o.id, o.external_id, o.order_number, o.manager_id, o.client_id,
		       o.address_id, o.address_text, o.address_latitude, o.address_longitude,
		       o.delivery_date, o.delivery_time_slot, o.status, o.payment_status,
		       o.payment_type, o.total_amount, o.bonus_used, o.bonus_earned,
		       o.comment, o.created_at, o.updated_at
		FROM orders o WHERE o.id = ?`, orderID).Scan(
		&order.ID, &order.ExternalID, &order.OrderNumber, &order.ManagerID, &order.ClientID,
		&addressID, &order.AddressText, &lat, &lon,
		&order.DeliveryDate, &order.DeliveryTimeSlot, &order.Status, &order.PaymentStatus,
		&order.PaymentType, &order.TotalAmount, &order.BonusUsed, &order.BonusEarned,
		&order.Comment, &order.CreatedAt, &order.UpdatedAt,
	)
	if err != nil {
		return nil, fmt.Errorf("order not found: %w", err)
	}
	
	if addressID.Valid {
		order.AddressID = &addressID.Int64
	}
	if lat.Valid {
		order.AddressLatitude = &lat.Float64
	}
	if lon.Valid {
		order.AddressLongitude = &lon.Float64
	}
	
	result["order"] = order
	
	// Получаем клиента
	var client models.Client
	var lastOrderDate sql.NullTime
	err = a.DB.DB.QueryRow(`
		SELECT id, COALESCE(external_id, ''), phone, COALESCE(name, ''),
		       bonus_balance, total_orders, total_spent, last_order_date,
		       COALESCE(notes, ''), created_at, updated_at
		FROM clients WHERE id = ?`, order.ClientID).Scan(
		&client.ID, &client.ExternalID, &client.Phone, &client.Name,
		&client.BonusBalance, &client.TotalOrders, &client.TotalSpent,
		&lastOrderDate, &client.Notes, &client.CreatedAt, &client.UpdatedAt,
	)
	if err == nil {
		if lastOrderDate.Valid {
			client.LastOrderDate = &lastOrderDate.Time
		}
		result["client"] = client
	}
	
	// Получаем менеджера
	var manager models.Manager
	var lastSyncAt sql.NullTime
	err = a.DB.DB.QueryRow(`
		SELECT id, pin_code, name, COALESCE(phone, ''), COALESCE(email, ''),
		       status, last_sync_at, COALESCE(device_id, ''),
		       COALESCE(device_model, ''), COALESCE(app_version, ''),
		       created_at, updated_at
		FROM managers WHERE id = ?`, order.ManagerID).Scan(
		&manager.ID, &manager.PINCode, &manager.Name, &manager.Phone,
		&manager.Email, &manager.Status, &lastSyncAt, &manager.DeviceID,
		&manager.DeviceModel, &manager.AppVersion, &manager.CreatedAt,
		&manager.UpdatedAt,
	)
	if err == nil {
		if lastSyncAt.Valid {
			manager.LastSyncAt = &lastSyncAt.Time
		}
		result["manager"] = manager
	}
	
	// Получаем позиции заказа
	rows, err := a.DB.DB.Query(`
		SELECT id, order_id, product_id, product_name, price_at_moment, quantity, 
		       0, 0, sum, COALESCE(product_external_id, ''), created_at
		FROM order_items WHERE order_id = ? ORDER BY id`, orderID)
	if err != nil {
		return result, nil
	}
	defer rows.Close()
	
	var items []models.OrderItem
	for rows.Next() {
		var item models.OrderItem
		var productID sql.NullInt64
		err := rows.Scan(&item.ID, &item.OrderID, &productID, &item.ProductName,
			&item.PriceAtMoment, &item.Quantity, &item.Sum, &item.ProductExternalID)
		if err != nil {
			continue
		}
		if productID.Valid {
			item.ProductID = &productID.Int64
		}
		items = append(items, item)
	}
	result["items"] = items
	
	return result, nil
}

// UpdateProduct - обновление товара
func (a *App) UpdateProduct(product models.Product) error {
	_, err := a.DB.DB.Exec(`
		UPDATE products SET name = ?, category = ?, price = ?, unit = ?,
		       article = ?, barcode = ?, description = ?, image_url = ?,
		       is_active = ?, updated_at = ?
		WHERE id = ?`,
		product.Name, product.Category, product.Price, product.Unit,
		product.Article, product.Barcode, product.Description, product.ImageURL,
		product.IsActive, time.Now(), product.ID)
	return err
}

// CreateProduct - создание товара
func (a *App) CreateProduct(product models.Product) (int64, error) {
	result, err := a.DB.DB.Exec(`
		INSERT INTO products (external_id, name, category, category_id, price, unit,
		      article, barcode, description, image_url, is_active, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		product.ExternalID, product.Name, product.Category, product.CategoryID,
		product.Price, product.Unit, product.Article, product.Barcode,
		product.Description, product.ImageURL, product.IsActive, time.Now(), time.Now())
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// DeleteProduct - удаление товара
func (a *App) DeleteProduct(id int64) error {
	_, err := a.DB.DB.Exec("DELETE FROM products WHERE id = ?", id)
	return err
}

// UpdateClient - обновление клиента
func (a *App) UpdateClient(client models.Client) error {
	_, err := a.DB.DB.Exec(`
		UPDATE clients SET phone = ?, name = ?, notes = ?,
		       bonus_balance = ?, total_orders = ?, total_spent = ?,
		       last_order_date = ?, updated_at = ?
		WHERE id = ?`,
		client.Phone, client.Name, client.Notes,
		client.BonusBalance, client.TotalOrders, client.TotalSpent,
		client.LastOrderDate, time.Now(), client.ID)
	return err
}

// CreateClient - создание клиента
func (a *App) CreateClient(client models.Client) (int64, error) {
	result, err := a.DB.DB.Exec(`
		INSERT INTO clients (external_id, phone, name, bonus_balance, total_orders,
		      total_spent, last_order_date, notes, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		client.ExternalID, client.Phone, client.Name, client.BonusBalance,
		client.TotalOrders, client.TotalSpent, client.LastOrderDate,
		client.Notes, time.Now(), time.Now())
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// DeleteClient - удаление клиента
func (a *App) DeleteClient(id int64) error {
	_, err := a.DB.DB.Exec("DELETE FROM clients WHERE id = ?", id)
	return err
}

// UpdateManager - обновление менеджера
func (a *App) UpdateManager(manager models.Manager) error {
	_, err := a.DB.DB.Exec(`
		UPDATE managers SET pin_code = ?, name = ?, phone = ?, email = ?,
		       status = ?, device_id = ?, device_model = ?, app_version = ?,
		       updated_at = ?
		WHERE id = ?`,
		manager.PINCode, manager.Name, manager.Phone, manager.Email,
		manager.Status, manager.DeviceID, manager.DeviceModel,
		manager.AppVersion, time.Now(), manager.ID)
	return err
}

// CreateManager - создание менеджера
func (a *App) CreateManager(manager models.Manager) (int64, error) {
	result, err := a.DB.DB.Exec(`
		INSERT INTO managers (pin_code, name, phone, email, status,
		      device_id, device_model, app_version, created_at, updated_at)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
		manager.PINCode, manager.Name, manager.Phone, manager.Email,
		manager.Status, manager.DeviceID, manager.DeviceModel,
		manager.AppVersion, time.Now(), time.Now())
	if err != nil {
		return 0, err
	}
	return result.LastInsertId()
}

// DeleteManager - удаление менеджера
func (a *App) DeleteManager(id int64) error {
	_, err := a.DB.DB.Exec("DELETE FROM managers WHERE id = ?", id)
	return err
}

// GetAnalytics - получение аналитики
func (a *App) GetAnalytics(periodDays int) (map[string]interface{}, error) {
	result := make(map[string]interface{})
	
	// Период
	startDate := time.Now().AddDate(0, 0, -periodDays)
	
	// Общая статистика
	var totalOrders, totalRevenue, avgOrderValue float64
	err := a.DB.DB.QueryRow(`
		SELECT COUNT(*), COALESCE(SUM(total_amount), 0), 
		       COALESCE(AVG(total_amount), 0)
		FROM orders WHERE created_at >= ?`, startDate).Scan(
		&totalOrders, &totalRevenue, &avgOrderValue)
	if err != nil {
		totalOrders = 0
		totalRevenue = 0
		avgOrderValue = 0
	}
	
	result["total_orders"] = int(totalOrders)
	result["total_revenue"] = totalRevenue
	result["avg_order_value"] = avgOrderValue
	
	// Заказы по статусам
	statusRows, err := a.DB.DB.Query(`
		SELECT status, COUNT(*) as count
		FROM orders WHERE created_at >= ?
		GROUP BY status`, startDate)
	if err == nil {
		defer statusRows.Close()
		statusStats := make(map[string]int)
		for statusRows.Next() {
			var status string
			var count int
			statusRows.Scan(&status, &count)
			statusStats[status] = count
		}
		result["orders_by_status"] = statusStats
	}
	
	// Топ товаров
	topProductsRows, err := a.DB.DB.Query(`
		SELECT oi.product_name, SUM(oi.quantity) as total_qty, SUM(oi.total) as total_sum
		FROM order_items oi
		JOIN orders o ON oi.order_id = o.id
		WHERE o.created_at >= ?
		GROUP BY oi.product_id, oi.product_name
		ORDER BY total_sum DESC LIMIT 10`, startDate)
	if err == nil {
		defer topProductsRows.Close()
		type ProductStat struct {
			Name     string  `json:"name"`
			Quantity int     `json:"quantity"`
			Sum      float64 `json:"sum"`
		}
		var topProducts []ProductStat
		for topProductsRows.Next() {
			var ps ProductStat
			topProductsRows.Scan(&ps.Name, &ps.Quantity, &ps.Sum)
			topProducts = append(topProducts, ps)
		}
		result["top_products"] = topProducts
	}
	
	// Заказы по дням
	dailyRows, err := a.DB.DB.Query(`
		SELECT DATE(created_at) as date, COUNT(*) as count, SUM(total_amount) as revenue
		FROM orders WHERE created_at >= ?
		GROUP BY DATE(created_at) ORDER BY date`, startDate)
	if err == nil {
		defer dailyRows.Close()
		type DailyStat struct {
			Date    string  `json:"date"`
			Orders  int     `json:"orders"`
			Revenue float64 `json:"revenue"`
		}
		var dailyStats []DailyStat
		for dailyRows.Next() {
			var ds DailyStat
			dailyRows.Scan(&ds.Date, &ds.Orders, &ds.Revenue)
			dailyStats = append(dailyStats, ds)
		}
		result["daily_stats"] = dailyStats
	}
	
	// Топ клиентов
	topClientsRows, err := a.DB.DB.Query(`
		SELECT c.name, c.phone, COUNT(o.id) as order_count, SUM(o.total_amount) as total_spent
		FROM clients c
		JOIN orders o ON c.id = o.client_id
		WHERE o.created_at >= ?
		GROUP BY c.id, c.name, c.phone
		ORDER BY total_spent DESC LIMIT 10`, startDate)
	if err == nil {
		defer topClientsRows.Close()
		type ClientStat struct {
			Name       string  `json:"name"`
			Phone      string  `json:"phone"`
			OrderCount int     `json:"order_count"`
			TotalSpent float64 `json:"total_spent"`
		}
		var topClients []ClientStat
		for topClientsRows.Next() {
			var cs ClientStat
			topClientsRows.Scan(&cs.Name, &cs.Phone, &cs.OrderCount, &cs.TotalSpent)
			topClients = append(topClients, cs)
		}
		result["top_clients"] = topClients
	}
	
	return result, nil
}

// GetDeliveryMap - получение данных для карты доставок
func (a *App) GetDeliveryMap(date string) ([]map[string]interface{}, error) {
	var query string
	var args []interface{}
	
	if date != "" {
		query = `
			SELECT id, order_number, address_text, address_latitude, address_longitude,
			       client_id, status, delivery_time_slot, total_amount
			FROM orders 
			WHERE DATE(delivery_date) = ? AND address_latitude IS NOT NULL AND address_longitude IS NOT NULL
			ORDER BY delivery_time_slot`
		args = append(args, date)
	} else {
		query = `
			SELECT id, order_number, address_text, address_latitude, address_longitude,
			       client_id, status, delivery_time_slot, total_amount
			FROM orders 
			WHERE address_latitude IS NOT NULL AND address_longitude IS NOT NULL
			ORDER BY delivery_date DESC`
	}
	
	rows, err := a.DB.DB.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	
	var deliveries []map[string]interface{}
	for rows.Next() {
		var id int64
		var orderNum, addressText, clientID, status, timeSlot string
		var amount float64
		var lat, lon float64
		
		err := rows.Scan(&id, &orderNum, &addressText, &lat, &lon, &clientID, &status, &timeSlot, &amount)
		if err != nil {
			continue
		}
		
		deliveries = append(deliveries, map[string]interface{}{
			"id":         id,
			"order_number": orderNum,
			"address":    addressText,
			"latitude":   lat,
			"longitude":  lon,
			"client_id":  clientID,
			"status":     status,
			"time_slot":  timeSlot,
			"amount":     amount,
		})
	}
	
	return deliveries, nil
}

// ExportToCSV - экспорт данных в CSV
func (a *App) ExportToCSV(entityType string) (string, error) {
	var query string
	var headers []string
	
	switch entityType {
	case "orders":
		query = `SELECT order_number, delivery_date, client_id, address_text, 
		                status, payment_status, total_amount, created_at
		         FROM orders ORDER BY created_at DESC`
		headers = []string{"Номер заказа", "Дата доставки", "Клиент", "Адрес", "Статус", "Оплата", "Сумма", "Создан"}
	case "products":
		query = `SELECT article, name, category, price, unit, is_active, created_at
		         FROM products ORDER BY name`
		headers = []string{"Артикул", "Наименование", "Категория", "Цена", "Ед.", "Активен", "Создан"}
	case "clients":
		query = `SELECT name, phone, bonus_balance, total_orders, total_spent, created_at
		         FROM clients ORDER BY name`
		headers = []string{"Имя", "Телефон", "Бонусы", "Заказов", "Потрачено", "Создан"}
	case "managers":
		query = `SELECT pin_code, name, phone, email, status, created_at
		         FROM managers ORDER BY name`
		headers = []string{"PIN", "Имя", "Телефон", "Email", "Статус", "Создан"}
	default:
		return "", fmt.Errorf("unknown entity type: %s", entityType)
	}
	
	rows, err := a.DB.DB.Query(query)
	if err != nil {
		return "", err
	}
	defer rows.Close()
	
	// Создаем CSV в base64 для передачи на фронтенд
	csvContent := ""
	for i, h := range headers {
		if i > 0 {
			csvContent += ","
		}
		csvContent += "\"" + h + "\""
	}
	csvContent += "\n"
	
	cols := len(headers)
	values := make([]interface{}, cols)
	valuePtrs := make([]interface{}, cols)
	for i := range values {
		valuePtrs[i] = &values[i]
	}
	
	for rows.Next() {
		if err := rows.Scan(valuePtrs...); err != nil {
			continue
		}
		line := ""
		for i, v := range values {
			if i > 0 {
				line += ","
			}
			var val string
			if v == nil {
				val = ""
			} else {
				val = fmt.Sprintf("%v", v)
			}
			line += "\"" + val + "\""
		}
		csvContent += line + "\n"
	}
	
	return csvContent, nil
}

// BackupDatabase - резервное копирование БД
func (a *App) BackupDatabase(backupPath string) (string, error) {
	// Получаем путь к текущей БД
	dbPath := "ordermanager.db" // default path
	
	// Копируем файл БД
	sourceFile, err := os.Open(dbPath)
	if err != nil {
		return "", fmt.Errorf("failed to open database: %w", err)
	}
	defer sourceFile.Close()
	
	// Создаем backup файл с timestamp
	timestamp := time.Now().Format("20060102_150405")
	backupFileName := fmt.Sprintf("backup_%s.db", timestamp)
	if backupPath != "" {
		backupFileName = backupPath
	}
	
	destFile, err := os.Create(backupFileName)
	if err != nil {
		return "", fmt.Errorf("failed to create backup file: %w", err)
	}
	defer destFile.Close()
	
	_, err = io.Copy(destFile, sourceFile)
	if err != nil {
		return "", fmt.Errorf("failed to copy database: %w", err)
	}
	
	return backupFileName, nil
}

// SyncWithMobile - синхронизация с мобильными устройствами
func (a *App) SyncWithMobile(deviceID string) (map[string]interface{}, error) {
	result := make(map[string]interface{})
	result["status"] = "success"
	result["synced_at"] = time.Now().Format(time.RFC3339)
	
	// Получаем данные для синхронизации
	ordersRows, err := a.DB.DB.Query(`
		SELECT id, external_id, order_number, manager_id, client_id,
		       address_text, delivery_date, delivery_time_slot, status,
		       payment_status, payment_type, total_amount, bonus_used,
		       bonus_earned, comment, updated_at
		FROM orders WHERE updated_at > datetime('now', '-1 day')`)
	if err == nil {
		defer ordersRows.Close()
		var orders []models.Order
		for ordersRows.Next() {
			var order models.Order
			var addrID interface{}
			ordersRows.Scan(&order.ID, &order.ExternalID, &order.OrderNumber,
				&order.ManagerID, &order.ClientID, &addrID, &order.AddressText,
				&order.DeliveryDate, &order.DeliveryTimeSlot, &order.Status,
				&order.PaymentStatus, &order.PaymentType, &order.TotalAmount,
				&order.BonusUsed, &order.BonusEarned, &order.Comment, &order.UpdatedAt)
			orders = append(orders, order)
		}
		result["orders"] = orders
		result["orders_count"] = len(orders)
	}
	
	productsRows, err := a.DB.DB.Query(`
		SELECT id, external_id, name, price, unit, article, barcode,
		       is_active, updated_at
		FROM products WHERE updated_at > datetime('now', '-1 day')`)
	if err == nil {
		defer productsRows.Close()
		var products []models.Product
		for productsRows.Next() {
			var product models.Product
			productsRows.Scan(&product.ID, &product.ExternalID, &product.Name,
				&product.Price, &product.Unit, &product.Article, &product.Barcode,
				&product.IsActive, &product.UpdatedAt)
			products = append(products, product)
		}
		result["products"] = products
		result["products_count"] = len(products)
	}
	
	return result, nil
}
