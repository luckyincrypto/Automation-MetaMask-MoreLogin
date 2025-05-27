import random
import time
from pprint import pprint
from typing import Dict, Any, Optional, Tuple
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

from meta_mask import MetaMaskHelper, compare_addresses
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger, MIN_PERCENT_MON, MAX_PERCENT_MON
from utils import calculate_percentage, adjust_window_position, random_number_for_sell


class KuruSwap:
    """Класс для работы с Kuru Swap"""

    BASE_URL = 'https://www.kuru.io/swap?from=0x0000000000000000000000000000000000000000&to=0xf817257fed379853cDe0fa4F97AB987181B1E5Ea'

    # Селекторы для поиска элементов
    WALLET_SELECTORS = [
        'button[data-sentry-element="DialogTrigger"]',  # Connect wallet button
        'div[data-sentry-element="SheetTrigger"]',  # Wallet connected already
    ]

    TOKEN_SELECTORS = {
        'symbol': "max-w-44 w-fit min-w-10 truncate",
        'balance': "flex items-center justify-between text-secondary-text"
    }

    def __init__(self, driver):
        """
        Инициализация KuruSwap.

        Args:
            driver: WebDriver - экземпляр драйвера
        """
        self.driver = driver
        self.metamask = MetaMaskHelper(driver)

    def open_website(self) -> bool:
        """
        Открывает сайт Kuru Swap.

        Returns:
            bool: True если сайт успешно открыт, False в противном случае
        """
        try:
            logger.info('Opening Kuru website')
            self.driver.get(self.BASE_URL)
            time.sleep(2)  # Ждем загрузку страницы
            logger.info('Kuru website opened successfully')
            return True
        except Exception as e:
            logger.error(f'Error opening Kuru website: {str(e)}')
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

            if not SeleniumUtilities.find_and_click_child_by_text(dialog_block, 'MetaMask'):
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
            token_exist = {'selling_token': {}, 'buying_token': {}}

            # Получаем символы токенов
            els_symbol_list = SeleniumUtilities.get_elements(
                self.driver,
                self.TOKEN_SELECTORS['symbol']
            )
            logger.debug(f'Found token symbols: {els_symbol_list[0].text.strip()}, and: {els_symbol_list[1].text.strip()}')

            # if els_symbol_list[0].safe




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
            logger.debug(f"els_info_list: {els_info_list}")

            # Проверка наличия токенов
            number_tokens_selling = float(els_info_list[0]) if els_info_list[0] not in [None, 0, '0'] else 0.0
            token_exist.setdefault('selling_token', {})['number_tokens'] = number_tokens_selling

            if number_tokens_selling == 0.0:
                logger.debug(f"Токенов {selling_symbol} в кошельке нет")
            else:
                logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_selling} {selling_symbol}')

            # Обработка баланса buying token. Проверяем наличие данных и корректно преобразуем в float
            number_tokens_buying = float(els_info_list[1]) if els_info_list[1] not in [None, 0, '0'] else 0.0

            # Безопасное присваивание в `token_exist`
            token_exist.setdefault('buying_token', {})['number_tokens'] = number_tokens_buying

            # Логирование результата
            if number_tokens_buying == 0.0:
                logger.debug(f"Токенов {buying_symbol} в кошельке нет")
            else:
                logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_buying} {buying_symbol}')

            return token_exist

        except Exception as e:
            logger.error(f'Error getting token info: {str(e)}')
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
            css_selector_buying = '.app-container div.\!mt-0 input'
            elements_input_buying = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR, css_selector_buying)
            logger.debug(f"При продаже {number} получим: {elements_input_buying.get_attribute('value')}")

            quantity_will_purchase = elements_input_buying.get_attribute('value')
            return quantity_will_purchase, element_btn

        else:
            logger.error("Элемент не найден или недоступен для нажатия")
            return False


    def swap(self):
        # Получаем информацию по токенам
        token_info = self.get_token_info()
        if not token_info:
            logger.error(" (kuru), Failed to get token info")
            return False
        logger.debug(f' (kuru), Initial token_info: {token_info}')

        refresh_element = token_info['element_refresh']
        number_tokens_selling = token_info['selling_token']['number_tokens']
        selling_symbol = token_info['selling_token']['symbol']

        quantity_for_sale = token_info['selling_token']['quantity_for_sale'] = random_number_for_sell(selling_symbol,
                                                                                                      number_tokens_selling)
        quantity_will_purchase, element_btn_swap = self.input_number_for_sell(quantity_for_sale)
        if not quantity_will_purchase and not element_btn_swap:
            logger.error(" (kuru), Failed to input number for sell")
            return None


        window_kuru = self.driver.current_window_handle  # Определяем вкладку Kuru
        logger.debug(f' (kuru), Current opened Kuru tab: {window_kuru}')
        current_windows = self.driver.window_handles  # Определяем все открытые вкладки
        logger.debug(f' (kuru), Current opened tabs: {current_windows}')

        token_info['buying_token']['quantity_will_purchase'] = quantity_will_purchase
        if not SeleniumUtilities.click_safely(element_btn_swap):
            logger.error(" (kuru), Failed to click button <Swap>")
            if not SeleniumUtilities.click_safely(refresh_element):
                logger.error(" (kuru), Failed to click button <Refresh quote>")
            logger.error(" (kuru), Success click button <Refresh quote>")
            if not SeleniumUtilities.click_safely(element_btn_swap):
                logger.error(" (kuru), Failed to 2nd time click button <Swap>")

        # После успешного нажатия на кнопку <SWAP> на сайте Kuru, открывается вкладка MetaMask где нажимаем кнопку <Confirm>.
        new_window_mm = SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
        logger.debug(f' (kuru), New tab MetaMask is opened: {new_window_mm}')
        if new_window_mm:
            time.sleep(1)
            text_btn = 'Confirm'  # Transaction request
            button_element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
            if button_element:
                button_element.click()

        # После успешного нажатия на кнопку <Confirm> в MetaMask, переходим обратно на вкладку с сайтом Kuru.
        self.driver.switch_to.window(window_kuru)
        if self.driver.current_window_handle == window_kuru:
            logger.debug(f" (kuru), On tab Kuru website again")

        # После успешного взаимодействия с MetaMask на сайте Kuru нажимаем кнопку <Go back>
        btn_name = 'Go back'
        button_element = SeleniumUtilities.find_button_by_text(self.driver, btn_name)
        if button_element:
            button_element.click()

        time.sleep(5)
        self.driver.refresh()

        # После успешного нажатия на кнопку <Go back> проверяем свапнутые токены
        token_info_after_swap = self.get_token_info()
        logger.debug(f" (kuru), token_info_after_swap: {token_info_after_swap}")

        return True




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
        kuru_swap = KuruSwap(driver)

        if not kuru_swap.open_website():
            logger.error(f" (kuru), Failed to open website {'Kuru'}")
            return None

        if not kuru_swap.connect_wallet(mm_address):
            logger.error(" (kuru), Failed to connect MetaMask wallet")
            return None

        kuru_swap.swap()



    except Exception as e:
        logger.error(f'Error in kuru function: {str(e)}')
        return None
