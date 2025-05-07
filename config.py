import sys
import traceback
import yaml
import os

from environs import Env

from logger_setup import setup_logging


CONFIG_YAML = "config.yaml"  # Название файла конфигурации, в корне проекта
CONFIG_YAML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_YAML)


# чтобы преобразовать путь из формата Windows в формат UNIX
def convert_windows_path_to_unix(path):
    return path.replace("\\", "/")


def load_yaml_config(CONFIG_YAML_PATH):
    """
    Функция для загрузки конфигурации из YAML-файла.

    :param file_path: Путь до YAML-файла.
    :return: Словарь с загруженной конфигурацией.
    """
    with open(CONFIG_YAML_PATH, "r", encoding="utf-8") as file_config_yaml:
        try:
            config = yaml.safe_load(file_config_yaml)
            # print(f" (load_yaml_config), Конфигурация успешно загружена из {FILE_PATH}, формат Windows")
            return config
        except yaml.YAMLError as err:
            traceback.print_exc()
            print(f" (load_yaml_config), Произошла ошибка при загрузке YAML- 1: {err}")
            return None


config_data = load_yaml_config(CONFIG_YAML_PATH)

LOG_LEVEL = config_data.get(
    "LOG_LEVEL", "DEBUG"
)  # Значение по умолчанию — "DEBUG", require for logger_setup.py
if LOG_LEVEL is None:
    LOG_LEVEL = "DEBUG"  # Устанавливаем значение по умолчанию
logger = setup_logging(
    log_level=LOG_LEVEL
)  # Передача уровня логирования в setup_logging
logger.info(f"LOG_LEVEL: %s", LOG_LEVEL)


class Config:
    """Класс для управления конфигурацией приложения"""

    def __init__(self):
        self.env = self._setup_environment()
        self.file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      self.env.str("DATA_BASE"))
        self.baseurl = self.env.str("BASEURL")
        self.app_id = self.env.str("APP_ID")
        self.app_key = self.env.str("APP_KEY")
        self.secret_key = self.env.str("SECRET_KEY")
        self.worksheet_name = self.env.str("WORKSHEET_NAME")

        self.db_port = self.env("DB_PORT")
        self.db_host = self.env.str("DB_HOST")
        self.db_password = self.env.str("DB_PASSWORD")
        self.db_user = self.env.str("DB_USER")
        self.db_name = self.env.str("DB_NAME")

    @staticmethod
    def _setup_environment() -> Env:
        """Загрузка переменных окружения"""
        env = Env()
        if not os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"):
            logger.error("Файл .env не найден. Проверьте, что он существует в корне проекта.")
            sys.exit(1)
        env.read_env()
        return env


config = Config()
BASEURL = config.baseurl
SECRET_KEY = config.secret_key
APP_ID = config.app_id
APP_KEY = config.app_key
DATA_BASE_PATH = config.file_path
WORKSHEET_NAME = config.worksheet_name

DB_NAME=config.db_name
DB_USER=config.db_user
DB_PASSWORD=config.db_password
DB_HOST=config.db_host
DB_PORT=config.db_port