import time
import random
from pprint import pprint

from selenium.webdriver import Keys
from selenium.webdriver.remote.webelement import WebElement
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
    def switch_to_new_window(driver, current_windows, timeout=10):
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
        new_window_handles = list(set(new_windows) - set(current_windows))
        if new_window_handles:
            new_window = new_window_handles[-1]
            logger.debug(f' (switch_to_new_window), Переключаемся на новое окно: {new_window}')
            driver.switch_to.window(new_window)
            return new_window
        else:
            logger.error(' (switch_to_new_window), Новое окно не найдено')
            return None

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
            logger.debug(f" (SeleniumUtilities.find_element_safely), Element: '{selector}' not found after {timeout} seconds")
            return None
        except Exception as e:
            logger.error(f" (SeleniumUtilities.find_element_safely), Error finding element '{selector}': {e}")
            return None

    @staticmethod
    def find_elements_safely(driver, by, selector, timeout=15) -> list:
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
            if elements:
                return elements
            return []
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
                logger.debug(
                    f" (SeleniumUtilities.click_safely), Element clicked successfully on attempt {attempt + 1}")
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

        result = {"elements_info": []}  # Все элементы с их описанием и локатором

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
                # "text": element.text,
                "is_button": element.tag_name.lower() == "button",  # Является ли сам элемент кнопкой?
                "is_input_field": element.tag_name.lower() in ["input", "textarea"],
                "classes": element.get_attribute("class") or "",
                "aria_label": element.get_attribute("aria-label") or "",
                # "xpath": get_xpath(element)
            }
            result["elements_info"].append(element_info)

        return result

    @staticmethod
    def find_button_recursively(element, text_btn, max_depth=10, current_depth=0):
        """
        Рекурсивно ищет кнопку с точным текстом во вложенных элементах.

        Args:
            element: WebElement - элемент для поиска
            text_btn: str - текст кнопки для поиска
            max_depth: int - максимальная глубина вложенности
            current_depth: int - текущая глубина вложенности

        Returns:
            tuple: (WebElement, int) - найденный элемент и глубина, на которой он был найден, или (None, -1)
        """
        if current_depth >= max_depth:
            logger.debug(f"Достигнута максимальная глубина поиска ({max_depth})")
            return None, -1

        try:
            # Ищем все кнопки с точным текстом в текущем элементе
            buttons = element.find_elements(By.XPATH, f".//button[normalize-space(text())='{text_btn}']")
            if buttons:
                for button in buttons:
                    if button.is_displayed() and button.is_enabled():
                        logger.debug(f"Найдена кнопка '{text_btn}' на глубине {current_depth}")
                        return button, current_depth

            # Если кнопка не найдена, ищем во всех дочерних элементах
            children = element.find_elements(By.XPATH, "./*")
            logger.debug(f"Найдено {len(children)} дочерних элементов на глубине {current_depth}")

            for child in children:
                result, depth = SeleniumUtilities.find_button_recursively(
                    child, text_btn, max_depth, current_depth + 1
                )
                if result:
                    return result, depth

        except Exception as e:
            logger.debug(f"Ошибка при поиске на глубине {current_depth}: {str(e)}")

        return None, -1

    @staticmethod
    def find_click_button(main_block, text_btn, check_visibility=True):
        """Ищет и безопасно кликает по кнопке, выполняя поиск во вложенных элементах."""
        number_of_symbols = (len(text_btn))  # подсчет количества символов в строковой переменной
        try:
            logger.debug(f" (find_click_button), Начинаем поиск кнопки с текстом: '{text_btn}'")
            parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)

            for element_info in parsed_data['elements_info']:
                if element_info['is_button'] and element_info['text'][:number_of_symbols] == text_btn:
                    button = element_info['element']

                    # Проверка видимости
                    if check_visibility and not button.is_displayed():
                        continue

                    if SeleniumUtilities.click_safely(button):
                        logger.debug(f" (find_click_button), Успешный клик по кнопке '{text_btn}'")
                        return True

            logger.warning(f" (find_click_button), Не найдена кнопка с текстом: '{text_btn}'")
            return False

        except Exception as e:
            logger.exception(f"Ошибка в find_click_button: {str(e)}")
            return False

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

    @staticmethod
    def find_text(main_block, text_input, check_visibility=True) -> Dict[str, Any]:
        """Поиск текста с проверкой видимости элементов"""
        parsed_data = SeleniumUtilities.parse_interactive_elements(main_block)
        # logger.debug(f"Ищем текст: {text_input}")

        found_elements = []

        for el in parsed_data['elements_info']:
            try:
                if el['text'] and isinstance(el['text'], str):
                    text = el['text'].strip().lower()
                    # logger.debug(f' (SeleniumUtilities.find_text), text: {text}')
                    element = el['element']

                    # Проверка видимости
                    if check_visibility and not element.is_displayed():
                        continue

                    # Поиск совпадений
                    if any(word.lower() in text for word in text_input):
                        found_elements.append(element)
                        # Логируем только первое найденное совпадение
                        if len(found_elements) == 1:
                            logger.info(f"Найден текст '{el['text']}' по условию'")
                        break  # Прерываем поиск после первого совпадения
            except Exception as e:
                logger.error(f"Ошибка: {str(e)}")

        return {"elements": found_elements}

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
            # Ищем все дочерние элементы внутри родительского элемента
            child_elements = parent_element.find_elements(By.XPATH, ".//*")

            for child in child_elements:
                try:
                    if child.text and isinstance(child.text, str):
                        element_text = child.text.strip()

                        # Проверяем точное совпадение с MetaMask
                        if child_text.lower() == element_text.lower():
                        # if child_text.lower() == "metamask" and element_text.lower() == "metamask":
                            if child.is_displayed() and child.is_enabled():
                                logger.debug(f" (find_and_click_child_by_text), Найден элемент с текстом: '{element_text}'. Попытка клика...")

                                if SeleniumUtilities.click_safely(child):
                                    logger.debug(f" (find_and_click_child_by_text), Успешный клик по элементу с текстом: '{element_text}'")
                                    return True
                                else:
                                    logger.warning(f" (find_and_click_child_by_text), Не удалось кликнуть по элементу с текстом: '{element_text}'")
                            break

                        # Для других случаев используем обычную логику
                        elif child_text.lower() != element_text.lower():
                        # elif child_text.lower() != "metamask":
                            text_match = (child_text.lower() in element_text.lower()) if partial_match \
                                else (child_text.lower() == element_text.lower())

                            if text_match and child.is_displayed() and child.is_enabled():
                                logger.debug(f" (find_and_click_child_by_text), Найден элемент с текстом: '{element_text}'. Попытка клика...")

                                if SeleniumUtilities.click_safely(child):
                                    logger.debug(f" (find_and_click_child_by_text), Успешный клик по элементу с текстом: '{element_text}'")
                                    return True
                                else:
                                    logger.warning(f" (find_and_click_child_by_text), Не удалось кликнуть по элементу с текстом: '{element_text}'")
                                break

                except Exception as e:
                    logger.exception(f" (find_and_click_child_by_text), Ошибка при обработке элемента: {str(e)}")
                    continue

            logger.warning(f" (find_and_click_child_by_text), Не найден кликабельный элемент с текстом: '{child_text}'")
            return False

        except Exception as e:
            logger.exception(f" (find_and_click_child_by_text), Ошибка в find_and_click_child_by_text: {str(e)}")
            return False

    @staticmethod
    def find_which_selector(driver, by, selectors, timeout):
        for selector in selectors:
            logger.debug(f' (SeleniumUtilities.find_which_selector), Проверяем селектор: {selector}')
            selector_element = SeleniumUtilities.find_element_safely(driver, by, selector, timeout)
            if selector_element:
                logger.debug(f' (SeleniumUtilities.find_which_selector), Найден элемент, type: {selector_element.get_attribute('type')} по селектору: {selector}')
                return selector_element
            logger.debug(f' (SeleniumUtilities.find_which_selector), Элемента не найдено по данному селектору: {selector}')
        logger.debug(f' (SeleniumUtilities.find_which_selector), Элементов не найдено по данным селекторам')
        return None

    @staticmethod
    def fill_field(driver, locator, value):
        element = SeleniumUtilities.find_element_safely(driver, *locator)
        if element:
            element.clear()
            element.send_keys(value)
            if element.get_attribute("value") == value:
                logger.debug(f" (_fill_field), Вставка значения: {value} успешна")
                return True
        return False

    @staticmethod
    def get_element_attributes(driver, element) -> Dict[str, str]:
        """
        Получает все атрибуты указанного элемента.
        Args:
            driver (WebDriver): Экземпляр Selenium WebDriver.
            element (WebElement): Целевой элемент, у которого нужно получить атрибуты.
        Returns:
            Dict[str, str]: Словарь с названиями атрибутов и их значениями.
        Example:
            attributes = get_element_attributes(driver, some_element)
            print(attributes)
        """

        # Выполняем JavaScript для извлечения списка названий атрибутов
        attribute_names = driver.execute_script(
            "return arguments[0].getAttributeNames();", element
        )

        # Получаем значения атрибутов и формируем словарь
        attributes = {attr_name: element.get_attribute(attr_name) for attr_name in attribute_names}

        return attributes


    @staticmethod
    def get_elements(driver, class_names: str) -> List[str]:
        """
        Ищет все элементы с заданными классами и возвращает список элементов.
        :param driver: Экземпляр Selenium WebDriver.
        :param class_names: Строка с классами, разделёнными пробелами (например, "max-w-44 w-fit min-w-10 truncate").
        :return: Список найденных элементов.
        """
        class_selector = "." + ".".join(class_names.split())  # Преобразуем строку классов в CSS-селектор
        logger.debug(f' (SeleniumUtilities.get_elements), Преобразуем строку классов в CSS-селектор -> class_selector: {class_selector}')
        elements = SeleniumUtilities.find_elements_safely(driver, By.CSS_SELECTOR, class_selector)  # Находим элементы
        return [el for el in elements]  # Получаем список элементов


    @staticmethod
    def get_element(driver, class_names: str) -> WebElement:
        """
        Ищет элемент с заданными классами и возвращает его.
        :param driver: Экземпляр Selenium WebDriver.
        :param class_names: Строка с классами, разделёнными пробелами (например, "max-w-44 w-fit min-w-10 truncate").
        :return: Элемент с заданными классами.
        """
        class_selector = "." + ".".join(class_names.split())  # Преобразуем строку классов в CSS-селектор
        element = SeleniumUtilities.find_element_safely(driver, By.CSS_SELECTOR, class_selector)  # Находим элементы
        return element # Получаем 1 элемент

