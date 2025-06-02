import random
import time
from pprint import pprint
from typing import Dict, Any, Optional, Tuple

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from meta_mask import MetaMaskHelper, compare_addresses
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger
from utils import adjust_window_position, random_number_for_sell





class Fantasy:

    BASE_URL = 'https://monad.fantasy.top/shop'


    def __init__(self, driver):
        """
        Инициализация Fantasy.
        Args:
            driver: WebDriver - экземпляр драйвера
        """
        self.driver = driver


    def open_website(self) -> bool:
        """
        Открывает сайт https://monad.fantasy.top/shop.

        Returns:
            bool: True если сайт успешно открыт, False в противном случае
        """
        try:
            logger.info('Opening Fantasy website')
            self.driver.get(self.BASE_URL)
            time.sleep(2)  # Ждем загрузку страницы
            logger.info('Fantasy website opened successfully')
            return True
        except Exception as e:
            logger.error(f'Error opening Kuru website: {str(e)}')
            return False

    def claim(self):
        def first_click():
            time.sleep(3)
            text = 'Claim'
            element = SeleniumUtilities.find_button_by_text(self.driver, text)
            text_element = element.text
            logger.info(f' (first_click), Element with text: "{text}" has text "{text_element}"')
            if element:
                logger.info(f' (first_click), Found element with text "{text}"')
                if text == text_element:
                    SeleniumUtilities.click_safely(element)
                    logger.info(' (first_click), Clicked on the element with text "Claim"')
                    return True
                else:
                    logger.warning(f' (first_click), Element with text "{text}" has different text: "{text_element}"')
                    # Здесь добавить логику для добавления в БД crypto_activities.sqlite3 в activity_type, через какое время и когда Claim будет активен
                    return True
            else:
                logger.warning(f' (first_click), No element with text "{text}" found')
                return False

        def retweet_click():
            #  Если нажимаем на кнопку Claim первый раз то появляется модальное окно, и нужно нажать на кнопку Retweet
            #  и на странице Х сделать ретвит, затем нажать на кнопку Verify, только потом нажимаем на кнопку Claim
            current_windows = self.driver.window_handles
            logger.debug(f' (retweet_click), Current windows: {current_windows}')
            current_window_fantasy_tab = self.driver.current_window_handle
            logger.debug(f' (retweet_click), current_window_kuru_tab: {current_window_fantasy_tab}')

            time.sleep(3)
            class_names = 'mt-2 flex gap-x-5'  # ищем элемент с классом "mt-2 flex gap-x-5" в нем 2 кнопки, Retweet и Verify
            el = SeleniumUtilities.get_element(self.driver, class_names)

            if not el:
                logger.warning(f' (retweet_click), No element with class name "{class_names}" found')
                return False

            logger.info(f' (retweet_click), Найден элемент c текстом: {el.text}\n')
            child_text = 'Retweet'
            if child_text in el.text:
                logger.info(f' (retweet_click), Found text: {child_text} in element text: "{el.text}"')
                if not SeleniumUtilities.find_and_click_child_by_text(el, child_text, partial_match=False):
                    logger.error(f' (retweet_click), Failed to click on child element with text: {child_text}')
                    return False
                else:
                    logger.info(f' (retweet_click), Clicked on child element with text: {child_text} successfully')

                    def on_x_page():
                        time.sleep(2)
                        new_window_x_tab = SeleniumUtilities.switch_to_new_window(self.driver, current_windows)
                        if not new_window_x_tab:
                            logger.error(" (retweet_click, on_x_page), Failed to switch to new_window_x_tab")
                            return False
                        logger.debug(f' (retweet_click, on_x_page), On tab X: {new_window_x_tab}')

                        time.sleep(2)
                        # Нажимаем на кнопку <Follow>
                        # универсальный селектор для поиска кнопки с надписью "Follow" включая "Following".
                        logger.debug(f' (retweet_click, on_x_page), try to find and click on button "Follow"')
                        selector = 'button[role="button"][aria-label*="Follow"]'  # ищет любое значение, которое содержит "Follow", включая "Following".
                        el_btn_follow = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR, selector)
                        if not el_btn_follow:
                            logger.debug(
                                f' (retweet_click, on_x_page), Failed to find el_btn_follow "Follow" включая "Following"')
                        if el_btn_follow.text == 'Follow':
                            logger.info(
                                f' (retweet_click, on_x_page), Button "Follow" found successfully, trying to click it.')
                            if not SeleniumUtilities.click_safely(el_btn_follow):
                                logger.error(f' (retweet_click, on_x_page), Failed to click on button "Follow"')
                        else:
                            logger.info(f' (retweet_click, on_x_page), Found button: {el_btn_follow.text}')

                        max_attempts = 5
                        attempt = 0
                        while attempt < max_attempts:
                            attempt += 1
                            logger.debug(f' (retweet_click, on_x_page), Attempt №: {attempt}')
                            self.driver.refresh()
                            time.sleep(3)
                            # Нажимаем на кнопку <retweet>
                            selector_btn_retweet = 'button[data-testid="retweet"][role="button"]'
                            element_retweet_btn = SeleniumUtilities.find_element_safely(self.driver, By.CSS_SELECTOR,
                                                                                        selector_btn_retweet)
                            logger.debug(
                                f' (retweet_click, on_x_page), try to find and click on button[data-testid="retweet"][role="button"]')
                            if not element_retweet_btn:
                                logger.error(" (retweet_click, on_x_page), Failed to find element_retweet_btn")
                            logger.info(' (retweet_click, on_x_page), Find element_retweet_btn successfully')
                            if not SeleniumUtilities.click_safely(element_retweet_btn):
                                logger.error(" (retweet_click, on_x_page), Failed to click on element_retweet_btn")
                                continue  # переходит сразу к следующему кругу цикла.
                            logger.info(' (retweet_click, on_x_page), Clicked on element_retweet_btn successfully')
                            break  # выход из цикла

                        max_attempts = 5
                        attempt = 0
                        while attempt < max_attempts:
                            attempt += 1
                            logger.debug(f' (retweet_click, on_x_page), Attempt №: {attempt}')
                            self.driver.refresh()
                            time.sleep(3)
                            # Нажимаем на кнопку <Repost>
                            selector_btn_confirm = 'div[data-testid="retweetConfirm"][role="menuitem"]'
                            element_retweet_btn_confirm = SeleniumUtilities.find_element_safely(self.driver,
                                                                                                By.CSS_SELECTOR,
                                                                                                selector_btn_confirm)
                            logger.debug(
                                f' (retweet_click, on_x_page), try to find and click on div[data-testid="retweetConfirm"][role="menuitem"]')
                            if not element_retweet_btn_confirm:
                                logger.error(
                                    " (retweet_click, on_x_page), Failed to find <Repost> element_retweet_btn_confirm")
                                continue  # переходит сразу к следующему кругу цикла.
                            logger.info(
                                ' (retweet_click, on_x_page), Find <Repost> element_retweet_btn_confirm successfully')
                            if not SeleniumUtilities.click_safely(element_retweet_btn_confirm):
                                logger.error(" (retweet_click, on_x_page), Failed to click on btn <Repost>")
                                continue  # переходит сразу к следующему кругу цикла.
                            logger.info(' (retweet_click, on_x_page), Clicked on btn <Repost> successfully')
                            break  # выход из цикла

                        time.sleep(3)
                        self.driver.close()
                        logger.info(' (retweet_click, on_x_page), Closed current tab "X" successfully')
                        self.driver.switch_to.window(current_window_fantasy_tab)
                        current_window = self.driver.current_window_handle
                        if not current_window == current_window_fantasy_tab:
                            logger.error(' (retweet_click, on_x_page), Failed to switch to Fantasy tab')
                            return False
                        logger.info(' (retweet_click, on_x_page), Switched to Fantasy tab successfully')
                        time.sleep(1)
                        return True

                    if not on_x_page():
                        logger.info(' on_x_page), Failed to perform on_x_page actions')

            time.sleep(2)
            # Нажимаем на кнопку <Verify>
            child_text = 'Verify'
            if child_text in el.text:
                logger.info(f' (retweet_click), Found text {child_text} in element text: "{el.text}"')
                if not SeleniumUtilities.find_and_click_child_by_text(el, child_text):
                    logger.error(f' (retweet_click), Failed to click on child element with text: {child_text}')
                    return False
                else:
                    logger.info(f' (retweet_click), Clicked on child element with text: {child_text} successfully')

            time.sleep(3)
            # Нажимаем на кнопку <Claim>
            logger.debug(f' (retweet_click), try to find and click on button "Claim"')
            child_text = 'Claim'
            # универсальный селектор для поиска кнопки с надписью "Claim" включая "Claim now", "Claim reward" и т.д.
            selector_xpath = f'//button[contains(text(), "{child_text}")]'  # находит <button>, который содержит слово "Claim" в любом месте текста
            el_btn_claim = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, selector_xpath)
            if not el_btn_claim:
                logger.debug(f' (retweet_click), Failed to find el_btn_claim "Claim"')
            if el_btn_claim.text == 'Claim':
                logger.info(f' (retweet_click), Button: {el_btn_claim.text} found successfully, trying to click it.')
                if not SeleniumUtilities.click_safely(el_btn_claim):
                    logger.error(
                        f' (retweet_click), Failed to click on button: {el_btn_claim.text} пробуем кликнуть на кнопку с помощью ActionChains')

                    # Создаем объект ActionChains
                    actions = ActionChains(self.driver)
                    # Наводим курсор на кнопку и кликаем
                    actions.move_to_element(el_btn_claim).click().perform()
                    logger.info(
                        f' (retweet_click), Clicked on button: {el_btn_claim.text} successfully через ActionChains')
                    return True

                logger.info(f' (retweet_click), Clicked on button: {el_btn_claim.text} successfully')
                return True
            else:
                logger.info(f' (retweet_click),  Found button: {el_btn_claim.text} not "Claim"')

        if first_click():
            logger.info(' (claim), Successfully clicked on the element with text "Claim"')


        if retweet_click():
            first_click()

        tab_tag_name = self.driver.current_url
        logger.debug(f' (claim), Current tab name: {tab_tag_name}')
        if tab_tag_name == 'https://monad.fantasy.top/shop':
            logger.info(f' (claim), 1 Ждем результат спина и выигрыш')
            return True

        # Здесь добавить логику для добавления в БД crypto_activities.sqlite3 в activity_type, через какое время и когда Claim будет активен







def fantasy(driver) -> None:
    try:
        # Создаем экземпляр класса для работы с monad.fantasy.top
        fantasy = Fantasy(driver)

        # Открываем сайт https://monad.fantasy.top/shop
        if not fantasy.open_website():
            logger.error(f" (kuru), Failed to open website {'Fantasy'}")
        logger.debug(f" (kuru), Opened website {'Fantasy'}")
        if not fantasy.claim():
            logger.info(f" (fantasy), Failed to claim or Continue")
        logger.debug(f" (fantasy), Claimed successfully")


    except Exception as e:
        logger.error(f'Error in fantasy script: {str(e)}')