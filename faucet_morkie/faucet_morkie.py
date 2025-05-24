import time
import random
import re
from datetime import datetime, timedelta
from pprint import pprint
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait

from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger
from meta_mask import MetaMaskHelper

# Constants
MAX_RETRIES = 5
BASE_RETRY_DELAY = 3
FAUCET_URL = "https://faucet.morkie.xyz/monad"
MORKIE_ID_URL = "https://morkie.xyz/id"


class MonadFaucet:
    """
    Automates interaction with the Monad blockchain faucet to claim tokens.
    Uses SeleniumUtilities for all element interactions with robust error handling.
    """

    @staticmethod
    def exponential_backoff(retry_count: int,
                            base_delay: float = BASE_RETRY_DELAY,
                            max_delay: float = 60) -> float:
        """Calculate delay with exponential backoff and random jitter."""
        delay = min(base_delay * (2 ** retry_count), max_delay)
        return delay * random.uniform(0.8, 1.2)

    @staticmethod
    def input_eth_address(driver: Any, element, mm_address: str) -> bool:
        """Robust Ethereum address input using SeleniumUtilities."""
        # selectors = [
        #     "//input[contains(@placeholder, 'EVM Address')]",
        #     "//input[contains(@placeholder, 'Enter your EVM Address')]",
        #     "//input[contains(@aria-label, 'Ethereum address')]",
        #     "//input[@type='text' and contains(@class, 'border-gray-300')]"
        # ]

        # for selector in selectors:
        #     input_field = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector)
        #     if not input_field:
        #         continue

        try:
            # Clear field thoroughly
            element.clear()
            for _ in range(3):
                element.send_keys(Keys.BACKSPACE)
                time.sleep(0.1)

            # Input address with verification
            element.send_keys(mm_address)

            if (current_value := element.get_attribute('value') or "").lower() == mm_address.lower():
                return True

            logger.warning("Address mismatch. Expected: %s, Got: %s", mm_address, current_value)
        except Exception as e:
            logger.debug("Input error with selector %s: %s", element, str(e))

        logger.error("All address input attempts failed")
        return False

    @staticmethod
    def parse_wait_time(wait_str: str) -> Optional[timedelta]:
        """Safely parse wait time string into timedelta."""
        try:
            hours = minutes = 0
            if (h_match := re.search(r'(\d+)h', wait_str)):
                hours = int(h_match.group(1))
            if (m_match := re.search(r'(\d+)m', wait_str)):
                minutes = int(m_match.group(1))
            return timedelta(hours=hours, minutes=minutes)
        except (AttributeError, ValueError) as e:
            logger.error("Failed to parse wait time '%s': %s", wait_str, str(e))
            return None

    @staticmethod
    def get_faucet_status(driver: Any, main_block) -> Dict[str, Any]:
        """Определяет статус транзакции, используя find_text()."""

        STATUS_PATTERNS = {
            'limit_exceeded': [
                r'Too many requests',
                r'Claim limit exceeded',
                r'Claim limit reached',
                r'Try again in \d+h \d+m',
                r'Please try again later'
            ],
            'require_morkie_id': [
                r'You need a Morkie ID',
                r'Morkie ID required'
            ],
            'failed': [
                r'Transaction failed',
                r'Failed to process',
                r'Failed to send transaction',
                r'Too many requests. Please try again later.',
                r'Network error. Check your connection and try again.',
                r'error'
            ],
            'success': [
                r'Success!',
                r'Transaction:',
                r'Success! Check your wallet.'
            ]
        }

        # Дожидаемся, что внутри main_block есть хотя бы один элемент
        wait = WebDriverWait(driver, timeout=10)

        # Ожидаем появления элементов внутри main_block
        wait.until(
            lambda d: main_block.find_elements(By.XPATH, ".//*"),
            message="Элементы внутри main_block не загрузились"
        )

        try:
            message_text = []

            # выбираем элемент если удачный клейм
            xpath_selector = "//div[contains(@class, 'bg-green-900/40') and contains(., 'Success! Check your wallet') and .//span[text()='Transaction:']]"
            el = SeleniumUtilities.find_element_safely(driver, By.XPATH, xpath_selector)
            if el:
                print(f'el.text: {el.text}')
                message_text.append(el.text)
                # logger.info(f"Message text el.text: {message_text[0]}")  # Для отладки
            else:  # если не удачный клейм, используем обычный метод
                text_result = SeleniumUtilities.find_text(main_block, list(sum(STATUS_PATTERNS.values(), [])))
                message_text.append(text_result['elements'][0].text)
                # logger.info(f"Message text ['elements'][0].text: {message_text[0]}")  # Для отладки
            # logger.info(f"Message text: {message_text}")  # Для отладки
            result = {'message': message_text[0], 'status': 'unknown'}

            # 📌 Проверяем статус по шаблонам
            for status, patterns in STATUS_PATTERNS.items():
                if any(re.search(pattern, message_text[0], re.IGNORECASE) for pattern in patterns):
                    result['status'] = status
                    break

            # ⏳ Если статус 'limit_exceeded', извлекаем время ожидания
            if result['status'] == 'limit_exceeded':
                if (wait_match := re.search(r'in (\d+h \d+m|\d+h|\d+m)', message_text[0])):
                    if (wait_delta := MonadFaucet.parse_wait_time(wait_match.group(1))):
                        result["next_attempt"] = (datetime.now() + wait_delta).strftime("%Y-%m-%d %H:%M:%S")

            # 🔗 Если статус 'success', ищем транзакцию
            elif result['status'] == 'success':
                if (
                tx_element := SeleniumUtilities.find_element_safely(driver, By.XPATH, ".//a[contains(@href, 'tx/')]")):
                    if (href := tx_element.get_attribute('href')):
                        result['transaction'] = href.split('/tx/')[-1][:64]

            return result

        except Exception as e:
            logger.error("Status check failed: %s", str(e))
            return {'status': 'error', 'message': str(e)}


    @staticmethod
    def process_claim(driver: Any, wallet_address: str) -> Dict[str, Any]:
        """Complete claim process with intelligent retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                # Initial page load
                driver.get(FAUCET_URL)
                if not SeleniumUtilities.find_element_safely(driver, By.XPATH, "//body", timeout=10):
                    raise Exception("Page failed to load")

                # Find main block
                main_block = SeleniumUtilities.find_element_safely(
                    driver,
                    By.XPATH,
                    "//div[contains(@class, 'border-berryBlackmail')]",
                    timeout=5
                )

                logger.debug('Шаг 1: Нажимаем кнопку Claim')
                text_btn = 'Claim'
                if not SeleniumUtilities.find_click_button(main_block, text_btn):
                    logger.debug(f' (process_claim), Не удачное нажатие на кнопку: {text_btn}')

                logger.debug('Шаг 2: Вводим адрес в поле для ввода')
                locator = (By.XPATH, "//input[@type='text' and starts-with(@placeholder, 'Enter your EVM Address')]")
                if not SeleniumUtilities.fill_field(driver, locator, wallet_address):
                    logger.debug(f' (process_claim), Не удачный ввод в поле для адреса')

                logger.debug('Шаг 3: Нажимаем кнопку Claim')
                text_btn = 'Claim'
                if not SeleniumUtilities.find_click_button(main_block, text_btn):
                    logger.debug(f' (process_claim), Не удачное нажатие на кнопку: {text_btn}')

                time.sleep(5)  # Wait for transaction processing
                # if SeleniumUtilities.handle_element_obstruction(driver, main_block):
                #     logger.debug("Мешающие окна закрыты, проверяем результат...")


                result = MonadFaucet.get_faucet_status(driver, main_block)
                # time.sleep(5)

                # Ensure all required fields are present
                result.update({
                    "wallet_address": wallet_address,
                    "attempt": attempt + 1,
                    "status": result.get('status', 'unknown'),
                    "activity_type": "Monad_Faucet_Portal"
                })

                # Terminal statuses
                if result['status'] in {'limit_exceeded', 'require_morkie_id', 'success'}:
                    return result

                # Retriable failures
                if result['status'] == 'failed' and attempt < MAX_RETRIES - 1:
                    delay = MonadFaucet.exponential_backoff(attempt)
                    logger.warning("Claim failed, retrying in %.1f seconds...", delay)
                    time.sleep(delay)
                    continue

                return result

            except Exception as e:
                logger.error("Claim attempt %d failed: %s", attempt + 1, str(e))
                if attempt == MAX_RETRIES - 1:
                    return {
                        'status': 'error',
                        'message': str(e),
                        'wallet_address': wallet_address,
                        'attempt': attempt + 1,
                        'activity_type': "Monad_Faucet_Portal"
                    }
                delay = MonadFaucet.exponential_backoff(attempt)
                time.sleep(delay)

        return {
            'status': 'max_retries_exceeded',
            'message': 'Maximum retry attempts reached',
            'wallet_address': wallet_address,
            'attempt': MAX_RETRIES,
            'activity_type': "Monad_Faucet_Portal"
        }

    @staticmethod
    def process(driver: Any, wallet_address: str) -> Dict[str, Any]:
        """Process faucet claim and return result with activity type."""
        try:
            logger.info("Initiating faucet claim for %s", wallet_address)
            result = MonadFaucet.process_claim(driver, wallet_address)

            # Ensure all required fields are present
            result.update({
                'activity_type': 'Monad_Faucet_Portal',
                'status': result.get('status', 'unknown'),
                'wallet_address': wallet_address
            })

            if result.get("status") == "require_morkie_id":
                logger.info("Redirecting for Morkie ID registration")
                MetaMaskHelper.open_tab(driver, MORKIE_ID_URL)
                MetaMaskHelper.open_tab(driver, "https://app.1inch.io/#/1/simple/swap/1:ETH/8453:ETH")

            logger.info("Claim completed with status: %s", result.get('status', 'unknown'))
            return result

        except Exception as e:
            logger.critical("Fatal process error: %s", str(e))
            return {
                'activity_type': 'Monad_Faucet_Portal',
                'status': 'process_failed',
                'message': str(e),
                'wallet_address': wallet_address
            }
