import time

from config import logger  # Подключение конфигурации логгера


def calculate_percentage(number: float, percent: float) -> float:
    try:
        return round((number * percent) / 100, 4)  # Округляем до двух знаков после запятой
    except Exception as e:
        print(f"Ошибка: {e}")
        return 0.0


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