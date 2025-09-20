from datetime import datetime, timedelta
import random
from config import MIN_WAIT_TIME_BETWEEN_SWAP, MAX_WAIT_TIME_BETWEEN_SWAP
import re
import time
from pprint import pprint

# Работа с типами данных
from typing import Dict, Any, Optional, Tuple, List

# Работа с URL
from urllib.parse import urlparse, parse_qs, urlencode

# Selenium
from selenium.common import WebDriverException, NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import title_contains
from selenium.webdriver.support.wait import WebDriverWait

# Внешние зависимости проекта
from meta_mask import MetaMaskHelper, compare_addresses
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger
from utils import adjust_window_position, random_number_for_sell

toket_address_list = [
'0xf817257fed379853cDe0fa4F97AB987181B1E5Ea',
'0x3a98250F98Dd388C211206983453837C8365BDc1',
'0xfe140e1dce99be9f4f15d657cd9b7bf622270c50',
'0xe0590015a873bf326bd645c3e1266d4db41c4e6b',
'0x0f0bdebf0f83cd1ee3974779bcb7315f9808c714',
'0xb5a30b0fdc5ea94a52fdc42e3e9760cb8449fb37',
# '0xcf5a6076cfa32686c0df13abada2b40dec133f1d',  # WBTC
'0xabd7afa2161eb7254c0a9dbb5fe79216b7c28e03',
# '0x39e95286dd43f8da34cbda8e4b656da9f53ca644',  #AXO
'0x743cef7ccc8ac56605c8404607142e5b35efa11d',
'0x268e4e24e0051ec27b3d27a95977e71ce6875a05',
'0x4c10428ed0410dfb2de62fc007f7c1105ae861e9',
'0x2bb4219b8e85c111613f3ee192a115676f230d35',
'0x8507f576eb214d172012065d58cfb38a4540b0a6',
'0x859fb36f3fe7e22b37dd99b501f891377ddc9c33',
'0x53abd7e17c8939558bfa80a721e01633a3ef9d5c',
]


def extract_swap_addresses(url: str) -> List[str]:
    """
    Извлекает из URL параметры `from=` и `to=` в виде списка.

    Параметры:
        url (str): Исходный URL.

    Возвращает:
        List[str]: [from_token, to_token] если оба параметра присутствуют, иначе пустой список.
    """
    parsed_url = urlparse(url)  # Разбираем URL
    params = parse_qs(parsed_url.query)  # Извлекаем параметры запроса

    if "from" in params and "to" in params:  # Проверяем наличие параметров
        return [params["from"][0], params["to"][0]]  # Возвращаем список с адресами

    return []  # Если параметры отсутствуют, возвращаем пустой список


def normalize_value(value_str: str) -> str:
    original_value = value_str
    value_str = value_str.replace(',', '').strip()

    # Карта нижних индексов
    subscript_map = {
        '₀': '0', '₁': '1', '₂': '2', '₃': '3', '₄': '4',
        '₅': '5', '₆': '6', '₇': '7', '₈': '8', '₉': '9'
    }

    # Преобразуем нижние индексы в обычные цифры
    def convert_subscripts(s):
        return ''.join(subscript_map.get(char, char) for char in s)

    value_str = convert_subscripts(value_str)

    # Обработка специального формата: 0.0ₙXYZ → 0. + n нулей + XYZ
    match = re.match(r'^0\.0(\d)(\d+)$', value_str)
    if match:
        zero_count = int(match.group(1))
        rest = match.group(2)
        cleaned_value = f"0.{''.join(['0'] * zero_count)}{rest}"
        logger.debug(f"(normalize_value), Специальный формат: '{original_value}' → '{cleaned_value}'")
        return cleaned_value

    # Обработка суффиксов K, M, B
    multiplier = 1
    suffix_match = re.search(r'([KMB])$', value_str.upper())
    if suffix_match:
        suffix = suffix_match.group(1)
        if suffix == 'K':
            multiplier = 1_000
        elif suffix == 'M':
            multiplier = 1_000_000
        elif suffix == 'B':
            multiplier = 1_000_000_000
        value_str = value_str[:-1]

    # Удаляем всё лишнее кроме цифр и точки
    cleaned_value = re.sub(r'[^\d\.]', '', value_str)

    # Защита от ложных преобразований: если cleaned_value уже валидное число, не трогаем
    if re.fullmatch(r'\d+(\.\d+)?', cleaned_value):
        try:
            normalized = float(cleaned_value) * multiplier
            logger.debug(f"(normalize_value), Исходное: '{original_value}' → '{normalized}'")
            return str(normalized)
        except ValueError:
            logger.error(f"(normalize_value), Ошибка преобразования: '{cleaned_value}' из '{original_value}'")
            return original_value

    # Если не удалось распознать — возвращаем исходное
    logger.warning(f"(normalize_value), Не удалось интерпретировать: '{original_value}'")
    return original_value


