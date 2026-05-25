package models

import (
	"time"
)

// ManagerStatus - статус менеджера
type ManagerStatus string

const (
	ManagerStatusActive   ManagerStatus = "ACTIVE"
	ManagerStatusBlocked  ManagerStatus = "BLOCKED"
	ManagerStatusInactive ManagerStatus = "INACTIVE"
)

// OrderStatus - статус заказа
type OrderStatus string

const (
	OrderStatusNew        OrderStatus = "NEW"
	OrderStatusInProgress OrderStatus = "IN_PROGRESS"
	OrderStatusDelivered  OrderStatus = "DELIVERED"
	OrderStatusCanceled   OrderStatus = "CANCELED"
)

// PaymentStatus - статус оплаты
type PaymentStatus string

const (
	PaymentStatusUnpaid       PaymentStatus = "UNPAID"
	PaymentStatusPaid         PaymentStatus = "PAID"
	PaymentStatusPartiallyPaid PaymentStatus = "PARTIALLY_PAID"
)

// PaymentType - тип оплаты
type PaymentType string

const (
	PaymentTypeCash     PaymentType = "CASH"
	PaymentTypeCard     PaymentType = "CARD"
	PaymentTypeTransfer PaymentType = "TRANSFER"
	PaymentTypeMixed    PaymentType = "MIXED"
)

// BonusTransactionType - тип транзакции бонусов
type BonusTransactionType string

const (
	BonusTransactionTypeEarned    BonusTransactionType = "EARNED"
	BonusTransactionTypeSpent     BonusTransactionType = "SPENT"
	BonusTransactionTypeExpired   BonusTransactionType = "EXPIRED"
	BonusTransactionTypeAdjusted  BonusTransactionType = "ADJUSTED"
)

// DeliveryEventType - тип события доставки
type DeliveryEventType string

const (
	DeliveryEventTypeStarted          DeliveryEventType = "started"
	DeliveryEventTypePaymentReceived  DeliveryEventType = "payment_received"
	DeliveryEventTypeDelivered        DeliveryEventType = "delivered"
)

// Category - категория товаров
type Category struct {
	ID        int64     `json:"id"`
	ExternalID string    `json:"external_id"`
	Name      string    `json:"name"`
	ParentID  *int64    `json:"parent_id,omitempty"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
	
	// Relationships
	Parent   *Category   `json:"parent,omitempty" gorm:"foreignKey:ParentID"`
	Children []Category  `json:"children,omitempty" gorm:"foreignKey:ParentID"`
	Products []Product   `json:"products,omitempty" gorm:"foreignKey:CategoryID"`
}

// Manager - менеджер (оператор)
type Manager struct {
	ID           int64         `json:"id"`
	PINCode      string        `json:"pin_code"`
	Name         string        `json:"name"`
	Phone        string        `json:"phone"`
	Email        string        `json:"email"`
	Status       ManagerStatus `json:"status"`
	LastSyncAt   *time.Time    `json:"last_sync_at,omitempty"`
	DeviceID     string        `json:"device_id"`
	DeviceModel  string        `json:"device_model"`
	AppVersion   string        `json:"app_version"`
	CreatedAt    time.Time     `json:"created_at"`
	UpdatedAt    time.Time     `json:"updated_at"`
	
	// Relationships
	Orders    []Order    `json:"orders,omitempty" gorm:"foreignKey:ManagerID"`
	SyncLogs  []SyncLog  `json:"sync_logs,omitempty" gorm:"foreignKey:ManagerID"`
}

// Client - клиент
type Client struct {
	ID            int64      `json:"id"`
	ExternalID    string     `json:"external_id"`
	Phone         string     `json:"phone"`
	Name          string     `json:"name"`
	BonusBalance  float64    `json:"bonus_balance"`
	TotalOrders   int64      `json:"total_orders"`
	TotalSpent    float64    `json:"total_spent"`
	LastOrderDate *time.Time `json:"last_order_date,omitempty"`
	Notes         string     `json:"notes"`
	CreatedAt     time.Time  `json:"created_at"`
	UpdatedAt     time.Time  `json:"updated_at"`
	
	// Relationships
	Addresses         []Address         `json:"addresses,omitempty" gorm:"foreignKey:ClientID"`
	Orders            []Order           `json:"orders,omitempty" gorm:"foreignKey:ClientID"`
	BonusTransactions []BonusTransaction `json:"bonus_transactions,omitempty" gorm:"foreignKey:ClientID"`
}

// Address - адрес клиента
type Address struct {
	ID          int64      `json:"id"`
	ExternalID  string     `json:"external_id"`
	ClientID    int64      `json:"client_id"`
	AddressText string     `json:"address_text"`
	Street      string     `json:"street"`
	House       string     `json:"house"`
	Apartment   string     `json:"apartment"`
	Latitude    *float64   `json:"latitude,omitempty"`
	Longitude   *float64   `json:"longitude,omitempty"`
	IsDefault   bool       `json:"is_default"`
	Label       string     `json:"label"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	
	// Relationships
	Client  Client  `json:"client,omitempty" gorm:"foreignKey:ClientID"`
	Orders  []Order `json:"orders,omitempty" gorm:"foreignKey:AddressID"`
}

