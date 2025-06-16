import random
import time
from pprint import pprint

# Работа с типами данных
from typing import Dict, Any, Optional, Tuple, List

# Работа с URL
from urllib.parse import urlparse, parse_qs, urlencode

# Selenium
from selenium.common import WebDriverException
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
'0xcf5a6076cfa32686c0df13abada2b40dec133f1d',
'0xabd7afa2161eb7254c0a9dbb5fe79216b7c28e03',
'0x39e95286dd43f8da34cbda8e4b656da9f53ca644',
'0x743cef7ccc8ac56605c8404607142e5b35efa11d',
'0x268e4e24e0051ec27b3d27a95977e71ce6875a05',
'0x4c10428ed0410dfb2de62fc007f7c1105ae861e9',
'0x2fa2c507289be90ca50a8802f8d436d43001b521',
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


class KuruSwap:
    """Класс для работы с Kuru Swap"""


    # Селекторы для поиска элементов
    WALLET_SELECTORS = [
        'button[data-sentry-element="DialogTrigger"]',  # Connect wallet button
        'div[data-sentry-element="SheetTrigger"]',  # Wallet connected already
    ]

    TOKEN_SELECTORS = {
        'symbol': "max-w-44 w-fit min-w-10 truncate",
        'balance': "flex items-center justify-between text-secondary-text",
        }

    def __init__(self, driver):
        """
        Инициализация KuruSwap.

        Args:
            driver: WebDriver - экземпляр драйвера
        """
        self.driver = driver
        self.metamask = MetaMaskHelper(driver)

    # def open_website(self) -> bool:
    #     """
    #     Открывает сайт Kuru Swap.
    #
    #     Returns:
    #         bool: True если сайт успешно открыт, False в противном случае
    #     """
    #     try:
    #         logger.info('Opening Kuru website')
    #         self.driver.get(self.BASE_URL)
    #         time.sleep(2)  # Ждем загрузку страницы
    #         logger.info('Kuru website opened successfully')
    #         return True
    #     except Exception as e:
    #         logger.error(f'Error opening Kuru website: {str(e)}')
    #         return False


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
            logger.info(f'Opening Kuru website: {BASE_URL}')
            self.driver.get(BASE_URL)

            # Ожидание загрузки страницы вместо time.sleep
            WebDriverWait(self.driver, 10).until(title_contains("Kuru"))

            logger.info('Kuru website opened successfully')
            return True

        except WebDriverException as e:
            logger.error(f'WebDriver error: {str(e)}')
            return False

        except Exception as e:
            logger.error(f'Unexpected error while opening Kuru website: {str(e)}')
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
                    By.CSS_SELECTOR,
                    self.WALLET_SELECTORS,
                    timeout=5
                )

                if not element:
                    logger.error("Не удалось найти элементы подключения кошелька")
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
        try:
            var = self.driver.refresh
            print(f'var: {var}')
            time.sleep(3)
            token_exist = {'selling_token': {}, 'buying_token': {}}

            # Получаем символы токенов
            els_symbol_list = SeleniumUtilities.get_elements(
                self.driver,
                self.TOKEN_SELECTORS['symbol']
            )
            logger.debug(f' (get_token_info), Found token symbols: {els_symbol_list[0].text.strip()}, and: {els_symbol_list[1].text.strip()}')

            selling_symbol = token_exist['selling_token']['symbol'] = els_symbol_list[0].text.strip()
            buying_symbol = token_exist['buying_token']['symbol'] = els_symbol_list[1].text.strip()

            # Получаем балансы токенов и элемент обновления
            els_info_list = []
            el_text = SeleniumUtilities.get_elements(self.driver, self.TOKEN_SELECTORS['balance'])
            for index, el in enumerate(el_text):
                if el.text.strip():
                    if 'Refresh quote' in el.text.strip():
                        els_list = SeleniumUtilities.parse_interactive_elements(el)
                        for el_refresh_quote in els_list['elements_info']:
                            if 'Refresh quote' == el_refresh_quote['text'] and el_refresh_quote['classes'] == 'text-sm font-medium':
                                token_exist['element_refresh'] = el_refresh_quote['element']
                    try:
                        number = float(el.text.split()[0])
                        els_info_list.append(number)
                    except Exception:
                        pass

            # Обработка баланса selling token
            logger.debug(f" (get_token_info), els_info_list: {els_info_list}")

            # Проверка наличия токенов
            number_tokens_selling = float(els_info_list[0]) if els_info_list[0] not in [None, 0, '0'] else 0.0
            token_exist.setdefault('selling_token', {})['number_tokens'] = number_tokens_selling

            if number_tokens_selling == 0.0:
                logger.debug(f" (get_token_info), Токенов {selling_symbol} в кошельке нет")
            else:
                logger.debug(f' (get_token_info), Токены есть в кошельке, можно продать: {number_tokens_selling} {selling_symbol}')

            # Обработка баланса buying token. Проверяем наличие данных и корректно преобразуем в float
            number_tokens_buying = float(els_info_list[1]) if els_info_list[1] not in [None, 0, '0'] else 0.0

            # Безопасное присваивание в `token_exist`
            token_exist.setdefault('buying_token', {})['number_tokens'] = number_tokens_buying

            # Логирование результата
            if number_tokens_buying == 0.0:
                logger.debug(f" (get_token_info), Токенов {buying_symbol} в кошельке нет")
            else:
                logger.debug(f' (get_token_info), Токены есть в кошельке, можно продать: {number_tokens_buying} {buying_symbol}')

            return token_exist

        except Exception as e:
            logger.error(f' (get_token_info), Error getting token info: {str(e)}')
            return {'selling_token': {}, 'buying_token': {}}

    def input_number_for_sell(self, number):
        css_selector_selling = '.app-container div.space-y-2 input'
        elements_input_selling = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR, css_selector_selling)
        if elements_input_selling:
            elements_input_selling.clear()
            elements_input_selling.send_keys(number)
            if elements_input_selling.get_attribute("value") == number:
                logger.debug(f" (_fill_field), Вставка значения: {number} успешна")
        else:
            logger.error("Не удалось найти элементы для ввода числа")

        text_button = 'Swap'
        element_btn = SeleniumUtilities.find_button_by_text(self.driver, text_button)
        if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
            css_selector_buying = r".app-container div.\!mt-0 input"
            elements_input_buying = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR, css_selector_buying)
            logger.debug(f"При продаже {number} получим: {elements_input_buying.get_attribute('value')}")

            quantity_will_purchase = elements_input_buying.get_attribute('value')
            return quantity_will_purchase

        else:
            logger.error("Элемент не найден или недоступен для нажатия")
            return False

    def swap(self, token_info_swap: Dict[str, Dict[str, Any]]):
        refresh_element = token_info_swap['element_refresh']
        number_tokens_selling = token_info_swap['selling_token']['number_tokens']
        selling_symbol = token_info_swap['selling_token']['symbol']

        quantity_for_sale = token_info_swap['selling_token']['quantity_for_sale'] = random_number_for_sell(selling_symbol,
                                                                                                      number_tokens_selling)
        quantity_will_purchase = self.input_number_for_sell(quantity_for_sale)
        if not quantity_will_purchase:
            logger.error(" (swap), Failed to input number for sell")
            return False


        window_kuru = self.driver.current_window_handle  # Определяем вкладку Kuru
        logger.debug(f' (swap), Current opened Kuru tab: {window_kuru}')
        current_windows = self.driver.window_handles  # Определяем все открытые вкладки
        logger.debug(f' (swap), Current opened tabs: {current_windows}')

        token_info_swap['buying_token']['quantity_will_purchase'] = quantity_will_purchase

        max_attempts = 5
        attempt = 0
        while attempt < max_attempts:
            attempt += 1
            logger.debug(f'Attempt №: {attempt}')
            time.sleep(3)
            text_button = 'Swap'
            element_btn = SeleniumUtilities.find_button_by_text(self.driver, text_button, timeout=20)
            if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
                if not SeleniumUtilities.click_safely(element_btn):
                    logger.error(" (swap), Failed to click button <Swap>")
                    if not SeleniumUtilities.click_safely(refresh_element):
                        logger.error(" (swap), Failed to click button <Refresh quote>")
                        continue  # переходит сразу к следующему кругу цикла.
                    logger.error(" (swap), Success click button <Refresh quote>")
                    time.sleep(2)
                    continue  # переходит сразу к следующему кругу цикла.


            # После успешного нажатия на кнопку <SWAP> на сайте Kuru, открывается вкладка MetaMask где нажимаем кнопку <Confirm>.
            new_window_mm = SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
            if not new_window_mm:
                continue  # переходит сразу к следующему кругу цикла.
            logger.debug(f' (swap), New tab MetaMask is opened: {new_window_mm}')
            if new_window_mm:
                time.sleep(1)

                text_btn = 'Confirm'  # MetaMask. Transaction request. Button <Confirm>
                button_element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
                if button_element:
                    button_element.click()
                    logger.debug(f" (swap), MetaMask tab. Clicked button {text_btn} successfully")


            # После успешного нажатия на кнопку <Confirm> в MetaMask, переходим обратно на вкладку с сайтом Kuru.
            self.driver.switch_to.window(window_kuru)
            if self.driver.current_window_handle == window_kuru:
                logger.debug(f" (swap), On tab Kuru website again")

            btn_name = 'Retry the swap'
            button_element_retry_swap = SeleniumUtilities.find_button_by_text(self.driver, btn_name)
            if button_element_retry_swap:
                button_element_retry_swap.click()
                logger.debug(f" (swap), Clicked button <{btn_name}> successfully")
                time.sleep(2)
                continue  # переходит сразу к следующему кругу цикла.

            logger.debug(f'selling_symbol, {selling_symbol}')
            if not selling_symbol.lower() == 'mon':
                time.sleep(5)
                new_window_mm = SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
                if new_window_mm:
                    SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
                    text_btn = 'Confirm'  # MetaMask. Transaction request. Button <Confirm>
                    button_element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
                    if button_element:
                        button_element.click()
                        logger.debug(f" (swap), MetaMask tab. Clicked button {text_btn} successfully")

                        self.driver.switch_to.window(window_kuru)
                        if self.driver.current_window_handle == window_kuru:
                            logger.debug(f" (swap), On tab Kuru website again")

                            btn_name = 'Retry the swap'
                            button_element_retry_swap = SeleniumUtilities.find_button_by_text(self.driver, btn_name)
                            if button_element_retry_swap:
                                button_element_retry_swap.click()
                                logger.debug(f" (swap), Clicked button {btn_name} successfully")
                                time.sleep(2)
                                continue  # переходит сразу к следующему кругу цикла.



            # После успешного взаимодействия с MetaMask на сайте Kuru нажимаем кнопку <Go back>
            btn_name = 'Go back'
            logger.debug(f" (swap), Trying to find button: {btn_name}")
            button_element_go_back = SeleniumUtilities.find_button_by_text(self.driver, btn_name)
            if button_element_go_back:
                button_element_go_back.click()
                logger.debug(f" (swap), Clicked button {btn_name} successfully")
                return True
            return False
        else:
            logger.error(" (swap), Max swap attempts reached")
            return False


