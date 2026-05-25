"""
Реальный WebDAV клиент для синхронизации
"""
import requests
from requests.auth import HTTPBasicAuth
from typing import Optional, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class WebDAVClient:
    """Клиент для работы с WebDAV сервером"""

    def __init__(self, url: str, username: str = None, password: str = None):
        """
        Args:
            url: URL WebDAV сервера
            username: Имя пользователя
            password: Пароль
        """
        self.url = url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password) if username else None
        self.session = requests.Session()
        if self.auth:
            self.session.auth = self.auth

    def test_connection(self) -> bool:
        """
        Тест подключения к серверу

        Returns:
            True если подключение успешно
        """
        try:
            response = self.session.request(
                'PROPFIND',
                self.url,
                timeout=5,
                headers={'Depth': '0'}
            )
            return response.status_code in [200, 207, 301, 302]
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def list_files(self, path: str = "") -> List[str]:
        """
        Получить список файлов в папке

        Args:
            path: Путь к папке

        Returns:
            Список имен файлов
        """
        try:
            # Конвертируем Windows пути в URL пути
            path = path.replace('\\', '/')
            url = f"{self.url}/{path}".rstrip('/')
            response = self.session.request(
                'PROPFIND',
                url,
                timeout=10,
                headers={'Depth': '1'}
            )

            if response.status_code not in [200, 207]:
                logger.error(f"Failed to list files: {response.status_code}")
                return []

            # Парсим XML ответ
            import xml.etree.ElementTree as ET
            files = []

            try:
                root = ET.fromstring(response.content)
                # WebDAV использует namespace
                namespaces = {'d': 'DAV:'}

                for response_elem in root.findall('.//d:response', namespaces):
                    href = response_elem.find('d:href', namespaces)
                    if href is not None:
                        file_path = href.text
                        # Извлекаем имя файла из пути
                        if file_path and not file_path.endswith('/'):
                            file_name = file_path.split('/')[-1]
                            if file_name and file_name.endswith('.json'):
                                files.append(file_name)

                logger.info(f"Found {len(files)} files in {path}")
                return files

            except ET.ParseError as e:
                logger.error(f"Failed to parse XML response: {e}")
                return []

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """
        Скачать файл с сервера

        Args:
            remote_path: Путь к файлу на сервере
            local_path: Путь для сохранения локально

        Returns:
            True если успешно
        """
        try:
            # Конвертируем Windows пути в URL пути
            remote_path = remote_path.replace('\\', '/')
            url = f"{self.url}/{remote_path}"
            response = self.session.get(url, timeout=30)

            if response.status_code == 200:
                Path(local_path).parent.mkdir(parents=True, exist_ok=True)
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded: {remote_path} -> {local_path}")
                return True
            else:
                logger.error(f"Failed to download {remote_path}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """
        Загрузить файл на сервер

        Args:
            local_path: Путь к локальному файлу
            remote_path: Путь на сервере

        Returns:
            True если успешно
        """
        try:
            if not Path(local_path).exists():
                logger.error(f"Local file not found: {local_path}")
                return False

            # Конвертируем Windows пути в URL пути (обратные слеши в прямые)
            remote_path = remote_path.replace('\\', '/')
            url = f"{self.url}/{remote_path}"

            # Создаем папки если нужно
            parent_path = str(Path(remote_path).parent).replace('\\', '/')
            if parent_path and parent_path != '.':
                self.create_directory(parent_path)

            with open(local_path, 'rb') as f:
                response = self.session.put(url, data=f, timeout=30)

            if response.status_code in [200, 201, 204]:
                logger.info(f"Uploaded: {local_path} -> {remote_path}")
                return True
            else:
                logger.error(f"Failed to upload {local_path}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error uploading file: {e}")
            return False

    def create_directory(self, path: str) -> bool:
        """
        Создать папку на сервере

        Args:
            path: Путь к папке

        Returns:
            True если успешно
        """
        try:
            # Конвертируем Windows пути в URL пути
            path = path.replace('\\', '/')

            # Создаем все родительские папки рекурсивно
            parts = path.split('/')
            current_path = ''

            for part in parts:
                if not part or part == '.':
                    continue

                current_path = f"{current_path}/{part}" if current_path else part
                url = f"{self.url}/{current_path}".rstrip('/')

                try:
                    response = self.session.request('MKCOL', url, timeout=10)

                    if response.status_code in [200, 201]:
                        logger.info(f"Created directory: {current_path}")
                    elif response.status_code == 405:
                        # Папка уже существует - это нормально
                        pass
                    else:
                        logger.warning(f"Failed to create directory {current_path}: {response.status_code}")
                except Exception as e:
                    logger.warning(f"Error creating directory {current_path}: {e}")

            return True

        except Exception as e:
            logger.error(f"Error creating directory: {e}")
            return False

    def delete_file(self, remote_path: str) -> bool:
        """
        Удалить файл с сервера

        Args:
            remote_path: Путь к файлу на сервере

        Returns:
            True если успешно
        """
        try:
            # Конвертируем Windows пути в URL пути
            remote_path = remote_path.replace('\\', '/')
            url = f"{self.url}/{remote_path}"
            response = self.session.delete(url, timeout=10)

            if response.status_code in [200, 204, 404]:  # 404 = уже удален
                logger.info(f"Deleted: {remote_path}")
                return True
            else:
                logger.error(f"Failed to delete {remote_path}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error deleting file: {e}")
            return False

    def move_file(self, source_path: str, dest_path: str) -> bool:
        """
        Переместить файл на сервере

        Args:
            source_path: Исходный путь
            dest_path: Целевой путь

        Returns:
            True если успешно
        """
        try:
            # Конвертируем Windows пути в URL пути
            source_path = source_path.replace('\\', '/')
            dest_path = dest_path.replace('\\', '/')

            source_url = f"{self.url}/{source_path}"
            dest_url = f"{self.url}/{dest_path}"

            response = self.session.request(
                'MOVE',
                source_url,
                headers={'Destination': dest_url},
                timeout=10
            )

            if response.status_code in [200, 201, 204]:
                logger.info(f"Moved: {source_path} -> {dest_path}")
                return True
            else:
                logger.error(f"Failed to move {source_path}: {response.status_code}")
                return False

        except Exception as e:
            logger.error(f"Error moving file: {e}")
            return False

    def file_exists(self, remote_path: str) -> bool:
        """
        Проверить существование файла

        Args:
            remote_path: Путь к файлу на сервере

        Returns:
            True если файл существует
        """
        try:
            # Конвертируем Windows пути в URL пути
            remote_path = remote_path.replace('\\', '/')
            url = f"{self.url}/{remote_path}"
            response = self.session.head(url, timeout=10)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error checking file existence: {e}")
            return False
