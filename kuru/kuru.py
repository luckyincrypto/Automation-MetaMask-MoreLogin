import random
import time
from pprint import pprint
from typing import Dict, Any, Optional
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from  meta_mask import MetaMaskHelper, compare_addresses
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger, MIN_PERCENT_MON, MAX_PERCENT_MON
from utils import calculate_percentage


def kuru(driver, mm_address):
    URL = 'https://www.kuru.io/swap?from=0x0000000000000000000000000000000000000000&to=0xf817257fed379853cDe0fa4F97AB987181B1E5Ea'
    logger.info('Opening Kuru website')
    driver.get(URL)
    logger.info('Opened')
    time.sleep(2)

    # поиск подходящего селектора для подключенного адреса кошелька или если нужно подключить
    css_selectors = [
        'button[data-sentry-element="DialogTrigger"]',  # Connect wallet button
        'div[data-sentry-element="SheetTrigger"]',  # Wallet connected already
        ]
    def connection_wallet_to_site():
        while True:
            time.sleep(3)
            element =  SeleniumUtilities.find_which_selector(driver, By.CSS_SELECTOR, css_selectors, timeout=5)
            text_in_element = element.text
            logger.debug(f'text_in_element: {text_in_element}')
            if text_in_element == 'Connect wallet':
                element.click()
                logger.debug(f'Нажали на кнопку <Connect wallet>')

                time.sleep(3)
                role_name = 'dialog'
                selector = f"//div[@role='{role_name}']"
                dialog_block = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector, timeout=5)
                if dialog_block:
                    # Перед взаимодействием с MetaMask получаем текущие открытые окна
                    current_windows = driver.window_handles
                    logger.debug(f'current_windows: {current_windows}')

                    child_text = 'MetaMask'
                    logger.debug('Click on child: %s', child_text)
                    if SeleniumUtilities.find_and_click_child_by_text(dialog_block, child_text):
                        logger.info('Clicked on child: %s', child_text)

                        new_window = SeleniumUtilities.switch_to_new_window(driver, current_windows)
                        if new_window:
                            logger.debug(f'new_window: {new_window}')

                            rect = driver.get_window_rect()
                            logger.debug(f"Позиция: ({rect['x']}, {rect['y']}), Размер: {rect['width']}x{rect['height']}")

                            driver.maximize_window()
                            time.sleep(2)
                            logger.debug(f'Активное окно приложения MetaMask')
                            # Установить окно: x=100, y=200 (позиция), width=800, height=600 (размер)
                            driver.set_window_rect(rect['x'], rect['y'], rect['width'], rect['height'])


                            helper = MetaMaskHelper(driver)
                            connection_button = helper.handle_metamask_connection(driver)
                            if connection_button:
                                logger.info("Подключение выполнено")
                                window = current_windows[-1]
                                driver.switch_to.window(window)
                            else:
                                logger.error("Не удалось завершить подключение")

            else:
                if compare_addresses(mm_address, text_in_element):
                    logger.info(f'Адрес MetaMask {mm_address} подключен к сайту: https://www.kuru.io/ \n')
                    break
        return True

    print(f'connection_wallet_to_site(): {connection_wallet_to_site()}')

    def swap_coin():
        # Нахождение selling токена и его количества
        token_exist = {'selling_token': {}, 'buying_token': {}}
        texts = SeleniumUtilities.get_elements_text(driver, "max-w-44 w-fit min-w-10 truncate")
        logger.debug(f'texts: {texts} ')

        selling_symbol = token_exist['selling_token']['symbol'] = texts[0]
        buying_symbol = token_exist['buying_token']['symbol'] = texts[1]

        xpath_selector = "flex items-center justify-between text-secondary-text"
        el_text = SeleniumUtilities.get_elements_text(driver, xpath_selector)
        logger.debug(f'el_text: {el_text} ')

        if not el_text[1]:
            number_tokens_selling = token_exist['selling_token']['number_tokens'] = 0.0
        else:
            number_tokens_selling = token_exist['selling_token']['number_tokens'] = float(el_text[1])
            if number_tokens_selling == 0.0:
                logger.debug(f"Токенов {selling_symbol} в кошельке нет")
            logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_selling} {selling_symbol}')

        if not el_text[2]:
            number_tokens_buying = token_exist['buying_token']['number_tokens'] = 0.0
        else:
            number_tokens_buying = token_exist['buying_token']['number_tokens'] = float(el_text[2])

        percent_from_mon = random.randint(MIN_PERCENT_MON, MAX_PERCENT_MON)
        number_for_sell = calculate_percentage(number_tokens_selling, percent_from_mon)
        logger.debug(f"Выбрано рандомно число: {percent_from_mon}% от {number_tokens_selling} {selling_symbol} = {number_for_sell} {selling_symbol} на продажу")
        token_exist['selling_token']['number_for_sell'] = number_for_sell

        if number_tokens_buying:
            if number_tokens_buying == 0.0:
                logger.debug(f"Токенов {buying_symbol} в кошельке нет")

            logger.debug(f'Токены есть в кошельке, можно продать: {number_tokens_buying} {buying_symbol}')

        return token_exist



    pprint(swap_coin())








