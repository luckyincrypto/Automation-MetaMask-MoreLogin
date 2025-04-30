import time
import random
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
    WebDriverException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from config import logger  # Подключение конфигурации логгера


class SeleniumUtilities:
    """
    Универсальный модуль для работы с Selenium, который можно расширять.
    """

    @staticmethod
    def find_element_safely(driver, by, selector, timeout=10):
        """
        Найти элемент безопасно, без выброса исключений.

        Args:
            driver: Selenium WebDriver instance.
            by: Метод поиска (например, By.XPATH, By.ID).
            selector: Селектор элемента.
            timeout: Максимальное время ожидания элемента в секундах.

        Returns:
            WebElement, если найден, или None в противном случае.
        """
        try:
            wait = WebDriverWait(driver, timeout)
            element = wait.until(EC.presence_of_element_located((by, selector)))
            return element
        except TimeoutException:
            logger.debug(f"Element '{selector}' not found after {timeout} seconds")
            return None
        except Exception as e:
            logger.error(f"Error finding element '{selector}': {e}")
            return None

    @staticmethod
    def click_safely(element, retry_count=3, base_delay=1, jitter_range=(0.8, 1.2), exp_factor=2):
        """
        Попытка нажать на элемент с экспоненциальной задержкой при повторных попытках.

        Args:
            element: WebElement для клика.
            retry_count: Количество попыток клика.
            base_delay: Базовая задержка между попытками в секундах.
            jitter_range: Кортеж (мин., макс.) для случайного отклонения задержки.
            exp_factor: Коэффициент экспоненциального увеличения задержки.

        Returns:
            True, если клик выполнен успешно, False в противном случае.
        """
        if not element:
            logger.error("Element is None, cannot click")
            return False

        for attempt in range(retry_count):
            try:
                element.click()
                logger.debug(f"Element clicked successfully on attempt {attempt + 1}")
                return True
            except ElementClickInterceptedException:
                if attempt < retry_count - 1:
                    retry_delay = base_delay * (exp_factor ** attempt)
                    jitter = random.uniform(*jitter_range)
                    time.sleep(retry_delay * jitter)
                else:
                    logger.debug(f"Button click intercepted after {retry_count} attempts")
                    return False
            except Exception as e:
                logger.error(f"Error clicking element: {e}")
                return False

        return False

    @staticmethod
    def find_button_by_text(driver, text, timeout=10):
        """
        Найти кнопку с определённым текстом.

        Args:
            driver: Selenium WebDriver instance.
            text: Текст кнопки для поиска.
            timeout: Максимальное время ожидания элемента в секундах.

        Returns:
            WebElement кнопки, если найдена, или None в противном случае.
        """
        if not text or text.strip() == "":
            logger.debug("Empty text provided for button search")
            return None

        xpath = f"//button[contains(normalize-space(text()), '{text}')]"
        return SeleniumUtilities.find_element_safely(driver, By.XPATH, xpath, timeout=timeout)





# Пример использования модуля
# try:
#     # Пример использования функций
#     button = SeleniumUtilities.find_button_by_text(driver, "Submit", timeout=10)
#     if button:
#         text = SeleniumUtilities.find_element_safely(driver, by, selector)
#         print(f"Text: {text}")
#         if SeleniumUtilities.click_safely(button):
#             print("Button clicked successfully")
# finally:
#     driver.quit()