def kuru(driver, mm_address):
    """
    Основная функция для работы с Kuru Swap.

    Args:
        driver: WebDriver - экземпляр драйвера
        mm_address: str - адрес кошелька MetaMask

    Returns:
        Dict[str, Dict[str, Any]]: Информация о токенах для свопа
    """
    try:
        # Создаем экземпляр класса для работы с Kuru Swap
        kuru_swap = KuruSwap(driver)

        # Открываем сайт
        while True:
            driver.refresh()

            random_address = random.choice(toket_address_list)
            logger.debug(f"Случайный токен: {random_address}")

            if not kuru_swap.open_website(to_token=random_address):
                logger.error(f" (kuru), Failed to open website Kuru")
                continue  # переходит сразу к следующему кругу цикла.
            logger.debug(f" (kuru), Opened website Kuru")
            break  # выход из цикла

        # Подключаем кошелек
        while True:
            if not kuru_swap.connect_wallet(mm_address):
                logger.error(" (kuru), Failed to connect MetaMask wallet")
                continue  # переходит сразу к следующему кругу цикла.
            logger.debug(" (kuru), Connected MetaMask wallet")
            break  # выход из цикла

        # Получаем информацию по токенам
        token_info_before_swap = kuru_swap.get_token_info()
        if not token_info_before_swap:
            logger.error(" (kuru), Failed to get token info")
            return False
        logger.debug(f' (kuru), Get token_info_before_swap successfully')

        # Если есть токены в кошельке более чем 0.2 и это MON, то продаем его
        if token_info_before_swap['selling_token']['number_tokens'] > 0.2 and token_info_before_swap['selling_token']['symbol'].lower() == 'mon':
            # Вводим количество токенов для продажи и получаем количество получаемых токенов
            if not kuru_swap.swap(token_info_before_swap):
                logger.error(f" (kuru), Failed to swap {token_info_before_swap['selling_token']['symbol']} tokens")
                return False
            logger.debug(f" (kuru), Swapped from {token_info_before_swap['selling_token']['symbol']} "
                         f"to {token_info_before_swap['buying_token']['symbol']} tokens successfully")

        # Для обратного свапа. Если есть другие токены в кошельке больше 0,0 кроме MON, то продаем его
        elif token_info_before_swap['selling_token']['number_tokens'] != 0.0:
            if not kuru_swap.swap(token_info_before_swap):
                logger.error(f" (kuru), Failed to swap {token_info_before_swap['selling_token']['symbol']} tokens")
                return False
            logger.debug(f" (kuru), Swapped from {token_info_before_swap['selling_token']['symbol']} "
                         f"to {token_info_before_swap['buying_token']['symbol']} tokens successfully")

        time.sleep(2)
        driver.refresh()
        time.sleep(5)
        # После успешного нажатия на кнопку <Go back> проверяем свапнутые токены
        token_info_after_swap = kuru_swap.get_token_info()
        logger.debug(f" (kuru), Get token_info_after_swap successfully")

        logger.debug(f' (kuru), Initial token_info: {token_info_before_swap}')
        logger.debug(f" (kuru), token_info_after_swap: {token_info_after_swap}")


        url_name_swap = driver.current_url
        list_addresses = extract_swap_addresses(url_name_swap)
        # Проверяем, что список не пустой и содержит два элемента
        if len(list_addresses) == 2:
            token_from, token_to = list_addresses
        else:
            print("Ошибка: Невозможно извлечь `from` и `to` из URL")
            token_from, token_to = None, None
        if token_from and token_to:
            kuru_swap.open_website(from_token=token_to, to_token=token_from)  # Меняем местами
            url_name_swap_revers = driver.current_url
            logger.debug(f'url_name_swap_revers successful: {url_name_swap_revers}')
        else:
            logger.error("Ошибка: Не удалось открыть страницу обмена, поскольку адреса токенов невалидны.")

        while True:
            time.sleep(3)
            # Кнопка <Swap> для обратного свапа
            text_button = 'Swap'
            element_btn = SeleniumUtilities.find_button_by_text(driver, text_button)
            if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
                break
            # Получаем информацию по токенам обратный свап
            token_info_before_revers_swap = kuru_swap.get_token_info()
            if not token_info_before_revers_swap:
                logger.error(" (kuru), Failed to get token info token_info_before_revers_swap")
                return False
            logger.debug(f' (kuru), Get token_info_before_revers_swap successfully')

            # Если есть токены в кошельке более чем 0,2 и это MON, то продаем его
            if token_info_before_revers_swap['selling_token']['number_tokens'] > 0.2 and \
                    token_info_before_revers_swap['selling_token']['symbol'].lower() == 'mon':
                # Вводим количество токенов для продажи и получаем количество получаемых токенов
                if not kuru_swap.swap(token_info_before_revers_swap):
                    logger.error(f" (kuru), Failed to swap {token_info_before_revers_swap['selling_token']['symbol']} tokens")
                    return False
                logger.debug(f" (kuru), Swapped from {token_info_before_revers_swap['selling_token']['symbol']} "
                             f"to {token_info_before_revers_swap['buying_token']['symbol']} tokens successfully")

            # Обратный свап. Если есть другие токены в кошельке больше 0,0 кроме MON, то продаем его
            elif token_info_before_revers_swap['selling_token']['number_tokens'] != 0.0:
                if not kuru_swap.swap(token_info_before_revers_swap):
                    logger.error(f" (kuru), Failed to swap {token_info_before_revers_swap['selling_token']['symbol']} tokens")
                    return False
                logger.debug(f" (kuru), Swapped from {token_info_before_revers_swap['selling_token']['symbol']} "
                             f"to {token_info_before_revers_swap['buying_token']['symbol']} tokens successfully")

                time.sleep(5)

                token_info_after_revers_swap = kuru_swap.get_token_info()
                if token_info_before_revers_swap['selling_token']['number_tokens'] != token_info_after_revers_swap['selling_token']['number_tokens']:
                    logger.debug(f" (kuru), Get token_info_after_revers_swap successfully")
                    return False
                else:
                    logger.debug(f" (kuru), Failed to token_info_after_revers_swap")
                    return True

            else:
                logger.error(" (kuru), No tokens to swap")
                classes="flex h-7 cursor-pointer items-center rounded-full border bg-white px-2 text-xs font-semibold duration-200 hover:bg-black/5 dark:bg-white dark:bg-opacity-5 dark:hover:border-brand/50 dark:hover:text-brand"
                el_100 = SeleniumUtilities.get_element(driver, classes)
                if el_100:
                    logger.debug(f'el_100 found')
                    if SeleniumUtilities.click_safely(el_100):
                        logger.debug(f'el_100 click_safely')
                        time.sleep(3)
                        text_button = 'Swap'
                        element_btn = SeleniumUtilities.find_button_by_text(driver, text_button, timeout=20)
                        if element_btn and element_btn.is_enabled() and element_btn.is_displayed():
                            if not SeleniumUtilities.click_safely(element_btn):
                                logger.error(" (swap), Failed to click button <Swap>")

                return False



    except Exception as e:
        logger.error(f'Error in kuru function: {str(e)}')
        return None
