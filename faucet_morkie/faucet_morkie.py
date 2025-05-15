import time
import random
import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
    def input_eth_address(driver: Any, mm_address: str) -> bool:
        """Robust Ethereum address input using SeleniumUtilities."""
        selectors = [
            "//input[contains(@placeholder, 'EVM Address')]",
            "//input[contains(@placeholder, 'Enter your EVM Address')]",
            "//input[contains(@aria-label, 'Ethereum address')]",
            "//input[@type='text' and contains(@class, 'border-gray-300')]"
        ]

        for selector in selectors:
            input_field = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector)
            if not input_field:
                continue

            try:
                # Clear field thoroughly
                input_field.clear()
                for _ in range(3):
                    input_field.send_keys(Keys.BACKSPACE)
                    time.sleep(0.1)

                # Input address with verification
                for char in mm_address:
                    input_field.send_keys(char)
                    time.sleep(0.05)

                if (current_value := input_field.get_attribute('value') or "").lower() == mm_address.lower():
                    return True

                logger.warning("Address mismatch. Expected: %s, Got: %s", mm_address, current_value)
            except Exception as e:
                logger.debug("Input error with selector %s: %s", selector, str(e))
                continue

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
    def get_faucet_status(driver: Any) -> Dict[str, Any]:
        """Comprehensive status detection using SeleniumUtilities."""
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
                r'Network error. Check your connection and try again.'
            ],
            'success': [
                r'Success!',
                r'Transaction:',
                r'Check your wallet'
            ]
        }

        try:
            # Multiple selectors for status messages
            message_element = SeleniumUtilities.find_element_safely(
                driver,
                By.XPATH,
                "//div[contains(@class, 'border-berryBlackmail')]//div[contains(@class, 'rounded-lg')] | "
                "//div[contains(@class, 'alert')] | "
                "//div[contains(@class, 'message')]",
                timeout=5
            )

            if not message_element:
                return {'status': 'unknown', 'message': 'No status message found'}

            message_text = message_element.text.strip()
            result = {'message': message_text, 'status': 'unknown'}

            # Check all status patterns
            for status, patterns in STATUS_PATTERNS.items():
                if any(re.search(pattern, message_text, re.IGNORECASE) for pattern in patterns):
                    result['status'] = status
                    break

            # Additional data processing
            if result['status'] == 'limit_exceeded':
                if (wait_match := re.search(r'in (\d+h \d+m|\d+h|\d+m)', message_text)):
                    if (wait_delta := MonadFaucet.parse_wait_time(wait_match.group(1))):
                        result["next_attempt"] = (datetime.now() + wait_delta).strftime("%Y-%m-%d %H:%M:%S")

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

                claim_btn = SeleniumUtilities.find_button_by_text(driver, 'Claim')
                if not claim_btn or not SeleniumUtilities.click_safely(claim_btn):
                    raise Exception("Failed to interact with claim button")

                address_field = SeleniumUtilities.find_element_safely(
                    driver,
                    By.XPATH,
                    "//input[contains(@placeholder, 'EVM Address')]",
                    timeout=5
                )
                if not address_field:
                    raise Exception("Address field not revealed")

                if not MonadFaucet.input_eth_address(driver, wallet_address):
                    raise Exception("Address input failed")

                # Send transaction
                send_btn = SeleniumUtilities.find_button_by_text(driver, 'Send')
                claim_btn = SeleniumUtilities.find_button_by_text(driver, 'Claim')

                if send_btn and SeleniumUtilities.click_safely(send_btn):
                    logger.debug("Clicked 'Send' button")
                elif claim_btn and SeleniumUtilities.click_safely(claim_btn):
                    logger.debug("Clicked 'Claim' button")
                else:
                    raise Exception("Failed to find and click transaction button")

                # Process result
                time.sleep(3)  # Wait for transaction processing
                result = MonadFaucet.get_faucet_status(driver)

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

    @staticmethod
    def parse_faucet_block(driver: Any) -> Dict[str, Any]:
        """
        Parse the main faucet block and extract all relevant elements.
        Returns a dictionary containing buttons, input fields, and status information.
        """
        result = {
            'buttons': [],
            'input_fields': [],
            'status_info': None,
            'tier_info': None,
            'transaction_info': None,
            'initial_claim_button': None
        }

        try:
            # Find main block
            main_block = SeleniumUtilities.find_element_safely(
                driver,
                By.XPATH,
                "//div[contains(@class, 'border-berryBlackmail')]",
                timeout=5
            )

            if not main_block:
                logger.error("Main faucet block not found")
                return result

            # Find initial claim button
            initial_claim_btn = SeleniumUtilities.find_element_safely(
                main_block,
                By.XPATH,
                ".//button[contains(@class, 'primary-btn') and contains(text(), 'Claim')]"
            )

            if initial_claim_btn:
                result['initial_claim_button'] = {
                    'text': initial_claim_btn.text.strip(),
                    'element': initial_claim_btn,
                    'aria_label': initial_claim_btn.get_attribute('aria-label'),
                    'class': initial_claim_btn.get_attribute('class')
                }
                logger.debug("Found initial claim button: %s", initial_claim_btn.text.strip())

            # Find all buttons
            buttons = main_block.find_elements(By.TAG_NAME, "button")
            for btn in buttons:
                btn_info = {
                    'text': btn.text.strip(),
                    'element': btn,
                    'aria_label': btn.get_attribute('aria-label'),
                    'class': btn.get_attribute('class')
                }
                result['buttons'].append(btn_info)

            # Find all input fields
            input_fields = main_block.find_elements(By.TAG_NAME, "input")
            for input_field in input_fields:
                input_info = {
                    'placeholder': input_field.get_attribute('placeholder'),
                    'value': input_field.get_attribute('value'),
                    'element': input_field,
                    'aria_label': input_field.get_attribute('aria-label')
                }
                result['input_fields'].append(input_info)

            # Find tier information
            tier_div = SeleniumUtilities.find_element_safely(
                main_block,
                By.XPATH,
                ".//div[contains(@class, 'bg-indigo-900/30')]"
            )
            if tier_div:
                result['tier_info'] = {
                    'text': tier_div.text.strip(),
                    'element': tier_div
                }

            # Find status information
            status_divs = main_block.find_elements(
                By.XPATH,
                ".//div[contains(@class, 'bg-green-900/40') or contains(@class, 'bg-red-900/40')]"
            )
            for status_div in status_divs:
                status_info = {
                    'text': status_div.text.strip(),
                    'element': status_div,
                    'class': status_div.get_attribute('class')
                }

                # Check for transaction link
                tx_link = SeleniumUtilities.find_element_safely(
                    status_div,
                    By.XPATH,
                    ".//a[contains(@href, 'tx/')]"
                )
                if tx_link:
                    status_info['transaction'] = {
                        'hash': tx_link.text.strip(),
                        'url': tx_link.get_attribute('href')
                    }

                result['status_info'] = status_info
                break

            logger.debug("Successfully parsed faucet block")
            return result

        except Exception as e:
            logger.error("Failed to parse faucet block: %s", str(e))
            return result