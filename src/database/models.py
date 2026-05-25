"""
SQLAlchemy модели для центральной системы OrderManager
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime,
    ForeignKey, Text, Enum, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()


class ManagerStatus(enum.Enum):
    """Статус менеджера"""
    ACTIVE = "ACTIVE"
    BLOCKED = "BLOCKED"
    INACTIVE = "INACTIVE"


class OrderStatus(enum.Enum):
    """Статус заказа"""
    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    DELIVERED = "DELIVERED"
    CANCELED = "CANCELED"


class PaymentStatus(enum.Enum):
    """Статус оплаты"""
    UNPAID = "UNPAID"
    PAID = "PAID"
    PARTIALLY_PAID = "PARTIALLY_PAID"


class PaymentType(enum.Enum):
    """Тип оплаты"""
    CASH = "CASH"
    CARD = "CARD"
    TRANSFER = "TRANSFER"
    MIXED = "MIXED"


class BonusTransactionType(enum.Enum):
    """Тип транзакции бонусов"""
    EARNED = "EARNED"
    SPENT = "SPENT"
    EXPIRED = "EXPIRED"
    ADJUSTED = "ADJUSTED"


class DeliveryEventType(enum.Enum):
    """Тип события доставки"""
    STARTED = "started"
    PAYMENT_RECEIVED = "payment_received"
    DELIVERED = "delivered"


class Category(Base):
    """Категория товаров"""
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, nullable=False, index=True)  # ID из 1С
    name = Column(String(200), nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)  # Родительская категория
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    parent = relationship("Category", remote_side=[id], backref="children")
    products = relationship("Product", back_populates="category_obj")


class Manager(Base):
    """Менеджер (оператор)"""
    __tablename__ = 'managers'

    id = Column(Integer, primary_key=True)
    pin_code = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(20))
    email = Column(String(100))
    status = Column(Enum(ManagerStatus), default=ManagerStatus.ACTIVE, nullable=False)
    last_sync_at = Column(DateTime)
    device_id = Column(String(100))
    device_model = Column(String(100))
    app_version = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    orders = relationship("Order", back_populates="manager")
    sync_logs = relationship("SyncLog", back_populates="manager")

    def __repr__(self):
        return f"<Manager(pin={self.pin_code}, name={self.name})>"


class Client(Base):
    """Клиент"""
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, index=True)  # ID с устройства
    phone = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100))
    bonus_balance = Column(Float, default=0.0, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    total_spent = Column(Float, default=0.0, nullable=False)
    last_order_date = Column(DateTime)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    addresses = relationship("Address", back_populates="client", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="client")
    bonus_transactions = relationship("BonusTransaction", back_populates="client")

    def __repr__(self):
        return f"<Client(phone={self.phone}, name={self.name})>"


class Address(Base):
    """Адрес клиента"""
    __tablename__ = 'addresses'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, index=True)  # ID с устройства
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    address_text = Column(String(500), nullable=False)
    street = Column(String(200))
    house = Column(String(20))
    apartment = Column(String(20))
    latitude = Column(Float)
    longitude = Column(Float)
    is_default = Column(Boolean, default=False, nullable=False)
    label = Column(String(50))  # Дом, Работа, и т.д.
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="addresses")
    orders = relationship("Order", back_populates="address")

    # Indexes
    __table_args__ = (
        Index('idx_address_coords', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f"<Address(client_id={self.client_id}, text={self.address_text[:30]})>"


class Product(Base):
    """Товар"""
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100))  # Старое поле - оставляем для обратной совместимости
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=True)  # Новая связь с таблицей категорий
    price = Column(Float, nullable=False)
    unit = Column(String(20), default='шт')
    image_url = Column(String(500))
    image_path = Column(String(500))  # Локальный путь к картинке
    article = Column(String(50))  # Артикул товара
    barcode = Column(String(50))
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    category_obj = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")
    price_history = relationship("PriceHistory", back_populates="product")

    # Indexes
    __table_args__ = (
        Index('idx_product_name', 'name'),
        Index('idx_product_category', 'category'),
    )

    def __repr__(self):
        return f"<Product(id={self.external_id}, name={self.name})>"


class PriceHistory(Base):
    """История изменения цен"""
    __tablename__ = 'price_history'

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    changed_by = Column(String(100))
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="price_history")

    def __repr__(self):
        return f"<PriceHistory(product_id={self.product_id}, {self.old_price}->{self.new_price})>"


class Order(Base):
    """Заказ"""
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    external_id = Column(String(50), unique=True, nullable=False, index=True)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    manager_id = Column(Integer, ForeignKey('managers.id'), nullable=False)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    address_id = Column(Integer, ForeignKey('addresses.id'))
    address_text = Column(String(500), nullable=False)
    address_latitude = Column(Float)
    address_longitude = Column(Float)
    delivery_date = Column(DateTime, nullable=False)
    delivery_time_slot = Column(String(50))
    status = Column(Enum(OrderStatus), default=OrderStatus.NEW, nullable=False)
    payment_status = Column(Enum(PaymentStatus), default=PaymentStatus.UNPAID, nullable=False)
    payment_type = Column(Enum(PaymentType), default=PaymentType.CASH, nullable=False)
    total_amount = Column(Float, nullable=False)
    bonus_used = Column(Float, default=0.0, nullable=False)
    bonus_earned = Column(Float, default=0.0, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    manager = relationship("Manager", back_populates="orders")
    client = relationship("Client", back_populates="orders")
    address = relationship("Address", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    payment_location = relationship("PaymentLocation", back_populates="order", uselist=False)
    delivery_events = relationship("DeliveryEvent", back_populates="order", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index('idx_order_status', 'status'),
        Index('idx_order_delivery_date', 'delivery_date'),
        Index('idx_order_manager', 'manager_id'),
        Index('idx_order_client', 'client_id'),
    )

    def __repr__(self):
        return f"<Order(number={self.order_number}, status={self.status.value})>"


class OrderItem(Base):
    """Позиция заказа"""
    __tablename__ = 'order_items'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'))
    product_external_id = Column(String(50))  # ID товара с устройства
    product_name = Column(String(200), nullable=False)
    quantity = Column(Float, nullable=False)
    price_at_moment = Column(Float, nullable=False)
    sum = Column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self):
        return f"<OrderItem(order_id={self.order_id}, product={self.product_name})>"


class PaymentLocation(Base):
    """Координаты места оплаты"""
    __tablename__ = 'payment_locations'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), unique=True, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float)
    altitude = Column(Float)
    speed = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    device_model = Column(String(100))
    device_os = Column(String(50))
    app_version = Column(String(20))

    # Relationships
    order = relationship("Order", back_populates="payment_location")

    # Indexes
    __table_args__ = (
        Index('idx_payment_coords', 'latitude', 'longitude'),
    )

    def __repr__(self):
        return f"<PaymentLocation(order_id={self.order_id}, lat={self.latitude}, lon={self.longitude})>"


class DeliveryEvent(Base):
    """События доставки с GPS-координатами"""
    __tablename__ = 'delivery_events'

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey('orders.id'), nullable=False)
    event_type = Column(Enum(DeliveryEventType), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float)
    timestamp = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="delivery_events")

    # Indexes
    __table_args__ = (
        Index('idx_delivery_event_order', 'order_id'),
        Index('idx_delivery_event_type', 'event_type'),
        Index('idx_delivery_event_timestamp', 'timestamp'),
    )

    def __repr__(self):
        return f"<DeliveryEvent(order_id={self.order_id}, type={self.event_type.value})>"


class BonusTransaction(Base):
    """Транзакция бонусов"""
    __tablename__ = 'bonus_transactions'

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'), nullable=False)
    order_id = Column(Integer, ForeignKey('orders.id'))
    type = Column(Enum(BonusTransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    client = relationship("Client", back_populates="bonus_transactions")

    # Indexes
    __table_args__ = (
        Index('idx_bonus_client', 'client_id'),
        Index('idx_bonus_created', 'created_at'),
    )

    def __repr__(self):
        return f"<BonusTransaction(client_id={self.client_id}, type={self.type.value}, amount={self.amount})>"


class SyncLog(Base):
    """Лог синхронизации"""
    __tablename__ = 'sync_logs'

    id = Column(Integer, primary_key=True)
    manager_id = Column(Integer, ForeignKey('managers.id'), nullable=False)
    sync_type = Column(String(50), nullable=False)  # upload, download
    file_name = Column(String(200))
    status = Column(String(50), nullable=False)  # success, error, partial
    records_processed = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Relationships
    manager = relationship("Manager", back_populates="sync_logs")

    # Indexes
    __table_args__ = (
        Index('idx_sync_manager', 'manager_id'),
        Index('idx_sync_started', 'started_at'),
    )

    def __repr__(self):
        return f"<SyncLog(manager_id={self.manager_id}, type={self.sync_type}, status={self.status})>"


class Settings(Base):
    """Настройки системы"""
    __tablename__ = 'settings'

    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text)
    description = Column(String(500))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Settings(key={self.key})>"
