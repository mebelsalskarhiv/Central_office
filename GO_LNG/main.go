package main

import (
	"context"
	"embed"
	"log"
	"os"

	"github.com/wailsapp/wails/v2"
	"github.com/wailsapp/wails/v2/pkg/options"
	"github.com/wailsapp/wails/v2/pkg/options/assetserver"

	"github.com/ordermanager/central-office/internal/database"
	"github.com/ordermanager/central-office/internal/handlers"
)

//go:embed frontend/dist
var assets embed.FS

func main() {
	// Парсинг аргументов командной строки
	dbPath := ""
	recreateDB := false

	for i, arg := range os.Args {
		if arg == "--init-db" {
			// Флаг инициализации (используется по умолчанию)
		} else if arg == "--recreate-db" {
			recreateDB = true
		} else if arg == "--db-path" && i+1 < len(os.Args) {
			dbPath = os.Args[i+1]
		}
	}

	// Инициализация базы данных
	log.Println("Initializing database...")
	db, err := database.InitDatabase(dbPath, recreateDB)
	if err != nil {
		log.Fatalf("Error initializing database: %v", err)
	}
	log.Println("Database initialized successfully!")

	// Создаем обработчик приложения
	app := handlers.NewApp(db)

	// Создаем Wails приложение
	err = wails.Run(&options.App{
		Title:     "OrderManager Central Office",
		Width:     1400,
		Height:    900,
		MinWidth:  1024,
		MinHeight: 768,
		AssetServer: &assetserver.Options{
			Assets: assets,
		},
		BackgroundColour: &options.RGBA{R: 27, G: 38, B: 54, A: 1},
		OnStartup: func(ctx context.Context) {
			app.Startup(ctx)
		},
		OnShutdown: func(ctx context.Context) {
			app.Shutdown(ctx)
		},
		Bind: []interface{}{
			app,
		},
	})

	if err != nil {
		log.Fatal("Error running application:", err)
	}
}
