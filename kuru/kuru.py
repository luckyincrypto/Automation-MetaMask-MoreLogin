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
from utils import calculate_percentage, adjust_window_position


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

    # def _adjust_window_position(self):
    #     """Настраивает позицию и размер окна MetaMask."""
    #     try:
    #         rect = self.driver.get_window_rect()
    #         logger.debug(f"Window position: ({rect['x']}, {rect['y']}), Size: {rect['width']}x{rect['height']}")
    #
    #         self.driver.maximize_window()
    #         time.sleep(2)
    #
    #         self.driver.set_window_rect(
    #             rect['x'],
    #             rect['y'],
    #             rect['width'],
    #             rect['height']
    #         )
    #     except Exception as e:
    #         logger.error(f'Error adjusting window position: {str(e)}')

    def get_token_info(self) -> Dict[str, Dict[str, Any]]:
        """
        Получает информацию о токенах для свопа.

        Returns:
            Dict[str, Dict[str, Any]]: Информация о токенах в формате:
            {
                'selling_token': {
                    'symbol': str,
                    'number_tokens': float,
                    'quantity_for_sale': float
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

            print("els_info_list:", els_info_list)
            # Обработка баланса selling token
            if not els_info_list[0]:
                number_tokens_selling = token_exist['selling_token']['number_tokens'] = 0.0
            else:
                number_tokens_selling = token_exist['selling_token']['number_tokens'] = float(els_info_list[0])
                if number_tokens_selling == 0.0:
                    logger.debug(f"Токенов {selling_symbol} в кошельке нет")
                else:
                    logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_selling} {selling_symbol}')

            # Обработка баланса buying token
            if not els_info_list[1]:
                number_tokens_buying = token_exist['buying_token']['number_tokens'] = 0.0
            else:
                number_tokens_buying = token_exist['buying_token']['number_tokens'] = float(els_info_list[1])
                if number_tokens_buying == 0.0:
                    logger.debug(f"Токенов {buying_symbol} в кошельке нет")
                else:
                    logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_buying} {buying_symbol}')

            # Расчет количества для продажи
            percent_from_mon = random.randint(MIN_PERCENT_MON, MAX_PERCENT_MON)
            number_for_sell = calculate_percentage(number_tokens_selling, percent_from_mon)
            token_exist['selling_token']['quantity_for_sale'] = number_for_sell

            logger.debug(
                f"Выбрано рандомно число: {percent_from_mon}% от {number_tokens_selling} {selling_symbol} = "
                f"{number_for_sell} {selling_symbol} на продажу"
            )

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
        element = SeleniumUtilities.find_button_by_text(self.driver, text_button)
        if element and element.is_enabled() and element.is_displayed():
            css_selector_buying = '.app-container div.\!mt-0 input'
            elements_input_buying = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR, css_selector_buying)
            logger.debug(f"При продаже {number} получим: {elements_input_buying.get_attribute('value')}")

            quantity_will_purchase = elements_input_buying.get_attribute('value')
            return quantity_will_purchase, element

            # if SeleniumUtilities.click_safely(element):
            #     logger.info(f" (input_number_for_sell), Кликнули на кнопку: {text_button} успешно")
            #     return True
            # else:
            #     logger.info(f" (input_number_for_sell), Кликнуть на кнопку: {text_button} не удалось")
            #     return False
        else:
            logger.error("Элемент не найден или недоступен для нажатия")
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
        kuru_swap = KuruSwap(driver)

        if not kuru_swap.open_website():
            return None

        if not kuru_swap.connect_wallet(mm_address):
            return None

        token_info = kuru_swap.get_token_info()
        # if 'element_refresh' in token_info:
        refresh_element = token_info['element_refresh']

        # print(f'token_info: {token_info}')

        quantity_for_sale = token_info['selling_token']['quantity_for_sale']
        quantity_will_purchase, element = kuru_swap.input_number_for_sell(quantity_for_sale)
        if not quantity_will_purchase and not element:
            logger.error("Failed to input number for sell")

        token_info['buying_token']['quantity_will_purchase'] = quantity_will_purchase
        if not SeleniumUtilities.click_safely(element):
            logger.error("Failed to click button <Swap>")
            if not SeleniumUtilities.click_safely(refresh_element):
                logger.error("Failed to click button <Refresh quote>")
            logger.error("Success click button <Refresh quote>")
            if not SeleniumUtilities.click_safely(element):
                logger.error("Failed to 2nd time click button <Swap>")
        print(f"token_info: {token_info}")





        time.sleep(2)
        # SeleniumUtilities.click_safely(refresh_element)
        # kuru_swap.input_number_for_sell(number_for_sell+1.0)
        #
        # time.sleep(2)
        # SeleniumUtilities.click_safely(refresh_element)
        # kuru_swap.input_number_for_sell(number_for_sell + 3.0)

    except Exception as e:
        logger.error(f'Error in kuru function: {str(e)}')
        return None
