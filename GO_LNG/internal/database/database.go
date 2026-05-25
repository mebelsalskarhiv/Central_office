package database

import (
	"database/sql"
	"fmt"
	"log"
	"os"
	"path/filepath"
	"sync"
	"time"

	_ "github.com/mattn/go-sqlite3"
)

// Database - менеджер базы данных
type Database struct {
	DBPath string
	DB     *sql.DB
	mu     sync.Mutex
}

// NewDatabase - создание нового подключения к БД
func NewDatabase(dbPath string) (*Database, error) {
	if dbPath == "" {
		// Путь по умолчанию
		execPath, err := os.Executable()
		if err != nil {
			return nil, fmt.Errorf("error getting executable path: %w", err)
		}
		baseDir := filepath.Dir(execPath)
		dataDir := filepath.Join(baseDir, "data")
		if err := os.MkdirAll(dataDir, 0755); err != nil {
			return nil, fmt.Errorf("error creating data directory: %w", err)
		}
		dbPath = filepath.Join(dataDir, "central.db")
	}

	db := &Database{
		DBPath: dbPath,
	}

	return db, nil
}

// Connect - подключение к базе данных
func (d *Database) Connect() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	connectionString := fmt.Sprintf("file:%s?_foreign_keys=on", d.DBPath)

	db, err := sql.Open("sqlite3", connectionString)
	if err != nil {
		return fmt.Errorf("error opening database: %w", err)
	}

	// Настройки для SQLite
	db.SetMaxOpenConns(1) // SQLite не поддерживает множественные записи
	db.SetMaxIdleConns(1)
	db.SetConnMaxLifetime(time.Hour)

	// Тест подключения
	if err := db.Ping(); err != nil {
		return fmt.Errorf("error pinging database: %w", err)
	}

	d.DB = db
	log.Printf("Connected to database: %s", d.DBPath)

	return nil
}

