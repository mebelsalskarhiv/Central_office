"""
Launcher для OrderManager Central Office
Запускает приложение через встроенный Python
"""
import sys
import os
import subprocess
from pathlib import Path

def main():
    # Получаем директорию, где находится launcher
    if getattr(sys, 'frozen', False):
        # Запущен как EXE
        app_dir = Path(sys.executable).parent
    else:
        # Запущен как скрипт
        app_dir = Path(__file__).parent

    # Путь к python.exe и main.py
    python_exe = app_dir / "python.exe"
    main_py = app_dir / "src" / "main.py"

    if not python_exe.exists():
        print(f"Error: python.exe not found at {python_exe}")
        input("Press Enter to exit...")
        sys.exit(1)

    if not main_py.exists():
        print(f"Error: main.py not found at {main_py}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Запускаем main.py через python.exe
    try:
        subprocess.run([str(python_exe), str(main_py)], cwd=str(app_dir))
    except Exception as e:
        print(f"Error launching application: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == "__main__":
    main()