// Product - товар
type Product struct {
	ID          int64      `json:"id"`
	ExternalID  string     `json:"external_id"`
	Name        string     `json:"name"`
	Category    string     `json:"category"` // Старое поле для обратной совместимости
	CategoryID  *int64     `json:"category_id,omitempty"`
	Price       float64    `json:"price"`
	Unit        string     `json:"unit"`
	ImageURL    string     `json:"image_url"`
	ImagePath   string     `json:"image_path"`
	Article     string     `json:"article"`
	Barcode     string     `json:"barcode"`
	Description string     `json:"description"`
	IsActive    bool       `json:"is_active"`
	CreatedAt   time.Time  `json:"created_at"`
	UpdatedAt   time.Time  `json:"updated_at"`
	
	// Relationships
	CategoryObj *Category      `json:"category_obj,omitempty" gorm:"foreignKey:CategoryID"`
	OrderItems  []OrderItem    `json:"order_items,omitempty" gorm:"foreignKey:ProductID"`
	PriceHistory []PriceHistory `json:"price_history,omitempty" gorm:"foreignKey:ProductID"`
}

// PriceHistory - история изменения цен
type PriceHistory struct {
	ID         int64      `json:"id"`
	ProductID  int64      `json:"product_id"`
	OldPrice   float64    `json:"old_price"`
	NewPrice   float64    `json:"new_price"`
	ChangedBy  string     `json:"changed_by"`
	ChangedAt  time.Time  `json:"changed_at"`
	
	// Relationships
	Product Product `json:"product,omitempty" gorm:"foreignKey:ProductID"`
}

// Order - заказ
type Order struct {
	ID               int64          `json:"id"`
	ExternalID       string         `json:"external_id"`
	OrderNumber      string         `json:"order_number"`
	ManagerID        int64          `json:"manager_id"`
	ClientID         int64          `json:"client_id"`
	AddressID        *int64         `json:"address_id,omitempty"`
	AddressText      string         `json:"address_text"`
	AddressLatitude  *float64       `json:"address_latitude,omitempty"`
	AddressLongitude *float64       `json:"address_longitude,omitempty"`
	DeliveryDate     time.Time      `json:"delivery_date"`
	DeliveryTimeSlot string         `json:"delivery_time_slot"`
	Status           OrderStatus    `json:"status"`
	PaymentStatus    PaymentStatus  `json:"payment_status"`
	PaymentType      PaymentType    `json:"payment_type"`
	TotalAmount      float64        `json:"total_amount"`
	BonusUsed        float64        `json:"bonus_used"`
	BonusEarned      float64        `json:"bonus_earned"`
	Comment          string         `json:"comment"`
	CreatedAt        time.Time      `json:"created_at"`
	UpdatedAt        time.Time      `json:"updated_at"`
	
	// Relationships
	Manager        *Manager         `json:"manager,omitempty" gorm:"foreignKey:ManagerID"`
	Client         *Client          `json:"client,omitempty" gorm:"foreignKey:ClientID"`
	Address        *Address         `json:"address,omitempty" gorm:"foreignKey:AddressID"`
	Items          []OrderItem      `json:"items,omitempty" gorm:"foreignKey:OrderID"`
	PaymentLocation *PaymentLocation `json:"payment_location,omitempty" gorm:"foreignKey:OrderID"`
	DeliveryEvents []DeliveryEvent  `json:"delivery_events,omitempty" gorm:"foreignKey:OrderID"`
}

