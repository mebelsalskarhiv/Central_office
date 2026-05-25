# Исправления синхронизации - 01.05.2026

## ✅ Исправлено

### 1. Проблема с test_manager
**Было:** Всегда создавалась папка `test_manager`, игнорируя реальных менеджеров из БД

**Исправлено:**
- Теперь получаем список всех активных менеджеров из БД
- Генерируются файлы для каждого менеджера отдельно
- Используется реальный PIN-код из таблицы `managers`

**Код:**
```python
managers = session.query(Manager).filter_by(status='ACTIVE').all()
for manager in managers:
    manager_pin = manager.pin_code
    # Генерация файлов для каждого менеджера
```

### 2. Проблема с изображениями товаров
**Было:** 
- В `products.json` указывались полные локальные пути: `E:\WORK_RUCHEEK\...\image.jpg`
- Изображения не выгружались на WebDAV
- Мобильное приложение не могло получить изображения

**Исправлено:**
- Изображения копируются в `data/webdav/{PIN}/incoming/images/`
- В `products.json` используются относительные пути: `images/PROD-123.jpg`
- Изображения загружаются на WebDAV вместе с JSON
- Мобильное приложение скачивает изображения с WebDAV

**Структура на WebDAV:**
```
{PIN}/
  incoming/
    products.json          # Содержит "image_url": "images/PROD-123.jpg"
    settings.json
    images/
      PROD-123.jpg         # Полное изображение (800x800)
      PROD-123_thumb.jpg   # Миниатюра (200x200)
      PROD-456.jpg
      PROD-456_thumb.jpg
```

**Новые методы в SyncManager:**
- `copy_product_images(manager_pin)` - копирует изображения в папку менеджера
- `_get_relative_image_path(image_url)` - конвертирует полный путь в относительный

## 📱 Как это работает для мобильного приложения

### Процесс синхронизации:

1. **Центральная система (выгрузка):**
   - Генерирует `products.json` с относительными путями к изображениям
   - Копирует все изображения в `{PIN}/incoming/images/`
   - Загружает всё на WebDAV сервер

2. **Мобильное приложение (загрузка):**
   - Скачивает `products.json` с WebDAV
   - Читает `image_url`: `"images/PROD-123.jpg"`
   - Скачивает изображение с WebDAV: `{PIN}/incoming/images/PROD-123.jpg`
   - Сохраняет локально в кэш приложения

3. **Отображение в приложении:**
   - Если изображение есть в кэше - показывает из кэша
   - Если нет - показывает placeholder
   - Фоновая загрузка недостающих изображений

## 🔧 Что нужно сделать

### В центральной системе:
✅ Уже готово - исправления применены

### В мобильном приложении (Android):
Нужно обновить `SyncManager.kt`:

```kotlin
// При загрузке products.json
fun downloadProducts() {
    val productsJson = webdavClient.downloadFile("${pin}/incoming/products.json")
    val products = parseProducts(productsJson)
    
    // Скачиваем изображения
    products.forEach { product ->
        if (product.imageUrl.isNotEmpty()) {
            downloadProductImage(product.imageUrl)
        }
    }
}

fun downloadProductImage(relativePath: String) {
    // relativePath = "images/PROD-123.jpg"
    val remoteUrl = "${pin}/incoming/${relativePath}"
    val localPath = "${cacheDir}/products/${relativePath}"
    
    webdavClient.downloadFile(remoteUrl, localPath)
}
```

## 🧪 Как протестировать

1. **Добавьте менеджера в БД:**
   - Откройте вкладку "Менеджеры"
   - Добавьте менеджера с PIN, например: 1234
   - Убедитесь, что статус "Активен"

2. **Добавьте товар с изображением:**
   - Откройте вкладку "Товары"
   - Добавьте товар
   - Загрузите изображение
   - Сохраните

3. **Запустите синхронизацию:**
   - Нажмите F5
   - Выберите "Только выгрузка"
   - Нажмите "Начать синхронизацию"

4. **Проверьте результат:**
   - Локально: `data/webdav/1234/incoming/`
     - `products.json` - должен содержать `"image_url": "images/PROD-XXX.jpg"`
     - `images/PROD-XXX.jpg` - должен существовать
   - На WebDAV: `1234/incoming/images/` - должны быть изображения

5. **Проверьте products.json:**
   ```json
   {
     "products": [
       {
         "id": "PROD-123",
         "name": "Тестовый товар",
         "image_url": "images/PROD-123.jpg",  // ← Относительный путь!
         ...
       }
     ]
   }
   ```

## 📝 Примечания

- Копируются как полные изображения (800x800), так и миниатюры (_thumb.jpg)
- Если у товара нет изображения, `image_url` будет пустой строкой
- Изображения копируются только для активных товаров (`is_active = true`)
- Если изображение не найдено локально, оно пропускается (без ошибки)

## ✅ Готово к тестированию

Перезапустите приложение и попробуйте синхронизацию с реальным менеджером!

**Дата:** 01.05.2026 10:15  
**Файлы изменены:**
- `src/gui/dialogs/manual_sync_dialog.py`
- `src/sync/sync_manager.py`
