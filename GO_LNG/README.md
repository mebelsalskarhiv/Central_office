# OrderManager Central Office (Go + Wails)

Миграция приложения с Python/PyQt6 на Go + Wails.

## Структура проекта

```
GO_LNG/
├── main.go                          # Точка входа приложения
├── go.mod                           # Модуль Go
├── internal/
│   ├── database/
│   │   └── database.go              # Работа с SQLite
│   ├── models/
│   │   └── models.go                # Модели данных
│   ├── sync/
│   │   └── commerceml_parser.go     # Парсер CommerceML (1С)
│   └── handlers/
│       └── app.go                   # Обработчики для Wails
└── frontend/
    └── dist/
        └── index.html               # Веб-интерфейс
```

## Требования

- Go 1.19+
- Node.js (для сборки фронтенда, опционально)
- CGO (для работы с SQLite)

## Установка зависимостей

```bash
cd GO_LNG
go mod tidy
```

## Запуск в режиме разработки

```bash
# Инициализация БД и запуск
go run . --init-db

# Или с указанием пути к БД
go run . --db-path ./data/central.db --init-db

# Пересоздание БД
go run . --recreate-db
```

## Сборка релизной версии

```bash
# Установить Wails (если не установлен)
go install github.com/wailsapp/wails/v2/cmd/wails@latest

# Сборка
wails build

# Сборка для Windows
wails build -platform windows/amd64

# Сборка для Linux
wails build -platform linux/amd64

# Сборка для macOS
wails build -platform darwin/universal
```

## API методы (доступны из JavaScript)

### Заказы
- `window.go.main.App.GetOrders()` - получить список заказов

### Товары
- `window.go.main.App.GetProducts()` - получить список товаров
- `window.go.main.App.ImportFrom1C(importPath, offersPath)` - импорт из 1С

### Клиенты
- `window.go.main.App.GetClients()` - получить список клиентов

### Менеджеры
- `window.go.main.App.GetManagers()` - получить список менеджеров

### Настройки
- `window.go.main.App.GetSettings()` - получить все настройки
- `window.go.main.App.GetSetting(key)` - получить одну настройку
- `window.go.main.App.UpdateSetting(key, value)` - обновить настройку

## Отличия от PyQt6 версии

1. **GUI**: Вместо PyQt6 используется веб-интерфейс через Wails
2. **База данных**: Прямые SQL запросы вместо SQLAlchemy ORM
3. **Асинхронность**: Все вызовы к Go из JS асинхронные (Promise-based)
4. **CommerceML**: Упрощенный XML парсер без внешних зависимостей

## Преимущества новой архитектуры

- ✅ Кроссплатформенность (Windows, macOS, Linux)
- ✅ Меньший размер исполняемого файла
- ✅ Нет зависимости от Python
- ✅ Лучшая производительность
- ✅ Современный веб-интерфейс
- ✅ Простая сборка под разные платформы

## TODO

- [ ] Детали заказа (модальное окно)
- [ ] Редактирование товаров/клиентов/менеджеров
- [ ] Полноценные отчеты и аналитика
- [ ] Карта доставок
- [ ] Синхронизация с мобильными устройствами
- [ ] Экспорт данных в Excel/CSV
- [ ] Резервное копирование БД