// OrderItem - позиция заказа
type OrderItem struct {
	ID              int64    `json:"id"`
	OrderID         int64    `json:"order_id"`
	ProductID       *int64   `json:"product_id,omitempty"`
	ProductExternalID string `json:"product_external_id"`
	ProductName     string   `json:"product_name"`
	Quantity        float64  `json:"quantity"`
	PriceAtMoment   float64  `json:"price_at_moment"`
	Sum             float64  `json:"sum"`
	
	// Relationships
	Order   Order   `json:"order,omitempty" gorm:"foreignKey:OrderID"`
	Product *Product `json:"product,omitempty" gorm:"foreignKey:ProductID"`
}

// PaymentLocation - координаты места оплаты
type PaymentLocation struct {
	ID         int64     `json:"id"`
	OrderID    int64     `json:"order_id"`
	Latitude   float64   `json:"latitude"`
	Longitude  float64   `json:"longitude"`
	Accuracy   *float64  `json:"accuracy,omitempty"`
	Altitude   *float64  `json:"altitude,omitempty"`
	Speed      *float64  `json:"speed,omitempty"`
	Timestamp  time.Time `json:"timestamp"`
	DeviceModel string   `json:"device_model"`
	DeviceOS   string    `json:"device_os"`
	AppVersion string    `json:"app_version"`
	
	// Relationships
	Order Order `json:"order,omitempty" gorm:"foreignKey:OrderID"`
}

// DeliveryEvent - событие доставки с GPS-координатами
type DeliveryEvent struct {
	ID        int64             `json:"id"`
	OrderID   int64             `json:"order_id"`
	EventType DeliveryEventType `json:"event_type"`
	Latitude  float64           `json:"latitude"`
	Longitude float64           `json:"longitude"`
	Accuracy  *float64          `json:"accuracy,omitempty"`
	Timestamp time.Time         `json:"timestamp"`
	CreatedAt time.Time         `json:"created_at"`
	
	// Relationships
	Order Order `json:"order,omitempty" gorm:"foreignKey:OrderID"`
}

// BonusTransaction - транзакция бонусов
type BonusTransaction struct {
	ID           int64              `json:"id"`
	ClientID     int64              `json:"client_id"`
	OrderID      *int64             `json:"order_id,omitempty"`
	Type         BonusTransactionType `json:"type"`
	Amount       float64            `json:"amount"`
	BalanceBefore float64           `json:"balance_before"`
	BalanceAfter float64            `json:"balance_after"`
	Description  string             `json:"description"`
	CreatedAt    time.Time          `json:"created_at"`
	
	// Relationships
	Client Client `json:"client,omitempty" gorm:"foreignKey:ClientID"`
}

// SyncLog - лог синхронизации
type SyncLog struct {
	ID              int64      `json:"id"`
	ManagerID       int64      `json:"manager_id"`
	SyncType        string     `json:"sync_type"`
	FileName        string     `json:"file_name"`
	Status          string     `json:"status"`
	RecordsProcessed int64     `json:"records_processed"`
	RecordsFailed   int64      `json:"records_failed"`
	ErrorMessage    string     `json:"error_message"`
	StartedAt       time.Time  `json:"started_at"`
	CompletedAt     *time.Time `json:"completed_at,omitempty"`
	DurationSeconds *float64   `json:"duration_seconds,omitempty"`
	
	// Relationships
	Manager Manager `json:"manager,omitempty" gorm:"foreignKey:ManagerID"`
}

// Settings - настройки системы
type Settings struct {
	ID          int64     `json:"id"`
	Key         string    `json:"key"`
	Value       string    `json:"value"`
	Description string    `json:"description"`
	UpdatedAt   time.Time `json:"updated_at"`
}
