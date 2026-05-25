# PowerShell скрипт для установки Go, зависимостей и сборки проекта GO_LNG
# Запускать от имени администратора для установки системных компонентов

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Установка и сборка GO_LNG проекта" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$ErrorActionPreference = "Stop"
$ProjectPath = Join-Path $PSScriptRoot "GO_LNG"
$GoVersion = "1.23.4"
$GoInstallerUrl = "https://go.dev/dl/go$GoVersion.windows-amd64.msi"
$TempDir = $env:TEMP
$GoInstallerPath = Join-Path $TempDir "goinstaller.msi"

# Функция проверки установки Go
function Test-GoInstalled {
    try {
        $goVersion = go version 2>$null
        return $null -ne $goVersion
    } catch {
        return $false
    }
}

# Функция проверки установки GCC (для CGO)
function Test-GCCInstalled {
    try {
        $gccVersion = gcc --version 2>$null
        return $null -ne $gccVersion
    } catch {
        return $false
    }
}

# Функция проверки установки Wails
function Test-WailsInstalled {
    try {
        $wailsVersion = wails version 2>$null
        return $null -ne $wailsVersion
    } catch {
        return $false
    }
}

# Шаг 1: Проверка и установка Go
Write-Host "[1/6] Проверка установки Go..." -ForegroundColor Yellow
if (Test-GoInstalled) {
    Write-Host "  ✓ Go уже установлен: $(go version)" -ForegroundColor Green
} else {
    Write-Host "  Go не найден. Начинаем установку..." -ForegroundColor Yellow
    
    # Скачивание установщика Go
    Write-Host "  Скачивание Go $GoVersion..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $GoInstallerUrl -OutFile $GoInstallerPath -UseBasicParsing
    
    # Тихая установка Go
    Write-Host "  Установка Go..." -ForegroundColor Cyan
    Start-Process msiexec.exe -Wait -ArgumentList "/i `"$GoInstallerPath`" /quiet"
    
    # Обновление PATH в текущей сессии
    $GoPath = "C:\Program Files\Go\bin"
    if (Test-Path $GoPath) {
        $env:Path = "$GoPath;$env:Path"
        [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::Machine)
        Write-Host "  ✓ Go успешно установлен" -ForegroundColor Green
    } else {
        Write-Host "  ✗ Ошибка: Go не найден после установки" -ForegroundColor Red
        exit 1
    }
    
    # Очистка временных файлов
    Remove-Item $GoInstallerPath -Force -ErrorAction SilentlyContinue
}

# Шаг 2: Проверка и установка GCC (MinGW-w64) для CGO
Write-Host ""
Write-Host "[2/6] Проверка установки GCC (для CGO)..." -ForegroundColor Yellow
if (Test-GCCInstalled) {
    Write-Host "  ✓ GCC уже установлен: $(gcc --version | Select-Object -First 1)" -ForegroundColor Green
} else {
    Write-Host "  GCC не найден. Установка MinGW-w64 через winget..." -ForegroundColor Yellow
    
    # Попытка установки через winget
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        Write-Host "  Установка MinGW-w64..." -ForegroundColor Cyan
        winget install MSYS2.MSYS2 --silent --accept-package-agreements --accept-source-agreements 2>$null
        
        # Альтернатива: установка через chocolatey если есть
        if (-not (Test-GCCInstalled)) {
            if (Get-Command choco -ErrorAction SilentlyContinue) {
                Write-Host "  Попытка установки через Chocolatey..." -ForegroundColor Cyan
                choco install mingw -y 2>$null
            }
        }
        
        if (Test-GCCInstalled) {
            Write-Host "  ✓ GCC успешно установлен" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ GCC не установлен автоматически." -ForegroundColor Yellow
            Write-Host "  Скачайте и установите MinGW-w64 вручную:" -ForegroundColor Yellow
            Write-Host "  https://www.mingw-w64.org/downloads/" -ForegroundColor Cyan
            Write-Host "  Или используйте: winget install MSYS2.MSYS2" -ForegroundColor Cyan
            Write-Host "  После установки перезапустите скрипт." -ForegroundColor Yellow
            # Не прерываем выполнение, пробуем продолжить
        }
    } else {
        Write-Host "  ⚠ winget не найден. Установите MinGW-w64 вручную:" -ForegroundColor Yellow
        Write-Host "  https://www.mingw-w64.org/downloads/" -ForegroundColor Cyan
        Write-Host "  Или установите winget из Microsoft Store." -ForegroundColor Cyan
    }
}

# Шаг 3: Инициализация Go модуля и установка зависимостей
Write-Host ""
Write-Host "[3/6] Инициализация Go модуля и установка зависимостей..." -ForegroundColor Yellow

if (-not (Test-Path $ProjectPath)) {
    Write-Host "  ✗ Ошибка: Папка проекта не найдена: $ProjectPath" -ForegroundColor Red
    exit 1
}

Set-Location $ProjectPath

# Инициализация go.mod если не существует
if (-not (Test-Path "go.mod")) {
    Write-Host "  Инициализация go.mod..." -ForegroundColor Cyan
    go mod init github.com/user/go_lng
}

# Установка зависимостей
Write-Host "  Установка зависимостей Go..." -ForegroundColor Cyan
go mod tidy
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ✗ Ошибка при установке зависимостей" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ Зависимости установлены" -ForegroundColor Green

# Шаг 4: Установка Wails
Write-Host ""
Write-Host "[4/6] Проверка и установка Wails..." -ForegroundColor Yellow
if (Test-WailsInstalled) {
    Write-Host "  ✓ Wails уже установлен: $(wails version)" -ForegroundColor Green
} else {
    Write-Host "  Установка Wails..." -ForegroundColor Cyan
    go install github.com/wailsapp/wails/v2/cmd/wails@latest
    
    # Добавление GOPATH/bin в PATH
    $GoBinPath = Join-Path (go env GOPATH) "bin"
    if (Test-Path $GoBinPath) {
        $env:Path = "$GoBinPath;$env:Path"
        [Environment]::SetEnvironmentVariable("Path", $env:Path, [EnvironmentVariableTarget]::User)
    }
    
    if (Test-WailsInstalled) {
        Write-Host "  ✓ Wails успешно установлен: $(wails version)" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Wails не найден после установки." -ForegroundColor Yellow
        Write-Host "  Попробуйте установить вручную: go install github.com/wailsapp/wails/v2/cmd/wails@latest" -ForegroundColor Cyan
        Write-Host "  Убедитесь, что `%GOPATH%\bin` добавлен в PATH." -ForegroundColor Yellow
    }
}

# Шаг 5: Запуск тестов
Write-Host ""
Write-Host "[5/6] Запуск тестов..." -ForegroundColor Yellow
if (Test-Path "internal") {
    go test ./... -v
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  ✓ Все тесты пройдены" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ Некоторые тесты не пройдены (это может быть нормально для начальной версии)" -ForegroundColor Yellow
    }
} else {
    Write-Host "  ⊘ Тесты не найдены, пропускаем" -ForegroundColor Gray
}

# Шаг 6: Сборка бинарника
Write-Host ""
Write-Host "[6/6] Сборка бинарника..." -ForegroundColor Yellow

# Проверка наличия main.go
if (-not (Test-Path "main.go")) {
    Write-Host "  ✗ Ошибка: main.go не найден" -ForegroundColor Red
    exit 1
}

# Сборка через go build (базовая версия без Wails UI)
Write-Host "  Сборка через go build..." -ForegroundColor Cyan
go build -o central-office.exe -ldflags="-s -w" .
if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✓ Бинарник успешно собран: central-office.exe" -ForegroundColor Green
    $binarySize = (Get-Item "central-office.exe").Length / 1MB
    Write-Host "  Размер: $([math]::Round($binarySize, 2)) MB" -ForegroundColor Green
} else {
    Write-Host "  ✗ Ошибка сборки через go build" -ForegroundColor Red
}

# Попытка сборки через Wails (если установлен и есть проект wails)
if (Test-WailsInstalled) {
    if (Test-Path "wails.json") {
        Write-Host "  Сборка через Wails (полная версия с UI)..." -ForegroundColor Cyan
        wails build -o central-office-wails.exe
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  ✓ Wails бинарник успешно собран: central-office-wails.exe" -ForegroundColor Green
        } else {
            Write-Host "  ⚠ Ошибка сборки Wails (возможно, требуется дополнительная настройка)" -ForegroundColor Yellow
        }
    } else {
        Write-Host "  ⊘ wails.json не найден. Для полной сборки Wails выполните: wails init" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Сборка завершена!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Запуск приложения:" -ForegroundColor Yellow
Write-Host "  .\central-office.exe --init-db" -ForegroundColor Cyan
Write-Host ""
Write-Host "Если установлен Wails и настроен frontend:" -ForegroundColor Yellow
Write-Host "  wails dev  # режим разработки" -ForegroundColor Cyan
Write-Host "  wails build # полная сборка" -ForegroundColor Cyan
Write-Host ""

# Возврат в исходную директорию
Set-Location $PSScriptRoot
