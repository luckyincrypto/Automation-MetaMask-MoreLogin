import random
import re
import time
from pprint import pprint
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By

from meta_mask import MetaMaskHelper, compare_addresses
from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger
from utils import adjust_window_position, random_number_for_sell





class Fantasy:

    BASE_URL = 'https://monad.fantasy.top/shop'
    # ADDRESS_URL = 'https://monad.fantasy.top/shop/address'


    def __init__(self, driver):
        """
        Инициализация Fantasy.
        Args:
            driver: WebDriver - экземпляр драйвера
        """
        self.driver = driver

    def login(self):
        #  Click button <Register and Play for free>
        def register_button():
            text_btn = 'Register and Play for free'
            element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
            text_element = element.text
            logger.info(f' (login), Element with text: "{text_btn}" has text "{text_element}"')
            if element:
                logger.info(f' (login), Found element with text "{text_element}"')
                if text_btn == text_element:
                    SeleniumUtilities.click_safely(element)
                    logger.info(f' (login), Clicked on the element with text {text_element}')
                    return True
                logger.debug(f' (login), text_btn != text_element: {text_btn} != {text_element}')
            logger.error(f' (login), element not found')
            return False

        #  Click button <Twitter> on pop up window "Log in or sign up"
        def lofin_or_sign_up():
            text_btn = 'Twitter'
            # string(.) захватывает весь видимый текст, включая вложенные <span> и другие элементы внутри кнопки.
            selector_xpath = f'//button[contains(string(.), "{text_btn}")]'
            el_captcha = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, selector_xpath)
            if el_captcha:
                logger.info(f' (capcha), Found el_captcha try to click center of element')
                # Получаем координаты элемента
                rect = el_captcha.rect
                x_center = rect['x'] + rect['width'] // 2
                y_center = rect['y'] + rect['height'] // 2
                logger.debug(f' (capcha), x_center: {x_center}, y_center: {y_center}')

                # Эмулируем клик в центр элемента
                actions = ActionChains(self.driver)
                actions.move_to_element_with_offset(el_captcha, rect['width'] // 2,
                                                    rect['height'] // 2).click().perform()
                logger.debug(f' (capcha), Клик в центр элемента успешен')
                return True

            logger.error(f' (capcha), el_captcha not found')
            return False

        #  When successful connect to X then click button <Continue>
        def continue_btn():
            text_btn = 'Continue'
            element = SeleniumUtilities.find_button_by_text(self.driver, text_btn)
            text_element = element.text
            logger.info(f' (continue_btn), Element with text: "{text_btn}" has text "{text_element}"')
            if element:
                logger.info(f' (continue_btn), Found element with text "{text_element}"')
                if text_btn == text_element:
                    SeleniumUtilities.click_safely(element)
                    logger.info(f' (continue_btn), Clicked on the element with text {text_element}')
                    return True
                logger.debug(f' (continue_btn), text_btn != text_element: {text_btn} != {text_element}')
            logger.error(f' (continue_btn), element not found')
            return False

        def capcha():
            selector_xpath = '//input[@type="checkbox"]'
            el_captcha = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, selector_xpath)
            if el_captcha:
                logger.info(f' (capcha), Found el_captcha try to click center of element')
                # Получаем координаты элемента
                rect = el_captcha.rect
                x_center = rect['x'] + rect['width'] // 2
                y_center = rect['y'] + rect['height'] // 2
                logger.debug(f' (capcha), x_center: {x_center}, y_center: {y_center}')

                # Эмулируем клик в центр элемента
                actions = ActionChains(self.driver)
                actions.move_to_element_with_offset(el_captcha, rect['width'] // 2,
                                                    rect['height'] // 2).click().perform()
                logger.debug(f' (capcha), Клик в центр элемента успешен')
                return True

            logger.error(f' (capcha), el_captcha not found')
            return False

        if register_button():
            if lofin_or_sign_up():
                if capcha():
                    continue_btn()
                    return True
            return False
        return False

    def _open_website(self) -> bool | None:
        """
        Открывает сайт https://monad.fantasy.top/shop.
        Returns:
            bool: True если сайт успешно открыт, False в противном случае
        """
        try:
            logger.debug('Opening Fantasy website')
            self.driver.get(self.BASE_URL)
            time.sleep(5)  # Ждем загрузку страницы)

            tab_tag_name = self.driver.current_url
            logger.debug(f' (open_website), Current tab name: {tab_tag_name}')
            if tab_tag_name == 'https://monad.fantasy.top/shop':
                logger.info(f' (open_website), Fantasy website opened on page: {tab_tag_name}')
                return True
            else:
                logger.info(f' (open_website), Fantasy website opened on page: {tab_tag_name}')
                return False

        except Exception as e:
            logger.error(f' (open_website), Error opening Kuru website: {str(e)}')
            return None

    def claim(self):
        """
        Пытается выполнить клейм XP.
        Returns:
            Dict: Результат выполнения клейма или None в случае ошибки
        """
        try:
            # Находим кнопку Claim
            claim_button = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, "//button[contains(text(), 'Claim')]")
            if not claim_button:
                logger.error("Failed to find Claim button")
                return None

            # Получаем текст кнопки
            button_text = claim_button.text.strip()
            if button_text != "Claim":
                # Парсим время ожидания
                match = re.search(r'Claim in (\d+)h (\d+)m', button_text)
                if match:
                    hours, minutes = map(int, match.groups())
                    next_attempt = datetime.now() + timedelta(hours=hours, minutes=minutes)

                    return {
                        'activity_type': 'Fantasy_Claim_XP',
                        'status': 'limit_exceeded',
                        'wallet_address': '',  # Будет заполнено позже
                        'next_attempt': next_attempt.strftime('%Y-%m-%d %H:%M:%S'),
                        'details': {
                            'message': button_text,
                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                    }
                else:
                    logger.warning(f"Unexpected button text: {button_text}")
                    return None

            # Кликаем по кнопке
            if not SeleniumUtilities.click_safely(claim_button):
                logger.error("Failed to click Claim button")
                return None

            # Ждем успешного клейма
            time.sleep(3)  # Даем время на обработку

            # Проверяем успешность клейма, получаем текст сообщения их модального окна
            unluck_message = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, "//div[contains(text(), 'Confirm')]")
            success_message = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, "//div[contains(text(), 'Successfully claimed')]")
            if success_message:
                now = datetime.now()
                return {
                    'activity_type': 'Fantasy_Claim_XP',
                    'status': 'success',
                    'wallet_address': '',  # Будет заполнено позже
                    'next_attempt': (now + timedelta(hours=24, minutes=3)).strftime('%Y-%m-%d %H:%M:%S'),
                    'details': {
                        'message': 'Successfully claimed XP',
                        'timestamp': now.strftime('%Y-%m-%d %H:%M:%S')
                    }
                }
            elif unluck_message:
                return {
                    'activity_type': 'Fantasy_Claim_XP',
                    'status': 'spin_unluck',
                    'wallet_address': '',  # Будет заполнено позже
                    'next_attempt': None,
                    'details': {
                        'message': 'Spinned but claim XP unlucky',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }

            else:
                logger.warning("No success message found after claim")
                return None

        except Exception as e:
            logger.error(f"Error in claim: {str(e)}")
            return None

    def fantasy(self):
        """
        Обрабатывает активность Fantasy_Claim_XP.
        Returns:
            Dict: Результат выполнения активности или None в случае ошибки
        """
        try:
            # Открываем сайт https://monad.fantasy.top/shop
            if not self._open_website():
                logger.info(f" (fantasy), Login Fantasy")
                if not self.login():
                    logger.error("Failed to login to Fantasy")
                    return None

            # Пытаемся выполнить клейм
            result = self.claim()
            if not result:
                logger.warning("Failed to claim XP in Fantasy")
                return None

            # Получаем адрес кошелька
            selector_xpath_player = "//a[starts-with(@href, '/player/')]"
            element_player = SeleniumUtilities.find_element_safely(self.driver, By.XPATH, selector_xpath_player)
            if not element_player:
                logger.error("Failed to find player element")
                return None

            # Получаем адрес кошелька из href
            wallet_address = element_player.get_attribute("href").split("/")[-1]
            if not wallet_address:
                logger.error("Failed to get wallet address from player element")
                return None

            # Обновляем результат с адресом кошелька
            if isinstance(result, dict):
                result.update({
                    'wallet_address': wallet_address,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                result = {
                    'activity_type': 'Fantasy_Claim_XP',
                    'status': 'error',
                    'wallet_address': wallet_address,
                    'next_attempt': None,
                    'details': {
                        'error': 'Invalid result format',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                }

            logger.info(f"Successfully processed Fantasy activity: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in fantasy activity: {str(e)}")
            return {
                'activity_type': 'Fantasy_Claim_XP',
                'status': 'error',
                'wallet_address': '',  # Не удалось получить адрес
                'next_attempt': None,
                'details': {
                    'error': str(e),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            }