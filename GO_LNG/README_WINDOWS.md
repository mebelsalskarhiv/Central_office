# OrderManager Central Office - Инструкция для Windows

## Быстрый старт

### Вариант 1: Автоматическая установка (рекомендуется)

1. **Откройте PowerShell от имени администратора**
   - Нажмите `Win + X` → выберите "Windows PowerShell (Admin)"
   - Или найдите PowerShell в меню Пуск, нажмите правой кнопкой → "Запустить от имени администратора"

2. **Перейдите в папку проекта**
   ```powershell
   cd E:\Central_office\GO_LNG
   ```

3. **Запустите скрипт установки**
   ```powershell
   .\setup_windows.ps1
   ```

4. **Если требуется установка GCC (MinGW)**
   
   Скрипт попытается установить автоматически. Если не получилось:
   
   **Способ A: Через winget**
   ```powershell
   winget install MSYS2.MSYS2
   ```
   
   **Способ B: Вручную**
   - Скачайте с https://www.mingw-w64.org/downloads/
   - Или используйте https://winlibs.com/
   - Распакуйте и добавьте `bin` в PATH

5. **Запустите приложение**
   ```powershell
   .\central-office.exe --init-db
   ```

### Вариант 2: Ручная установка

#### Шаг 1: Установите Go
- Скачайте с https://go.dev/dl/
- Запустите установщик
- Перезапустите терминал

#### Шаг 2: Установите GCC (MinGW-w64)
- Скачайте с https://winlibs.com/ (версия без LLVM, standalone)
- Распакуйте в `C:\mingw64`
- Добавьте `C:\mingw64\bin` в переменную окружения PATH

#### Шаг 3: Установите Wails (опционально, для разработки)
```powershell
go install github.com/wailsapp/wails/v2/cmd/wails@latest
```

#### Шаг 4: Соберите проект
```powershell
cd E:\Central_office\GO_LNG
go mod tidy
CGO_ENABLED=1 go build -o central-office.exe .
```

#### Шаг 5: Запустите
```powershell
.\central-office.exe --init-db
```

## Режимы работы

### Обычный запуск
```powershell
.\central-office.exe --init-db
```

### Разработка с live-reload (требуется Wails)
```powershell
wails dev
```

### Сборка релизной версии
```powershell
wails build
```
Бинарник появится в папке `build/bin/`

## Структура проекта

```
GO_LNG/
├── main.go                 # Точка входа
├── go.mod                  # Зависимости Go
├── wails.json             # Конфигурация Wails
├── setup_windows.ps1      # Скрипт установки
├── frontend/dist/         # Веб-интерфейс
│   └── index.html        # Главный HTML файл
├── internal/
│   ├── database/         # Работа с БД
│   ├── models/           # Модели данных
│   ├── handlers/         # API обработчики
│   └── sync/             # Синхронизация
└── data/                 # Файлы БД и бэкапы
```

## Возможности приложения

✅ Просмотр заказов, товаров, клиентов, менеджеров  
✅ Детали заказа (модальное окно)  
✅ Редактирование товаров/клиентов/менеджеров  
✅ Отчеты и аналитика  
✅ Карта доставок  
✅ Синхронизация с мобильными устройствами  
✅ Экспорт данных в Excel/CSV  
✅ Резервное копирование БД  
✅ Импорт из 1С (CommerceML)  

## Требования

- Windows 10/11 (64-bit)
- Go 1.21+ (для сборки)
- GCC/MinGW-w64 (для CGO, работа с SQLite)
- 100 MB свободного места

## Решение проблем

### Ошибка: "gcc not found"
Установите MinGW-w64 и добавьте в PATH:
```powershell
$env:Path = "C:\mingw64\bin;" + $env:Path
```

### Ошибка: "port already in use"
Измените порт в настройках или закройте другое приложение

### Ошибка: "database locked"
Закройте все экземпляры приложения и удалите файл `.db.lock`

### Приложение не запускается
Запустите от имени администратора или проверьте антивирус

## Контакты

Поддержка: support@ordermanager.com  
Документация: https://ordermanager.com/docs
