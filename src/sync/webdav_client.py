"""
WebDAV клиент для синхронизации данных
"""
import os
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import requests
from requests.auth import HTTPBasicAuth


class WebDAVClient:
    """Клиент для работы с WebDAV сервером"""

    def __init__(self, base_url: str, username: str = None, password: str = None):
        """
        Инициализация WebDAV клиента

        Args:
            base_url: Базовый URL WebDAV сервера (например, http://localhost:8080/webdav)
            username: Имя пользователя для аутентификации
            password: Пароль для аутентификации
        """
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth

    def list_files(self, path: str) -> List[Dict]:
        """
        Получить список файлов в директории

        Args:
            path: Путь к директории относительно base_url

        Returns:
            Список словарей с информацией о файлах
        """
        url = f"{self.base_url}/{path.lstrip('/')}"

        # PROPFIND запрос для получения списка файлов
        headers = {
            'Depth': '1',
            'Content-Type': 'application/xml'
        }

        try:
            response = self.session.request('PROPFIND', url, headers=headers)
            response.raise_for_status()

            # TODO: Парсинг XML ответа
            # Пока возвращаем пустой список
            return []

        except requests.exceptions.RequestException as e:
            print(f"Error listing files: {e}")
            return []

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Скачать файл с WebDAV сервера

        Args:
            remote_path: Путь к файлу на сервере
            local_path: Локальный путь для сохранения

        Returns:
            True если успешно, False иначе
        """
        url = f"{self.base_url}/{remote_path.lstrip('/')}"

        try:
            response = self.session.get(url)
            response.raise_for_status()

            # Создаем директорию если не существует
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Сохраняем файл
            with open(local_path, 'wb') as f:
                f.write(response.content)

            return True

        except requests.exceptions.RequestException as e:
            print(f"Error downloading file: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Загрузить файл на WebDAV сервер

        Args:
            local_path: Локальный путь к файлу
            remote_path: Путь на сервере

        Returns:
            True если успешно, False иначе
        """
        url = f"{self.base_url}/{remote_path.lstrip('/')}"

        try:
            with open(local_path, 'rb') as f:
                response = self.session.put(url, data=f)
                response.raise_for_status()

            return True

        except (requests.exceptions.RequestException, IOError) as e:
            print(f"Error uploading file: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """
        Удалить файл с WebDAV сервера

        Args:
            remote_path: Путь к файлу на сервере

        Returns:
            True если успешно, False иначе
        """
        url = f"{self.base_url}/{remote_path.lstrip('/')}"

        try:
            response = self.session.delete(url)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error deleting file: {e}")
            return False

    def create_directory(self, remote_path: str) -> bool:
        """
        Создать директорию на WebDAV сервере

        Args:
            remote_path: Путь к директории

        Returns:
            True если успешно, False иначе
        """
        url = f"{self.base_url}/{remote_path.lstrip('/')}"

        try:
            response = self.session.request('MKCOL', url)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error creating directory: {e}")
            return False

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Переместить файл на WebDAV сервере

        Args:
            source_path: Исходный путь
            dest_path: Целевой путь

        Returns:
            True если успешно, False иначе
        """
        source_url = f"{self.base_url}/{source_path.lstrip('/')}"
        dest_url = f"{self.base_url}/{dest_path.lstrip('/')}"

        headers = {
            'Destination': dest_url
        }

        try:
            response = self.session.request('MOVE', source_url, headers=headers)
            response.raise_for_status()
            return True

        except requests.exceptions.RequestException as e:
            print(f"Error moving file: {e}")
            return False


class LocalWebDAVManager:
    """Менеджер для работы с локальной файловой системой как WebDAV"""

    def __init__(self, root_path: str):
        """
        Инициализация менеджера

        Args:
            root_path: Корневая директория (webdav_root)
        """
        self.root_path = Path(root_path)
        self.root_path.mkdir(exist_ok=True)

    def get_manager_path(self, pin_code: str) -> Path:
        """Получить путь к папке менеджера"""
        return self.root_path / pin_code

    def get_incoming_path(self, pin_code: str) -> Path:
        """Получить путь к папке incoming"""
        return self.get_manager_path(pin_code) / "incoming"

    def get_outgoing_path(self, pin_code: str) -> Path:
        """Получить путь к папке outgoing"""
        return self.get_manager_path(pin_code) / "outgoing"

    def get_processed_path(self, pin_code: str) -> Path:
        """Получить путь к папке processed"""
        return self.get_manager_path(pin_code) / "processed"

    def ensure_manager_folders(self, pin_code: str):
        """Создать структуру папок для менеджера"""
        self.get_incoming_path(pin_code).mkdir(parents=True, exist_ok=True)
        self.get_outgoing_path(pin_code).mkdir(parents=True, exist_ok=True)
        self.get_processed_path(pin_code).mkdir(parents=True, exist_ok=True)

    def list_managers(self) -> List[str]:
        """Получить список PIN-кодов менеджеров"""
        return [d.name for d in self.root_path.iterdir() if d.is_dir()]

    def list_outgoing_files(self, pin_code: str) -> List[Path]:
        """Получить список файлов в outgoing"""
        outgoing_path = self.get_outgoing_path(pin_code)
        if not outgoing_path.exists():
            return []
        return list(outgoing_path.glob("*.json"))

    def read_json_file(self, file_path: Path) -> Optional[Dict]:
        """Прочитать JSON файл"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Error reading JSON file {file_path}: {e}")
            return None

    def write_json_file(self, file_path: Path, data: Dict) -> bool:
        """Записать JSON файл"""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            print(f"Error writing JSON file {file_path}: {e}")
            return False

    def move_to_processed(self, file_path: Path, pin_code: str) -> bool:
        """Переместить файл в processed"""
        try:
            processed_path = self.get_processed_path(pin_code)
            processed_path.mkdir(parents=True, exist_ok=True)

            dest_path = processed_path / file_path.name

            # Если файл уже существует в processed, удаляем его
            if dest_path.exists():
                dest_path.unlink()

            file_path.rename(dest_path)
            return True
        except IOError as e:
            print(f"Error moving file to processed: {e}")
            return False

    def create_products_file(self, pin_code: str, products: List[Dict]) -> bool:
        """Создать файл products.json в incoming"""
        data = {
            "version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            "products": products
        }

        file_path = self.get_incoming_path(pin_code) / "products.json"
        return self.write_json_file(file_path, data)

    def create_settings_file(self, pin_code: str, settings: Dict) -> bool:
        """Создать файл settings.json в incoming"""
        data = {
            "version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            **settings
        }

        file_path = self.get_incoming_path(pin_code) / "settings.json"
        return self.write_json_file(file_path, data)

    def create_sync_metadata_file(self, pin_code: str, metadata: Dict) -> bool:
        """Создать файл sync_metadata.json в incoming"""
        data = {
            "version": 1,
            "timestamp": int(datetime.utcnow().timestamp() * 1000),
            **metadata
        }

        file_path = self.get_incoming_path(pin_code) / "sync_metadata.json"
        return self.write_json_file(file_path, data)


if __name__ == "__main__":
    # Тест локального менеджера
    manager = LocalWebDAVManager("../../webdav_root")

    # Создаем папки для тестового менеджера
    manager.ensure_manager_folders("1234")

    print("Manager folders created successfully!")
    print(f"Managers: {manager.list_managers()}")