// CreateTables - создание всех таблиц
func (d *Database) CreateTables() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.DB == nil {
		return fmt.Errorf("database not connected")
	}

	schemas := []string{
		`CREATE TABLE IF NOT EXISTS categories (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			external_id TEXT UNIQUE NOT NULL,
			name TEXT NOT NULL,
			parent_id INTEGER,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (parent_id) REFERENCES categories(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_categories_external_id ON categories(external_id)`,
		
		`CREATE TABLE IF NOT EXISTS managers (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			pin_code TEXT UNIQUE NOT NULL,
			name TEXT NOT NULL,
			phone TEXT,
			email TEXT,
			status TEXT NOT NULL DEFAULT 'ACTIVE',
			last_sync_at DATETIME,
			device_id TEXT,
			device_model TEXT,
			app_version TEXT,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE INDEX IF NOT EXISTS idx_managers_pin_code ON managers(pin_code)`,
		
		`CREATE TABLE IF NOT EXISTS clients (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			external_id TEXT UNIQUE,
			phone TEXT UNIQUE NOT NULL,
			name TEXT,
			bonus_balance REAL NOT NULL DEFAULT 0.0,
			total_orders INTEGER NOT NULL DEFAULT 0,
			total_spent REAL NOT NULL DEFAULT 0.0,
			last_order_date DATETIME,
			notes TEXT,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE INDEX IF NOT EXISTS idx_clients_external_id ON clients(external_id)`,
		`CREATE INDEX IF NOT EXISTS idx_clients_phone ON clients(phone)`,
		
		`CREATE TABLE IF NOT EXISTS addresses (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			external_id TEXT UNIQUE,
			client_id INTEGER NOT NULL,
			address_text TEXT NOT NULL,
			street TEXT,
			house TEXT,
			apartment TEXT,
			latitude REAL,
			longitude REAL,
			is_default BOOLEAN NOT NULL DEFAULT 0,
			label TEXT,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (client_id) REFERENCES clients(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_addresses_external_id ON addresses(external_id)`,
		`CREATE INDEX IF NOT EXISTS idx_addresses_client_id ON addresses(client_id)`,
		`CREATE INDEX IF NOT EXISTS idx_address_coords ON addresses(latitude, longitude)`,
		
		`CREATE TABLE IF NOT EXISTS products (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			external_id TEXT UNIQUE NOT NULL,
			name TEXT NOT NULL,
			category TEXT,
			category_id INTEGER,
			price REAL NOT NULL,
			unit TEXT DEFAULT 'шт',
			image_url TEXT,
			image_path TEXT,
			article TEXT,
			barcode TEXT,
			description TEXT,
			is_active BOOLEAN NOT NULL DEFAULT 1,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (category_id) REFERENCES categories(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_products_external_id ON products(external_id)`,
		`CREATE INDEX IF NOT EXISTS idx_product_name ON products(name)`,
		`CREATE INDEX IF NOT EXISTS idx_product_category ON products(category)`,
		
		`CREATE TABLE IF NOT EXISTS price_history (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			product_id INTEGER NOT NULL,
			old_price REAL NOT NULL,
			new_price REAL NOT NULL,
			changed_by TEXT,
			changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (product_id) REFERENCES products(id)
		)`,
		
		`CREATE TABLE IF NOT EXISTS orders (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			external_id TEXT UNIQUE NOT NULL,
			order_number TEXT UNIQUE NOT NULL,
			manager_id INTEGER NOT NULL,
			client_id INTEGER NOT NULL,
			address_id INTEGER,
			address_text TEXT NOT NULL,
			address_latitude REAL,
			address_longitude REAL,
			delivery_date DATETIME NOT NULL,
			delivery_time_slot TEXT,
			status TEXT NOT NULL DEFAULT 'NEW',
			payment_status TEXT NOT NULL DEFAULT 'UNPAID',
			payment_type TEXT NOT NULL DEFAULT 'CASH',
			total_amount REAL NOT NULL,
			bonus_used REAL NOT NULL DEFAULT 0.0,
			bonus_earned REAL NOT NULL DEFAULT 0.0,
			comment TEXT,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (manager_id) REFERENCES managers(id),
			FOREIGN KEY (client_id) REFERENCES clients(id),
			FOREIGN KEY (address_id) REFERENCES addresses(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_orders_external_id ON orders(external_id)`,
		`CREATE INDEX IF NOT EXISTS idx_orders_order_number ON orders(order_number)`,
		`CREATE INDEX IF NOT EXISTS idx_order_status ON orders(status)`,
		`CREATE INDEX IF NOT EXISTS idx_order_delivery_date ON orders(delivery_date)`,
		`CREATE INDEX IF NOT EXISTS idx_order_manager ON orders(manager_id)`,
		`CREATE INDEX IF NOT EXISTS idx_order_client ON orders(client_id)`,
		
		`CREATE TABLE IF NOT EXISTS order_items (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			order_id INTEGER NOT NULL,
			product_id INTEGER,
			product_external_id TEXT,
			product_name TEXT NOT NULL,
			quantity REAL NOT NULL,
			price_at_moment REAL NOT NULL,
			sum REAL NOT NULL,
			FOREIGN KEY (order_id) REFERENCES orders(id),
			FOREIGN KEY (product_id) REFERENCES products(id)
		)`,
		
		`CREATE TABLE IF NOT EXISTS payment_locations (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			order_id INTEGER UNIQUE NOT NULL,
			latitude REAL NOT NULL,
			longitude REAL NOT NULL,
			accuracy REAL,
			altitude REAL,
			speed REAL,
			timestamp DATETIME NOT NULL,
			device_model TEXT,
			device_os TEXT,
			app_version TEXT,
			FOREIGN KEY (order_id) REFERENCES orders(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_payment_coords ON payment_locations(latitude, longitude)`,
		
		`CREATE TABLE IF NOT EXISTS delivery_events (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			order_id INTEGER NOT NULL,
			event_type TEXT NOT NULL,
			latitude REAL NOT NULL,
			longitude REAL NOT NULL,
			accuracy REAL,
			timestamp DATETIME NOT NULL,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (order_id) REFERENCES orders(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_delivery_event_order ON delivery_events(order_id)`,
		`CREATE INDEX IF NOT EXISTS idx_delivery_event_type ON delivery_events(event_type)`,
		`CREATE INDEX IF NOT EXISTS idx_delivery_event_timestamp ON delivery_events(timestamp)`,
		
		`CREATE TABLE IF NOT EXISTS bonus_transactions (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			client_id INTEGER NOT NULL,
			order_id INTEGER,
			type TEXT NOT NULL,
			amount REAL NOT NULL,
			balance_before REAL NOT NULL,
			balance_after REAL NOT NULL,
			description TEXT,
			created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			FOREIGN KEY (client_id) REFERENCES clients(id),
			FOREIGN KEY (order_id) REFERENCES orders(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_bonus_client ON bonus_transactions(client_id)`,
		`CREATE INDEX IF NOT EXISTS idx_bonus_created ON bonus_transactions(created_at)`,
		
		`CREATE TABLE IF NOT EXISTS sync_logs (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			manager_id INTEGER NOT NULL,
			sync_type TEXT NOT NULL,
			file_name TEXT,
			status TEXT NOT NULL,
			records_processed INTEGER DEFAULT 0,
			records_failed INTEGER DEFAULT 0,
			error_message TEXT,
			started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
			completed_at DATETIME,
			duration_seconds REAL,
			FOREIGN KEY (manager_id) REFERENCES managers(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_sync_manager ON sync_logs(manager_id)`,
		`CREATE INDEX IF NOT EXISTS idx_sync_started ON sync_logs(started_at)`,
		
		`CREATE TABLE IF NOT EXISTS settings (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			key TEXT UNIQUE NOT NULL,
			value TEXT,
			description TEXT,
			updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
		)`,
		`CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)`,
	}

	for _, schema := range schemas {
		if _, err := d.DB.Exec(schema); err != nil {
			return fmt.Errorf("error executing schema: %w", err)
		}
	}

	log.Println("Database tables created successfully")
	return nil
}