class KuruSwap:
    """Класс для работы с Kuru Swap"""


    # Селекторы для поиска элементов
    WALLET_SELECTORS = [
        '//button[contains(text(), "Connect wallet")]'
        # 'button[data-sentry-element="DialogTrigger"]',  # Connect wallet button
        # 'div[data-sentry-element="SheetTrigger"]',  # Wallet connected already
    ]

    TOKEN_SELECTORS = {
        # 'symbol': "max-w-44 w-fit min-w-10 truncate",
        'balance': "flex items-center space-x-2 visible",
        }

    def __init__(self, driver):
        """
        Инициализация KuruSwap.

        Args:
            driver: WebDriver - экземпляр драйвера
        """
        self.current_url = None
        self.driver = driver
        self.metamask = MetaMaskHelper(driver)


    def open_website(self, from_token='0x0000000000000000000000000000000000000000',
                     to_token='0xf817257fed379853cDe0fa4F97AB987181B1E5Ea') -> bool:
        """
        Открывает сайт Kuru Swap с заданными параметрами `from_token` и `to_token`.

        Параметры:
            from_token (str): Адрес токена, с которого меняют.
            to_token (str): Адрес токена, на который меняют.

        Returns:
            bool: True если сайт успешно открыт, False в случае ошибки.
        """
        BASE_URL = f'https://www.kuru.io/swap?from={from_token}&to={to_token}'

        try:
            logger.info(f'Opening website: {BASE_URL}')
            self.driver.get(BASE_URL)

            # Ожидание загрузки страницы вместо time.sleep
            WebDriverWait(self.driver, 10).until(title_contains("Kuru"))

            logger.info('Website opened successfully')
            return True

        except WebDriverException as e:
            logger.error(f'WebDriver error: {str(e)}')
            return False

        except Exception as e:
            logger.error(f'Unexpected error while opening website: {str(e)}')
            return False

    def connect_wallet(self, mm_address: str) -> bool:
        """
        Подключает кошелек к сайту.

        Args:
            mm_address: str - ожидаемый адрес кошелька

        Returns:
            bool: True если кошелек успешно подключен, False в противном случае
        """
        try:
            while True:
                time.sleep(3)
                element = SeleniumUtilities.find_which_selector(
                    self.driver,
                    By.XPATH,
                    self.WALLET_SELECTORS,
                    timeout=5
                )

                if not element:
                    logger.error("Не удалось найти элементы подключения кошелька: By.CSS_SELECTOR, self.WALLET_SELECTORS")
                    # return False

                    element = SeleniumUtilities.find_element_safely(self.driver, By.CLASS_NAME, 'ml-1', timeout=3)
                    if not element:
                        logger.error(
                            "Не удалось найти элементы подключения кошелька: By.CLASS_NAME, 'ml-1'")
                        return False

                text_in_element = element.text
                logger.debug(f'Found element text: {text_in_element}')

                if text_in_element == 'Connect wallet':
                    if not self._handle_connect_wallet_click(element):
                        return False
                else:
                    if compare_addresses(mm_address, text_in_element):
                        logger.info(f'MetaMask address {mm_address} connected to site: https://www.kuru.io/')
                        return True

        except Exception as e:
            logger.error(f'Error connecting wallet: {str(e)}')
            return False

    def _handle_connect_wallet_click(self, element) -> bool:
        """
        Обрабатывает клик по кнопке подключения кошелька.

        Args:
            element: WebElement - элемент кнопки подключения

        Returns:
            bool: True если подключение успешно, False в противном случае
        """
        try:
            element.click()
            logger.debug('Clicked on <Connect wallet> button')

            time.sleep(3)
            dialog_block = SeleniumUtilities.find_element_safely(
                self.driver,
                By.XPATH,
                "//div[@role='dialog']",
                timeout=5
            )

            if not dialog_block:
                logger.error("Dialog block not found")
                return False

            current_windows = self.driver.window_handles
            logger.debug(f'Current windows: {current_windows}')

            if not SeleniumUtilities.find_and_click_child_by_text(dialog_block, 'MetaMask', partial_match=False):
                logger.error("Failed to click MetaMask button")
                return False

            new_window = SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
            if not new_window:
                logger.error("Failed to switch to new window")
                return False

            adjust_window_position(self.driver)

            if not self.metamask.handle_metamask_connection(self.driver):
                logger.error("Failed to complete MetaMask connection")
                return False

            self.driver.switch_to.window(current_windows[-1])
            logger.info("Connection completed successfully")
            return True

        except Exception as e:
            logger.error(f'Error handling connect wallet click: {str(e)}')
            return False

    def get_token_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает информацию о токенах для свопа.

        Returns:
            Dict[str, Dict[str, Any]]: Информация о токенах в формате:
            {
                'selling_token': {
                    'symbol': str,
                    'number_tokens': float,
                },
                'buying_token': {
                    'symbol': str,
                    'number_tokens': float
                },
                'element_refresh': WebElement  # Элемент для обновления котировки
            }
        """
        while True:
            try:

                time.sleep(3)
                token_exist = {'selling_token': {}, 'buying_token': {}}
                class_path = 'w-max'
                els_symbol_list = SeleniumUtilities.find_elements_safely(
                    self.driver,
                    By.CLASS_NAME,
                    class_path
                )

                logger.debug(f' (get_token_info), Found token symbols: {els_symbol_list[0].text.strip()}, and: {els_symbol_list[2].text.strip()}')

                selling_symbol = token_exist['selling_token']['symbol'] = els_symbol_list[0].text.strip()
                buying_symbol = token_exist['buying_token']['symbol'] = els_symbol_list[2].text.strip()

                # Получаем балансы токенов и элемент обновления
                def extract_token_values(driver):
                    results  = []
                    time.sleep(5)
                    blocks = SeleniumUtilities.get_elements(driver, 'flex items-center space-x-2 visible')

                    if blocks:
                        logger.debug(f"(get_token_info), Найдено блоков: {len(blocks)}")

                    for block in blocks:
                        # Проверка наличия <span>
                        try:
                            span_element = block.find_element(By.TAG_NAME, 'span')
                            span_value = normalize_value(span_element.text.strip())
                        except NoSuchElementException:
                            logger.error(f" (get_token_info, extract_token_values), Не найден <span> в блоке")
                            continue

                        # Проверка наличия <div class="max-w-16 truncate undefined">
                        try:
                            token_element = block.find_element(
                                By.XPATH, './/div[@class="max-w-16 truncate undefined"]'
                            )
                            token_name = token_element.text.strip()
                        except NoSuchElementException:
                            logger.error(f" (get_token_info, extract_token_values), Не найден криптовалютный тикер (truncate)")
                            continue
                        results .append((token_name, span_value))

                    return results

                # Пример использования
                els_info_list = extract_token_values(self.driver)
                logger.debug(f"(get_token_info), Результат парсинга: {els_info_list}")

                number_tokens_selling = els_info_list[0][1]
                logger.debug(f"(get_token_info), number_tokens_selling: {number_tokens_selling}")
                number_tokens_buying = els_info_list[1][1]
                logger.debug(f'(get_token_info), number_tokens_buying: {number_tokens_buying}')

                # Проверка наличия токенов
                number_tokens_selling = float(number_tokens_selling.replace(',', '') if number_tokens_selling not in [None, 0, '0'] else 0.0)
                token_exist.setdefault('selling_token', {})['number_tokens'] = number_tokens_selling

                if number_tokens_selling == 0.0000:
                    logger.info(f" (get_token_info), Токенов {selling_symbol} в кошельке нет")
                else:
                    logger.info(f' (get_token_info), Токены есть в кошельке, можно продать: {number_tokens_selling} {selling_symbol}')

                # Обработка баланса buying token. Проверяем наличие данных и корректно преобразуем в float
                number_tokens_buying = float(number_tokens_buying.replace(',', '') if number_tokens_buying not in [None, 0, '0'] else 0.0)

                # Безопасное присваивание в `token_exist`
                token_exist.setdefault('buying_token', {})['number_tokens'] = number_tokens_buying

                # Логирование результата
                if number_tokens_buying == 0.0000:
                    logger.info(f" (get_token_info), Токенов {buying_symbol} в кошельке нет")
                else:
                    logger.info(f' (get_token_info), Токены есть в кошельке, можно продать: {number_tokens_buying} {buying_symbol}')

                return token_exist

            except Exception as e:
                logger.error(f' (get_token_info), Error getting token info: {str(e)}')
                continue
                # return {'selling_token': {}, 'buying_token': {}}

    def input_number_for_sell(self, number):
        css_selector_selling = 'input[placeholder]'
        # css_selector_selling = '.app-container div.space-y-2 input'
        elements_input = SeleniumUtilities.find_elements_safely(self.driver, By.CSS_SELECTOR, css_selector_selling)
        if elements_input[0]:
            elements_input[0].clear()
            if elements_input[0].send_keys(number):
                logger.debug(f" (input_number_for_sell), Вставка значения: {number} успешна")
                time.sleep(3)
                logger.debug(
                    f" (input_number_for_sell),  elements_input[0]: {elements_input[0].get_attribute('value')}")
        else:
            logger.error("Не удалось найти элементы для ввода числа 1")
        time.sleep(3)
        elements_input = SeleniumUtilities.find_elements_safely(self.driver, By.CSS_SELECTOR, css_selector_selling)
        text_button = 'Swap'
        element_btn = SeleniumUtilities.find_button_by_text(self.driver, text_button)
        if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
            if elements_input[1]:
                logger.debug(f" (input_number_for_sell),  elements_input[1]: {elements_input[1].get_attribute('value')}")

                quantity_will_purchase = elements_input[1].get_attribute('value')
                logger.info(f' (input_number_for_sell), При продаже: {number}, получим: {quantity_will_purchase}')
                return quantity_will_purchase
            else:
                logger.error(f' (input_number_for_sell), Не удалось найти элемент для ввода 2')

        else:
            logger.error("Элемент не найден или недоступен для нажатия")
            return False

    def swap(self, token_info_swap: Dict[str, Dict[str, Any]]):
        number_tokens_selling = token_info_swap['selling_token']['number_tokens']
        selling_symbol = token_info_swap['selling_token']['symbol']

        quantity_for_sale = token_info_swap['selling_token']['quantity_for_sale'] = random_number_for_sell(
            selling_symbol, number_tokens_selling
        )
        quantity_will_purchase = self.input_number_for_sell(quantity_for_sale)
        if not quantity_will_purchase:
            logger.error(" (swap), Failed to input number for sell")
            return False

        window_kuru = self.driver.current_window_handle
        logger.debug(f' (swap), Current opened Kuru tab: {window_kuru}')
        current_windows = self.driver.window_handles
        logger.debug(f' (swap), Current opened tabs: {current_windows}')

        token_info_swap['buying_token']['quantity_will_purchase'] = quantity_will_purchase

        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            logger.debug(f' (KuruSwap.swap), Attempt swap №: {attempt}')
            time.sleep(3)

            text_button = 'Swap'
            element_btn = SeleniumUtilities.find_button_by_text(self.driver, text_button, timeout=20)
            if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
                if not SeleniumUtilities.click_safely(element_btn):
                    logger.error(" (swap), Failed to click button <Swap>")
                    time.sleep(2)
                    continue

                # Обработка окон MetaMask
                confirmation_count = 0
                max_confirmations = 2  # Максимум 2 подтверждения

                while confirmation_count < max_confirmations:
                    # Ждем появления нового окна
                    new_window_mm = None
                    try:
                        # Ожидаем появления нового окна в течение 30 секунд
                        WebDriverWait(self.driver, 30).until(
                            lambda driver: len(driver.window_handles) > len(current_windows)
                        )
                        # Находим новое окно
                        new_windows = [window for window in self.driver.window_handles if window not in current_windows]
                        if new_windows:
                            new_window_mm = new_windows[0]
                            self.driver.switch_to.window(new_window_mm)
                            logger.debug(f' (swap), New tab MetaMask is opened: {new_window_mm}')
                        else:
                            break
                    except:
                        logger.debug("No new MetaMask window appeared")
                        break

                    # Пытаемся найти и нажать кнопку Confirm в MetaMask
                    text_btn = 'Confirm'
                    try:
                        button_element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
                        if button_element:
                            button_element.click()
                            logger.debug(f" (swap), MetaMask tab. Clicked button {text_btn} successfully")
                            confirmation_count += 1

                            # Закрываем окно MetaMask после подтверждения
                            self.driver.close()
                            self.driver.switch_to.window(window_kuru)
                            current_windows = self.driver.window_handles
                    except:
                        logger.error(f" (swap), Could not find or click {text_btn} button in MetaMask")
                        self.driver.close()
                        self.driver.switch_to.window(window_kuru)
                        break

                    # Небольшая пауза между подтверждениями
                    time.sleep(2)

                if confirmation_count > 0:
                    logger.info(f"Successfully processed {confirmation_count} MetaMask confirmations")
                    return True
                else:
                    logger.error("No MetaMask confirmations were processed")
                    continue

        logger.error(" (swap), Max swap attempts reached")
        return False



# Заменяем функцию kuru() на новую реализацию
def kuru(driver, mm_address):
    """
    Основная функция для работы с Kuru Swap.

    Args:
        driver: WebDriver - экземпляр драйвера
        mm_address: str - адрес кошелька MetaMask

    Returns:
        Dict[str, Any]: Результат операции с обязательными полями
    """
    # global next_attempt, result_data
    try:
        # Создаем экземпляр класса для работы с Kuru Swap
        kuru_swap = KuruSwap(driver)
        result_data = {
            'activity_type': 'Kuru_Swap',
            'status': 'error',
            'wallet_address': mm_address,
            'next_attempt': None,
            'details': {}
        }

        # Открываем сайт
        random_address = random.choice(toket_address_list)
        logger.debug(f"Случайный токен: {random_address}")

        if not kuru_swap.open_website(to_token=random_address):
            logger.error("Failed to open website Kuru")
            result_data['details'] = {'error': 'Failed to open website'}
            return result_data

        # Подключаем кошелек
        if not kuru_swap.connect_wallet(mm_address):
            logger.error("Failed to connect MetaMask wallet")
            result_data['details'] = {'error': 'Failed to connect wallet'}
            return result_data

        # Получаем информацию по токенам до первого свапа
        token_info_before_swap = kuru_swap.get_token_info()
        if not token_info_before_swap:
            logger.error("Failed to get initial token info")
            result_data['details'] = {'error': 'Failed to get initial token info'}
            return result_data

        # Первый свап (продажа MON или другого токена)
        first_swap_details = {}
        if token_info_before_swap['selling_token']['number_tokens'] > 0.2 and \
                token_info_before_swap['selling_token']['symbol'].lower() == 'mon':

            if not kuru_swap.swap(token_info_before_swap):
                logger.error(f"Failed to swap {token_info_before_swap['selling_token']['symbol']} tokens")
                result_data['details'] = {'error': f'First swap failed: from: {token_info_before_swap["selling_token"]["symbol"]} to: {token_info_before_swap["buying_token"]["symbol"]}'}
                # Sent to Telegram
                return result_data
            # Sent to Telegram
            logger.info(f'First swap successful,\n'
                        f' from: {token_info_before_swap["selling_token"]["symbol"]} to: {token_info_before_swap["buying_token"]["symbol"]}')

            # Получаем информацию после первого свапа
            token_info_after_swap = kuru_swap.get_token_info()
            if not token_info_after_swap:
                logger.error("Failed to get token info after first swap")
                result_data['details'] = {'error': 'Failed to get token info after first swap'}
                # Sent to Telegram
                return result_data

            # Вычисляем изменения после первого свапа
            sold_tokens = token_info_before_swap['selling_token']['number_tokens'] - \
                          token_info_after_swap['selling_token']['number_tokens']

            bought_tokens = token_info_after_swap['buying_token']['number_tokens'] - \
                            token_info_before_swap['buying_token']['number_tokens']

            logger.info(f'First swap: \n'
                        f'Продано токенов: {sold_tokens} {token_info_before_swap['selling_token']['symbol']} tokens\n'
                        f'Куплено токенов: {bought_tokens} {token_info_after_swap['buying_token']['symbol']} tokens')

            first_swap_details = {
                'first_swap': {
                    'sold_before_after': f'{token_info_before_swap["selling_token"]["number_tokens"]} - {token_info_after_swap["selling_token"]["number_tokens"]}',
                    'sold_tokens_symbol': f'{sold_tokens} {token_info_before_swap["selling_token"]["symbol"]}',
                    'bought_before_after': f'{token_info_before_swap["buying_token"]["number_tokens"]} - {token_info_after_swap["buying_token"]["number_tokens"]}',
                    'bought_tokens_symbol': f'{bought_tokens} {token_info_after_swap["buying_token"]["symbol"]}',
                }
            }
            # Sent to Telegram

            # Подготовка к обратному свапу
            url_name_swap = driver.current_url
            list_addresses = extract_swap_addresses(url_name_swap)
            if len(list_addresses) != 2:
                logger.error("Failed to extract token addresses from URL")
                result_data['details'] = {**first_swap_details, 'error': 'Failed to extract token addresses from URL'}
                return result_data

            token_from, token_to = list_addresses

            # Открываем страницу для обратного свапа
            if not kuru_swap.open_website(from_token=token_to, to_token=token_from):
                logger.error("Failed to open reverse swap page")
                result_data['details'] = {**first_swap_details, 'error': 'Failed to open reverse swap page'}
                return result_data

            # Подключаем кошелек
            if not kuru_swap.connect_wallet(mm_address):
                logger.error("Failed to connect MetaMask wallet")
                result_data['details'] = {'error': 'Failed to connect wallet'}
                return result_data

            # Получаем информацию для обратного свапа
            time.sleep(3)
            token_info_before_reverse_swap = kuru_swap.get_token_info()
            if not token_info_before_reverse_swap:
                logger.error("Failed to get token info for reverse swap")
                result_data['details'] = {**first_swap_details, 'error': 'Failed to connect wallet'}
                return result_data

            # Выполняем обратный свап
            max_attempts = 5
            attempt = 0
            while attempt < max_attempts:
                attempt += 1
                logger.debug(f'Attempt for reverse swap №: {attempt}')
                time.sleep(3)

                if not kuru_swap.swap(token_info_before_reverse_swap):
                    logger.error(
                        f"Failed to reverse swap {token_info_before_reverse_swap['selling_token']['symbol']} tokens")
                    continue
                logger.info(f'Reverse swap successful,\n'
                            f' from: {token_info_before_reverse_swap["selling_token"]["symbol"]} to: {token_info_before_reverse_swap["buying_token"]["symbol"]}')
                # Sent to Telegram

                # Получаем финальную информацию после обратного свапа
                driver.refresh()
                time.sleep(3)
                token_info_after_reverse_swap = kuru_swap.get_token_info()
                if not token_info_after_reverse_swap:
                    logger.error("Failed to get token info after reverse swap")
                    result_data['details'] = {**first_swap_details, 'error': 'Failed to get token info after reverse swap'}
                    # Sent to Telegram
                    return result_data

                # Вычисляем изменения после обратного свапа
                reverse_sold_tokens = token_info_before_reverse_swap['selling_token']['number_tokens'] - \
                                      token_info_after_reverse_swap['selling_token']['number_tokens']

                reverse_bought_tokens = token_info_after_reverse_swap['buying_token']['number_tokens'] - \
                                        token_info_before_reverse_swap['buying_token']['number_tokens']
                logger.info(
                    f'Обратный свап. Продано токенов: {reverse_sold_tokens} {token_info_before_reverse_swap['selling_token']['symbol']} tokens')
                logger.info(f'Обратный свап. Куплено токенов: {reverse_bought_tokens} {token_info_after_reverse_swap['buying_token']['symbol']} tokens')
                # Sent to Telegram

                # Проверяем, что свапы были успешными
                if (token_info_before_swap['selling_token']['number_tokens'] >
                        token_info_after_swap['selling_token']['number_tokens'] and
                        token_info_before_swap['buying_token']['number_tokens'] <
                        token_info_after_swap['buying_token']['number_tokens'] and
                        token_info_before_reverse_swap['selling_token']['number_tokens'] >
                        token_info_after_reverse_swap['selling_token']['number_tokens'] and
                        token_info_before_reverse_swap['buying_token']['number_tokens'] <
                        token_info_after_reverse_swap['buying_token']['number_tokens']):
                    # Успешное выполнение
                    wait_minutes = random.randint(MIN_WAIT_TIME_BETWEEN_SWAP, MAX_WAIT_TIME_BETWEEN_SWAP)
                    next_attempt = (datetime.now() + timedelta(minutes=wait_minutes)).strftime("%Y-%m-%d %H:%M:%S")

                    result_data.update({
                        'status': 'success',
                        'next_attempt': next_attempt,
                        'details': {
                            **first_swap_details,
                            'second_swap': {
                                'sold_before_after': f'{token_info_before_reverse_swap["selling_token"]["number_tokens"]} - {token_info_after_reverse_swap["selling_token"]["number_tokens"]}',
                                'sold_tokens_symbol': f'{reverse_sold_tokens} {token_info_before_reverse_swap["selling_token"]["symbol"]}',
                                'bought_before_after': f'{token_info_before_reverse_swap["buying_token"]["number_tokens"]} - {token_info_after_reverse_swap["buying_token"]["number_tokens"]}',
                                'bought_tokens_symbol': f'{reverse_bought_tokens} {token_info_after_reverse_swap["buying_token"]["symbol"]}',
                            }
                        }
                    })
                    return result_data
                else:
                    logger.error(f"Swap completed but token amounts didn't change as expected. Attempt for reverse swap №: {attempt}")
                    result_data['details'] = {'error': f'Swap completed but token amounts didn\'t change as expected, Attempt for reverse swap №: {attempt}'}
                    continue

            # Если не удалось выполнить обратный свап после всех попыток
            next_attempt = (datetime.now() + timedelta(minutes=10)).strftime("%Y-%m-%d %H:%M:%S")
            result_data.update({
                'status': 'error',
                'next_attempt': next_attempt,
                'details': {**first_swap_details, 'error': 'Reverse swap failed after max attempts'}
            })
            return result_data


        else:
            logger.error("No tokens to swap or insufficient balance")
            result_data['details'] = {'error': 'No tokens to swap or insufficient balance'}
            return result_data

    except Exception as e:
        logger.error(f'Error in kuru function: {str(e)}')
        result_data['details'] = {'error': str(e)}
        return result_data