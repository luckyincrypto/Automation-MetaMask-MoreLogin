import random
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
        self.mix_profiles = self.global_settings.get("MIX_PROFILES", True)
        self.profile_delay = self.global_settings.get("PROFILE_DELAY")
        self.auto_mode = self.global_settings.get("AUTO_MODE", False)
        self.min_interval_minutes = self.global_settings.get("MIN_INTERVAL_MINUTES", 60)  # Минимальный интервал между запусками (в минутах)
        self.max_interval_minutes = self.global_settings.get("MAX_INTERVAL_MINUTES", 150)  # Минимальный интервал между запусками (в минутах)

        # Настройки активности
        self.activity_settings = config_data.get("ACTIVITY_SETTINGS", {})
        self.auto_process_unexpected_status = self.activity_settings.get("AUTO_PROCESS_UNEXPECTED_STATUS", True)
        self.success_wait_time = self.activity_settings.get("SUCCESS_WAIT_TIME", {"HOURS": 24, "MINUTES": 3})
        self.max_records_per_profile = self.activity_settings.get("MAX_RECORDS_PER_PROFILE", 35)

        # Экспортируем настройки активности
        self.ACTIVITY_SETTINGS = self.activity_settings

        # Настройки обработки активностей Kuru
        self.kuru_activity_settings = config_data.get("KURU_ACTIVITY_SETTINGS", {})


# Создаем экземпляр конфигурации
config = Config()

# Экспортируем все необходимые переменные
BASEURL = config.baseurl  # Используем порт из .env файла
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
GLOBAL_SETTINGS = config.global_settings # Глобальные настройки скрипта
ACTIVITY_SETTINGS = config.activity_settings # Настройки обработки активностей MonadFaucet
MODE_CLOSE_PROFILE = config.mode_close_profile  # Закрывать профиль после выполнения: TRUE/FALSE
MIX_PROFILES = config.mix_profiles  # Перемешивать профили при обработке нескольких: TRUE/FALSE
PROFILE_DELAY = config.profile_delay   # Задержка между профилями
AUTO_MODE = config.auto_mode  # Автоматический запуск скрипта: TRUE/FALSE
MIN_INTERVAL_MINUTES = config.min_interval_minutes   # Минимальный интервал между запусками main.py (в минутах)
MAX_INTERVAL_MINUTES = config.max_interval_minutes  # Максимальный интервал между запусками (в минутах)

# Настройки обработки активностей MonadFaucet
AUTO_PROCESS_UNEXPECTED_STATUS = config.auto_process_unexpected_status
SUCCESS_WAIT_TIME = config.success_wait_time
MAX_RECORDS_PER_PROFILE = config.max_records_per_profile

# Получаем значение из конфигурации и преобразуем в список
# logger.debug(f"Activity settings from config: {config.activity_settings}")
DEFAULT_ACTIVITIES = [activity.strip() for activity in config.activity_settings.get("DEFAULT_ACTIVITIES", "").split(",") if activity.strip()]
logger.debug(f"Processed DEFAULT_ACTIVITIES: {DEFAULT_ACTIVITIES}")

# Настройки обработки активностей Kuru
MIN_PERCENT_MON = config.kuru_activity_settings.get("MIN_PERCENT_MON")
MAX_PERCENT_MON = config.kuru_activity_settings.get("MAX_PERCENT_MON")
MIN_PERCENT_TOKEN = config.kuru_activity_settings.get("MIN_PERCENT_TOKEN")
MAX_PERCENT_TOKEN = config.kuru_activity_settings.get("MAX_PERCENT_TOKEN")
MIN_WAIT_TIME_BETWEEN_SWAP = config.kuru_activity_settings.get("MIN_WAIT_TIME_BETWEEN_SWAP")
MAX_WAIT_TIME_BETWEEN_SWAP = config.kuru_activity_settings.get("MAX_WAIT_TIME_BETWEEN_SWAP")
