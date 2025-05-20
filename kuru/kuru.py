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


URL = 'https://www.kuru.io/swap?from=0x0000000000000000000000000000000000000000&to=0xf817257fed379853cDe0fa4F97AB987181B1E5Ea'

# def switch_to_new_window(driver, current_windows, timeout=15):
#     """
#     Ожидает появление нового окна/вкладки и переключается на него.
#
#     Параметры:
#         driver: экземпляр WebDriver
#         current_windows: текущие открытые окна
#         timeout: максимальное время ожидания в секундах (по умолчанию 10)
#
#     Возвращает:
#         handle нового окна
#     """
#
#     # Ждем появления нового окна
#     WebDriverWait(driver, timeout).until(EC.new_window_is_opened(current_windows))
#
#     # Получаем все окна после открытия нового
#     new_windows = driver.window_handles
#
#     # Находим handle нового окна
#     new_window = list(set(new_windows) - set(current_windows))[0]
#
#     # Переключаемся на новое окно
#     driver.switch_to.window(new_window)
#     return new_window

def kuru(driver: Any):
    logger.info('Opening Kuru website')
    driver.get(URL)
    logger.info('Opened')

    class_name = 'space-y-4'
    celector = f"//div[contains(@class, {class_name})]"
    main_block = SeleniumUtilities.find_element_safely(
        driver,
        By.XPATH,
        celector,
        timeout=5
    )

    # Парсим элементы внутри main_block
    # info = SeleniumUtilities.parse_interactive_elements(main_block)
    # pprint(info)

    # Клик по "Connect wallet"
    text_btn = 'Connect wallet'
    logger.info('Click on button: %s', text_btn)
    if SeleniumUtilities.find_click_button(main_block, text_btn):
        logger.info('Clicked on button: %s', text_btn)

    time.sleep(3)
    role_name = 'dialog'
    celector = f"//div[@role='{role_name}']"  # Правильно: @role='dialog'
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