// DropTables - удаление всех таблиц (осторожно!)
func (d *Database) DropTables() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.DB == nil {
		return fmt.Errorf("database not connected")
	}

	tables := []string{
		"settings", "sync_logs", "bonus_transactions", "delivery_events",
		"payment_locations", "order_items", "orders", "price_history",
		"products", "addresses", "clients", "managers", "categories",
	}

	for _, table := range tables {
		if _, err := d.DB.Exec(fmt.Sprintf("DROP TABLE IF EXISTS %s", table)); err != nil {
			return fmt.Errorf("error dropping table %s: %w", table, err)
		}
	}

	log.Println("Database tables dropped")
	return nil
}

// Close - закрытие подключения
func (d *Database) Close() error {
	d.mu.Lock()
	defer d.mu.Unlock()

	if d.DB != nil {
		if err := d.DB.Close(); err != nil {
			return fmt.Errorf("error closing database: %w", err)
		}
		log.Println("Database connection closed")
	}

	return nil
}

// InitDatabase - инициализация базы данных
func InitDatabase(dbPath string, recreate bool) (*Database, error) {
	db, err := NewDatabase(dbPath)
	if err != nil {
		return nil, err
	}

	if err := db.Connect(); err != nil {
		return nil, err
	}

	if recreate {
		log.Println("Recreating database tables...")
		if err := db.DropTables(); err != nil {
			db.Close()
			return nil, err
		}
	}

	if err := db.CreateTables(); err != nil {
		db.Close()
		return nil, err
	}

	// Создаем начальные настройки
	if err := db.createDefaultSettings(); err != nil {
		log.Printf("Error creating default settings: %v", err)
	}

	return db, nil
}

// createDefaultSettings - создание настроек по умолчанию
func (d *Database) createDefaultSettings() error {
	defaultSettings := []struct {
		Key         string
		Value       string
		Description string
	}{
		{"bonus_enabled", "true", "Включена ли бонусная система"},
		{"bonus_earn_percentage", "5.0", "Процент начисления бонусов"},
		{"bonus_min_order_amount", "500.0", "Минимальная сумма заказа для бонусов"},
		{"bonus_max_per_order", "1000.0", "Максимум бонусов за заказ"},
		{"bonus_expiry_days", "365", "Срок действия бонусов (дни)"},
		{"delivery_min_amount", "300.0", "Минимальная сумма заказа"},
		{"sync_interval_minutes", "10", "Интервал синхронизации (минуты)"},
		{"keep_orders_days", "1", "Сколько дней хранить заказы на устройстве"},
		{"auto_cleanup", "true", "Автоматическая очистка старых данных"},
	}

	for _, setting := range defaultSettings {
		_, err := d.DB.Exec(
			"INSERT OR IGNORE INTO settings (key, value, description, updated_at) VALUES (?, ?, ?, ?)",
			setting.Key, setting.Value, setting.Description, time.Now(),
		)
		if err != nil {
			return err
		}
	}

	log.Println("Default settings created")
	return nil
}

// GetSetting - получение настройки
func (d *Database) GetSetting(key string) (string, error) {
	var value string
	err := d.DB.QueryRow("SELECT value FROM settings WHERE key = ?", key).Scan(&value)
	if err != nil {
		return "", err
	}
	return value, nil
}

// SetSetting - установка настройки
func (d *Database) SetSetting(key, value string) error {
	_, err := d.DB.Exec(
		"INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
		key, value, time.Now(),
	)
	return err
}
