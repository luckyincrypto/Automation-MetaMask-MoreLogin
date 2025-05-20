import time
import random

from selenium.webdriver import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (TimeoutException, ElementClickInterceptedException, NoSuchElementException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from typing import Dict, List, Optional, Any
from config import logger  # Подключение конфигурации логгера


class SeleniumUtilities:
    """
    Универсальный модуль для работы с Selenium, который можно расширять.
    """

    @staticmethod
    def open_tab(self, url):
        """Открывает новую вкладку."""
        self.driver.switch_to.new_window()
        self.driver.get(url)
        logger.debug(f"(open_tab) Открыта вкладка: {url}")

    @staticmethod
    def switch_to_new_window(driver, current_windows, timeout=15):
        """
        Ожидает появление нового окна/вкладки и переключается на него.

        Параметры:
            driver: экземпляр WebDriver
            current_windows: текущие открытые окна
            timeout: максимальное время ожидания в секундах (по умолчанию 10)

        Возвращает:
            handle нового окна
        """

        # Ждем появления нового окна
        WebDriverWait(driver, timeout).until(EC.new_window_is_opened(current_windows))

        # Получаем все окна после открытия нового
        new_windows = driver.window_handles

        # Находим handle нового окна
        new_window = list(set(new_windows) - set(current_windows))[0]

        # Переключаемся на новое окно
        driver.switch_to.window(new_window)
        return new_window

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
    def find_elements_safely(driver, by, selector, timeout=10):
        """
        Найти несколько элементов безопасно, без выброса исключений.

        Args:
            driver: Selenium WebDriver instance.
            by: Метод поиска (например, By.XPATH, By.ID).
            selector: Селектор элементов.
            timeout: Максимальное время ожидания элементов в секундах.

        Returns:
            List[WebElement], если найдены, иначе пустой список.
        """
        try:
            wait = WebDriverWait(driver, timeout)
            elements = wait.until(EC.presence_of_all_elements_located((by, selector)))
            return elements
        except TimeoutException:
            logger.debug(f"Elements '{selector}' not found after {timeout} seconds")
            return []
        except Exception as e:
            logger.error(f"Error finding elements '{selector}': {e}")
            return []


    @staticmethod
    def click_safely(element, retry_count=3, base_delay=1, jitter_range=(0.8, 1.2), exp_factor=2):
        """
        Попытка нажать на элемент с экспоненциальной задержкой при повторных попытках.

        Args:
            element: WebElement для клика
            retry_count: Количество попыток клика
            base_delay: Базовая задержка между попытками в секундах
            jitter_range: Кортеж (мин., макс.) для случайного отклонения задержки
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
                logger.debug(f" (SeleniumUtilities.click_safely), Element clicked successfully on attempt {attempt + 1}")
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

    @staticmethod
    def parse_interactive_elements(main_block) -> Dict[str, List[Dict]]:
        """Парсит блок, извлекая текст, кнопки и поля ввода с их метками."""

        def get_xpath(element) -> str:
            """Генерирует XPath для элемента (упрощенная версия)."""
            classes = element.get_attribute("class")
            element_id = element.get_attribute("id")
            if element_id:
                return f"//{element.tag_name}[@id='{element_id}']"
            if classes:
                return f"//{element.tag_name}[contains(@class, '{classes.split()[0]}')]"
            return f"//{element.tag_name}"

        result = {"elements_info": []} # Все элементы с их описанием и локатором

        if not main_block:
            logger.error("main_block is None, cannot parse elements")
            return {"elements_info": []}

        # 1. Собираем все элементы внутри main_block
        all_elements = main_block.find_elements(By.XPATH, ".//*")  # Все вложенные элементы
        if not all_elements:
            logger.warning("main_block не содержит элементов")
            return result

        for element in all_elements:

            element_info = {
                "tag_name": element.tag_name,
                "element": element,
                "text": element.text.strip() if element.text else "",
                "is_button": element.tag_name.lower() == "button",  # Является ли сам элемент кнопкой?
                "is_input_field": element.tag_name.lower() in ["input", "textarea"],
                "classes": element.get_attribute("class") or "",
                "aria_label": element.get_attribute("aria-label") or "",
                "xpath": get_xpath(element)
            }
            result["elements_info"].append(element_info)

        return result

    @staticmethod
    def find_click_button(main_block, text_btn):
        """Ищет и безопасно кликает по кнопке, выполняя повторный клик при необходимости."""
        parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)

        for el in parsed_data['elements_info']:
            try:
                if el['is_button'] and el['text'] and isinstance(el['text'], str) and text_btn in el['text'].strip():
                    if el['element'] and el['element'].is_displayed() and el['element'].is_enabled():
                        logger.debug(f"Попытка клика по кнопке с текстом: {el['text']}, XPath: {el['xpath']}")

                        if SeleniumUtilities.click_safely(el['element']):
                            logger.debug("Клик по кнопке успешен")
                            time.sleep(2)  # Подождем перед повторным кликом

                            # 🔄 Проверяем, существует ли элемент после клика
                            try:
                                el['element'] = main_block.find_element(By.XPATH, el['xpath'])
                                if el['element'].is_displayed() and el['element'].is_enabled():
                                    if SeleniumUtilities.click_safely(el['element']):
                                        logger.debug("Повторный клик успешно выполнен")
                                        return True
                                    else:
                                        logger.debug("Повторный клик не удался")
                                        return True
                            except NoSuchElementException:
                                logger.warning("Элемент исчез из DOM после первого клика, повторный клик невозможен")
                                return True
                        else:
                            raise Exception("Failed to interact with button")

                    else:
                        raise Exception("Элемент отсутствует или неактивен")
            except Exception as e:
                logger.exception(f"Ошибка при взаимодействии с кнопкой {text_btn}: {str(e)}")

    @staticmethod
    def find_input_field_click_paste(main_block, aria_label, text_input):
        """Ищет поле ввода по aria-label, кликает по нему и вставляет текст."""
        parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)

        for el in parsed_data['elements_info']:
            try:
                if el['is_input_field'] and el['element'] and el['aria_label'].strip().lower() == aria_label.lower():
                    if el['element'].is_displayed() and el['element'].is_enabled():
                        logger.debug(f"Попытка взаимодействия с полем ввода '{aria_label}', XPath: {el['xpath']}")

                        el['element'].click()
                        el['element'].clear()
                        el['element'].send_keys(text_input)

                        logger.debug(f"Текст '{text_input}' успешно введен в поле '{aria_label}'")
                        return True
                    else:
                        logger.warning(f"Поле '{aria_label}' недоступно для взаимодействия")
            except Exception as e:
                logger.exception(f"Ошибка при вводе текста в поле '{aria_label}': {str(e)}")

        return False

    # @staticmethod
    # def find_text(main_block, text_input) -> Dict[str, str]:
    #     """Парсит элементы и ищет текст, содержащий заданные слова или фразы."""
    #     parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)
    #
    #     for el in parsed_data['elements_info']:
    #         try:
    #             if el['text'] and isinstance(el['text'], str):
    #                 normalized_text = el['text'].strip().lower()
    #                 if any(word.lower() in normalized_text for word in text_input):
    #                     logger.debug(f"Найден текст '{el['text']}' по условию '{text_input}'")
    #                     return {"message": el["text"]}  # Возвращаем найденное значение полностью
    #         except Exception as e:
    #             logger.exception(f"Ошибка при поиске текста '{text_input}': {str(e)}")
    #
    #     return {"message": "Текст не найден"}

    @staticmethod
    def find_text(main_block, text_input, check_visibility=True) -> Dict[str, Any]:
        """Поиск текста с проверкой видимости элементов"""
        parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)
        logger.debug(f"Ищем текст: {text_input}")

        found_elements = []
        for el in parsed_data['elements_info']:
            try:
                if el['text'] and isinstance(el['text'], str):
                    text = el['text'].strip().lower()
                    element = el['element']

                    # Проверка видимости
                    if check_visibility and not element.is_displayed():
                        logger.warning("Элемент не виден")
                        continue

                    # Поиск совпадений
                    if any(word.lower() in text for word in text_input):
                        found_elements.append(element)
                        logger.debug(f"Найден текст '{el['text']}' по условию '{text_input}'")
            except Exception as e:
                logger.error(f"Ошибка: {str(e)}")

        return {
            "found": bool(found_elements),
            "elements": found_elements,
            "message": "Найдено совпадений: {}".format(len(found_elements)) if found_elements else "Текст не найден"
        }

    @staticmethod
    def handle_element_obstruction(driver, element):
        """Определяет, перекрыт ли нужный элемент и закрывает мешающие окна."""
        try:
            # 📌 Проверяем, не перекрыт ли элемент другим
            is_obstructed = driver.execute_script("""
                var elem = arguments[0];
                var rect = elem.getBoundingClientRect();
                var elemAtPoint = document.elementFromPoint(rect.x + rect.width/2, rect.y + rect.height/2);
                return { "obstructed": elemAtPoint !== elem, "obstructing_element": elemAtPoint.tagName, "obstructing_classes": elemAtPoint.className };
            """, element)

            logger.debug(f"Проверка перекрытия: {is_obstructed}")

            if is_obstructed["obstructed"]:
                logger.warning(f"Элемент перекрыт другим: {is_obstructed}")
                logger.warning("Ищем мешающие элементы...")

                # 📌 Ищем мешающие элементы
                obstructing_elements = driver.find_elements(By.XPATH,
                                                            "//div[contains(@class, 'popup') or contains(@class, 'modal') or contains(@class, 'overlay') or contains(@class, 'dialog') or contains(@class, 'backdrop')]")

                for obstr_elem in obstructing_elements:
                    try:
                        logger.debug(f"Попытка закрытия окна: {obstr_elem.get_attribute('class')}")

                        # 🔄 Ищем кнопку закрытия
                        close_buttons = obstr_elem.find_elements(By.XPATH,
                                                                 ".//button[contains(text(), 'Close') or contains(@class, 'close')]")
                        if close_buttons and close_buttons[0].is_displayed() and close_buttons[0].is_enabled():
                            close_buttons[0].click()
                            logger.debug("Мешающее окно закрыто!")
                            time.sleep(1)  # 🔄 Даем время на обновление страницы

                        # 📌 Если кнопка не найдена, пробуем `Esc`
                        if not close_buttons:
                            driver.send_keys(Keys.ESCAPE)
                            logger.debug("Попытка закрытия через Escape")

                        return True  # ✅ Обнаружено и закрыто

                    except Exception as e:
                        logger.warning(f"Не удалось закрыть окно: {str(e)}")

            else:
                logger.debug(f"Элемент НЕ перекрыт, можно кликнуть: {is_obstructed}")
                return False  # ✅ Перекрытия нет

        except Exception as e:
            logger.error(f"Ошибка при проверке перекрытия элемента: {str(e)}")
            return False

    @staticmethod
    def find_and_click_child_by_text(parent_element, child_text, partial_match=True):
        """
        Ищет дочерний элемент по заданному тексту внутри родительского элемента и кликает по нему.

        Параметры:
            parent_element: WebElement - родительский элемент, в котором будет производиться поиск
            child_text: str - текст для поиска в дочерних элементах
            partial_match: bool - если True, ищет частичное совпадение текста (по умолчанию True)

        Возвращает:
            bool - True, если элемент был найден и по нему кликнули, иначе False
        """
        try:
            parsed_data = SeleniumUtilities.parse_interactive_elements(parent_element)

            for el in parsed_data['elements_info']:
                try:
                    if el['text'] and isinstance(el['text'], str):
                        element_text = el['text'].strip()
                        text_match = (child_text.lower() in element_text.lower()) if partial_match \
                            else (child_text.lower() == element_text.lower())

                        if text_match and el['element'].is_displayed() and el['element'].is_enabled():
                            logger.debug(f"Найден элемент с текстом: '{element_text}'. Попытка клика...")

                            if SeleniumUtilities.click_safely(el['element']):
                                logger.debug(f"Успешный клик по элементу с текстом: '{element_text}'")
                                return True
                            else:
                                logger.warning(f"Не удалось кликнуть по элементу с текстом: '{element_text}'")
                except Exception as e:
                    logger.exception(f"Ошибка при обработке элемента: {str(e)}")
                    continue

            logger.warning(f"Не найден кликабельный элемент с текстом: '{child_text}'")
            return False

        except Exception as e:
            logger.exception(f"Ошибка в find_and_click_child_by_text: {str(e)}")
            return False