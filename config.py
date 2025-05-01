import traceback
import yaml
import os
from logger_setup import setup_logging


CONFIG_YAML = "config.yaml"  # Название файла конфигурации, в корне проекта
FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_YAML)


# чтобы преобразовать путь из формата Windows в формат UNIX
def convert_windows_path_to_unix(path):
    return path.replace("\\", "/")


def load_yaml_config(FILE_PATH):
    """
    Функция для загрузки конфигурации из YAML-файла.

    :param file_path: Путь до YAML-файла.
    :return: Словарь с загруженной конфигурацией.
    """
    with open(FILE_PATH, "r", encoding="utf-8") as file_config_yaml:
        try:
            config = yaml.safe_load(file_config_yaml)
            # print(f" (load_yaml_config), Конфигурация успешно загружена из {FILE_PATH}, формат Windows")
            return config
        except yaml.YAMLError as err:
            traceback.print_exc()
            print(f" (load_yaml_config), Произошла ошибка при загрузке YAML- 1: {err}")
            return None


config_data = load_yaml_config(FILE_PATH)

LOG_LEVEL = config_data.get(
    "LOG_LEVEL", "DEBUG"
)  # Значение по умолчанию — "DEBUG", require for logger_setup.py
if LOG_LEVEL is None:
    LOG_LEVEL = "DEBUG"  # Устанавливаем значение по умолчанию
logger = setup_logging(
    log_level=LOG_LEVEL
)  # Передача уровня логирования в setup_logging
logger.info(f"LOG_LEVEL: %s", LOG_LEVEL)

BASEURL = config_data["BASEURL"]  # require for BrowserManager in main.py
logger.debug(f"BASEURL = {BASEURL}")
