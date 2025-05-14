import logging
import sys

import colorlog

# Константы для форматов логирования
LOG_FORMAT_CONSOLE = '%(log_color)s%(asctime)s - %(levelname)s - %(message)s'
LOG_FORMAT_FILE = '%(asctime)s - %(levelname)s - %(message)s'

LOG_COLORS = {
    'DEBUG': 'white',
    'INFO': 'green',
    'WARNING': 'yellow',
    'ERROR': 'red',
    'CRITICAL': 'bold_red',
    'UPDATE': 'blue',  # Добавляем цвет для нового уровня
}

LOG_LEVEL_CONSOLE = logging.DEBUG
LOG_LEVEL_FILE = logging.INFO  # WARNING

logger = None

# Добавляем кастомный уровень UPDATE
UPDATE_LEVEL = 25
logging.addLevelName(UPDATE_LEVEL, "UPDATE")

def update(self, message, *args, **kwargs):
    if self.isEnabledFor(UPDATE_LEVEL):
        self._log(UPDATE_LEVEL, message, args, **kwargs)

# Добавляем метод в класс Logger
logging.Logger.update = update

def setup_logging(log_level="DEBUG"):
    global logger
    if logger is None:
        logger = logging.getLogger('main.py')
        logger.setLevel(logging.DEBUG)

        # Проверка наличия обработчиков
        if not logger.hasHandlers():
            # Настройка обработчика консоли с цветным выводом
            console_handler = colorlog.StreamHandler(sys.stdout)
            console_handler.setLevel(
                getattr(logging, log_level.upper(), logging.DEBUG))  # Установка уровня из параметра
            console_formatter = colorlog.ColoredFormatter(LOG_FORMAT_CONSOLE, log_colors=LOG_COLORS)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # Настройка обработчика файла без цветного вывода
            file_handler = logging.FileHandler('app.log', encoding="utf-8")
            file_handler.setLevel(LOG_LEVEL_FILE)
            file_formatter = logging.Formatter(LOG_FORMAT_FILE)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger