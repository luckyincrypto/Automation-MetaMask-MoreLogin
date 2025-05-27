import random
import time

from config import logger, MIN_PERCENT_MON, MAX_PERCENT_MON, MIN_PERCENT_TOKEN, \
    MAX_PERCENT_TOKEN  # Подключение конфигурации логгера и констант из config


def calculate_percentage(number: float, percent: float) -> float:
    try:
        return round((number * percent) / 100, 4)  # Округляем до 4 знаков после запятой
    except Exception as e:
        print(f"Ошибка: {e}")
        return 0.0

def random_number_for_sell(selling_symbol, number_tokens_selling):
    # Расчет количества для продажи
    if selling_symbol.lower() == 'mon':
        random_percent = random.randint(MIN_PERCENT_MON, MAX_PERCENT_MON)
        logger.debug(f'Выбран коин: {selling_symbol}')
    else:
        random_percent = random.randint(MIN_PERCENT_TOKEN, MAX_PERCENT_TOKEN)
        logger.debug(f'Выбран токен: {selling_symbol}')

    number_for_sell = calculate_percentage(number_tokens_selling, random_percent)
    logger.debug(
        f"Выбрано рандомно число: {random_percent}% от {number_tokens_selling} = "
        f"{number_for_sell} на продажу")
    return number_for_sell


def adjust_window_position(driver):
    """Настраивает позицию и размер окна MetaMask."""
    try:
        rect = driver.get_window_rect()
        logger.debug(f"Window position: ({rect['x']}, {rect['y']}), Size: {rect['width']}x{rect['height']}")

        driver.maximize_window()
        time.sleep(2)

        driver.set_window_rect(
            rect['x'],
            rect['y'],
            rect['width'],
            rect['height']
        )
    except Exception as e:
        logger.error(f'Error adjusting window position: {str(e)}')