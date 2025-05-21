import time
from pprint import pprint
from typing import Dict, Any, Optional
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from  meta_mask import MetaMaskHelper
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger




def kuru(driver: Any):
    URL = 'https://www.kuru.io/swap?from=0x0000000000000000000000000000000000000000&to=0xf817257fed379853cDe0fa4F97AB987181B1E5Ea'
    logger.info('Opening Kuru website')
    driver.get(URL)
    logger.info('Opened')
    time.sleep(2)

    # Определяем селектор для поиска адреса кошелька
    # selector = "button[data-sentry-element="DialogTrigger"]"  # Connect wallet
    selector = 'div[data-sentry-element="SheetTrigger"]'  # Wallet connected

    # Создаем экземпляр MetaMaskHelper
    metamask = MetaMaskHelper(driver)

    # Получаем информацию о кошельке или подключаем его
    result = metamask.get_info_wallet_or_connect_wallet(selector)

    if result:
        logger.info(f"Кошелек подключен, адрес: {result}")

    else:
        logger.info("Не удалось получить информацию о кошельке, подключение в процессе.")

    # class_name = 'space-y-4'
    # celector = f"//div[contains(@class, {class_name})]"
    # main_block = SeleniumUtilities.find_element_safely(
    #     driver,
    #     By.XPATH,
    #     celector,
    #     timeout=5
    # )

            # Парсим элементы внутри main_block
    # info = SeleniumUtilities.parse_interactive_elements(main_block)
    # pprint(info)

            # Клик по "Connect wallet"
    # text_btn = 'Connect wallet'
    # logger.info('Click on button: %s', text_btn)
    # if SeleniumUtilities.find_click_button(main_block, text_btn):
    #     logger.info('Clicked on button: %s', text_btn)

        time.sleep(3)
        role_name = 'dialog'
        celector = f"//div[@role='{role_name}']"
        dialog_block = SeleniumUtilities.find_element_safely(
            driver,
            By.XPATH,
            celector,
            timeout=5
        )

        # Парсим элементы внутри dialog_block
        # info_dialog_block = SeleniumUtilities.parse_interactive_elements(dialog_block)
        # pprint(info_dialog_block)

            # Получаем текущие открытые окна
        current_windows = driver.window_handles

        child_text = 'MetaMask'
        logger.info('Click on child: %s', child_text)
        if SeleniumUtilities.find_and_click_child_by_text(dialog_block, child_text):
            logger.info('Clicked on child: %s', child_text)

            SeleniumUtilities.switch_to_new_window(driver, current_windows)
            driver.maximize_window()
            helper = MetaMaskHelper(driver)
            if helper.handle_metamask_connection(driver):
                logger.info("Подключение выполнено")
            else:
                logger.error("Не удалось завершить подключение")
