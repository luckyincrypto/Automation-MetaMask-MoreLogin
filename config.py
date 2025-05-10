import sys
import traceback
import yaml
import os
from typing import Dict, Any, Optional
from environs import Env
from logger_setup import setup_logging


CONFIG_YAML = "config.yaml"  # Название файла конфигурации, в корне проекта
CONFIG_YAML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_YAML)


def convert_windows_path_to_unix(path: str) -> str:
    """Преобразует путь из формата Windows в формат UNIX."""
    return path.replace("\\", "/")


def load_yaml_config(config_path: str) -> Optional[Dict[str, Any]]:
    """
    Загружает конфигурацию из YAML-файла.

    Args:
        config_path: Путь до YAML-файла.

    Returns:
        Dict[str, Any]: Словарь с загруженной конфигурацией или None в случае ошибки.
    """
    try:
        with open(config_path, "r", encoding="utf-8") as file_config_yaml:
            config = yaml.safe_load(file_config_yaml)
            return config
    except yaml.YAMLError as err:
        traceback.print_exc()
        print(f"Ошибка при загрузке YAML: {err}")
        return None
    except Exception as e:
        traceback.print_exc()
        print(f"Неожиданная ошибка при загрузке конфигурации: {e}")
        return None


# Загружаем конфигурацию из YAML
config_data = load_yaml_config(CONFIG_YAML_PATH)

# Настройки логирования
LOG_LEVEL = config_data.get("LOG_LEVEL", "DEBUG") if config_data else "DEBUG"
logger = setup_logging(log_level=LOG_LEVEL)
logger.info(f"LOG_LEVEL: {LOG_LEVEL}")


class Config:
    """Класс для управления конфигурацией приложения."""

    def __init__(self):
        self.env = self._setup_environment()
        self._load_env_variables()
        self._load_yaml_settings()

    def _setup_environment(self) -> Env:
        """Загружает переменные окружения из .env файла."""
        env = Env()
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        if not os.path.exists(env_path):
            logger.error("Файл .env не найден. Проверьте, что он существует в корне проекта.")
            sys.exit(1)
        env.read_env()
        return env

    def _load_env_variables(self):
        """Загружает переменные окружения из .env файла."""
        # Базовые настройки
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     self.env.str("DATA_BASE"))
        self.baseurl = self.env.str("BASEURL")
        self.app_id = self.env.str("APP_ID")
        self.app_key = self.env.str("APP_KEY")
        self.secret_key = self.env.str("SECRET_KEY")
        self.worksheet_name = self.env.str("WORKSHEET_NAME")

        # Настройки базы данных
        # self.db_port = self.env("DB_PORT")
        # self.db_host = self.env.str("DB_HOST")
        # self.db_password = self.env.str("DB_PASSWORD")
        # self.db_user = self.env.str("DB_USER")
        self.db_name = self.env.str("DB_NAME")

    def _load_yaml_settings(self):
        """Загружает настройки из YAML файла."""
        if not config_data:
            logger.error("Не удалось загрузить настройки из config.yaml. Проверьте, что он существует в корне проекта.")
            sys.exit(1)

        # Глобальные настройки
        self.global_settings = config_data.get("GLOBAL_SETTINGS", {})
        self.mode_close_profile = self.global_settings.get("MODE_CLOSE_PROFILE", True)

        # Настройки активности
        self.activity_settings = config_data.get("ACTIVITY_SETTINGS", {})
        self.auto_process_unexpected_status = self.activity_settings.get("AUTO_PROCESS_UNEXPECTED_STATUS", True)
        self.success_wait_time = self.activity_settings.get("SUCCESS_WAIT_TIME", {"HOURS": 24, "MINUTES": 3})
        self.max_records_per_profile = self.activity_settings.get("MAX_RECORDS_PER_PROFILE", 35)


# Создаем экземпляр конфигурации
config = Config()

# Экспортируем все необходимые переменные
BASEURL = config.baseurl
SECRET_KEY = config.secret_key
APP_ID = config.app_id
APP_KEY = config.app_key
DATA_BASE_PATH = config.file_path
WORKSHEET_NAME = config.worksheet_name

# Настройки базы данных
DB_NAME = f"{config.db_name}.sqlite3"  # Для SQLite Database и PostgreSQL
# DB_USER = config.db_user  # Для PostgreSQL
# DB_PASSWORD = config.db_password  # Для PostgreSQL
# DB_HOST = config.db_host  # Для PostgreSQL
# DB_PORT = config.db_port  # Для PostgreSQL

# Настройки из YAML
MODE_CLOSE_PROFILE = config.mode_close_profile
AUTO_PROCESS_UNEXPECTED_STATUS = config.auto_process_unexpected_status
SUCCESS_WAIT_TIME = config.success_wait_time
MAX_RECORDS_PER_PROFILE = config.max_records_per_profile
GLOBAL_SETTINGS = config.global_settings