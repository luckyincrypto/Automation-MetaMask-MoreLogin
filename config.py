import logging
import traceback

import yaml
import os
from logger_setup import setup_logging

# logger = setup_logging()

CONFIG_YAML='config.yaml'  # Название файла конфигурации, в корне проекта
FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_YAML)

# чтобы преобразовать путь из формата Windows в формат UNIX
def convert_windows_path_to_unix(path):
    return path.replace('\\', '/')

def load_yaml_config(FILE_PATH):
    """
    Функция для загрузки конфигурации из YAML-файла.

    :param file_path: Путь до YAML-файла.
    :return: Словарь с загруженной конфигурацией.
    """
    with open(FILE_PATH, 'r') as file_config_yaml:
        try:
            config = yaml.safe_load(file_config_yaml)
            print(f" (load_yaml_config), Конфигурация успешно загружена из {FILE_PATH}, формат Windows")
            return config
        except yaml.YAMLError as err:
            traceback.print_exc()
            print(f" (load_yaml_config), Произошла ошибка при загрузке YAML- 1: {err}")
            # print(f" (load_yaml_config), Произошла ошибка при загрузке YAML - 2: {traceback.format_exc()}")
            return None


config_data = load_yaml_config(FILE_PATH)

LOG_LEVEL = config_data.get("LOG_LEVEL", "DEBUG")  # require for logger_setup.py
logger = setup_logging(log_level=LOG_LEVEL)  # Передача уровня логирования в setup_logging

log_level = logger.getEffectiveLevel()
logger.info("LOG_LEVEL = %s", logging.getLevelName(log_level))


path_local_cashe = convert_windows_path_to_unix(config_data['path_local_cashe'])  # require for modify_file_runtimelavamoat in file lava_more.py
BASEURL = config_data['BASEURL']  # require for BrowserManager in main.py

logger.debug(f'По умолчанию в этой папке хранится кэш временных файлов: '
             f'{convert_windows_path_to_unix(config_data['path_local_cashe'])}, формат UNIX\n'
             f'BASEURL = {BASEURL}')

