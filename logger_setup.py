import logging
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
}

LOG_LEVEL_CONSOLE = logging.DEBUG
LOG_LEVEL_FILE = logging.WARNING

logger = None

def setup_logging(log_level="DEBUG"):
    global logger
    if logger is None:
        logger = logging.getLogger('main.py')
        logger.setLevel(logging.DEBUG)

        # Проверка наличия обработчиков
        if not logger.hasHandlers():
            # Настройка обработчика консоли
            console_handler = colorlog.StreamHandler()
            console_handler.setLevel(
                getattr(logging, log_level.upper(), logging.DEBUG))  # Установка уровня из параметра
            console_formatter = colorlog.ColoredFormatter(LOG_FORMAT_CONSOLE, log_colors=LOG_COLORS)
            console_handler.setFormatter(console_formatter)
            logger.addHandler(console_handler)

            # Настройка обработчика файла
            file_handler = logging.FileHandler('app.log')
            file_handler.setLevel(LOG_LEVEL_FILE)
            file_formatter = logging.Formatter(LOG_FORMAT_FILE)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger