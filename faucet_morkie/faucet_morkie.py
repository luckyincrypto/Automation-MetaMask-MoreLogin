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
                        result["next_claim"] = (datetime.now() + wait_delta).strftime("%Y-%m-%d %H:%M:%S")

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


                claim_btn = SeleniumUtilities.find_button_by_text(driver, 'Claim $MON')
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
                if not send_btn or not SeleniumUtilities.click_safely(send_btn):
                    raise Exception("Failed to send transaction")

                # Process result
                time.sleep(3)  # Wait for transaction processing
                result = MonadFaucet.get_faucet_status(driver)
                result.update({
                    "wallet_address": wallet_address,
                    "attempt": attempt + 1
                })

                # Terminal statuses
                if result['status'] in {'limit_exceeded', 'require_morkie_id', 'success'}:
                    return result

                # Retriable failures
                if result['status'] == 'failed' and attempt < MAX_RETRIES - 1:
                    backoff = MonadFaucet.exponential_backoff(attempt)
                    logger.info("Attempt %d failed. Retrying in %.1fs", attempt + 1, backoff)
                    time.sleep(backoff)
                    continue

                return result

            except Exception as e:
                logger.error("Attempt %d error: %s", attempt + 1, str(e))
                if attempt < MAX_RETRIES - 1:
                    time.sleep(MonadFaucet.exponential_backoff(attempt))
                    driver.refresh()

        return {
            "status": "max_retries_exceeded",
            "message": f"All {MAX_RETRIES} attempts failed",
            "wallet_address": wallet_address
        }

    @staticmethod
    def process(driver: Any, wallet_address: str) -> Dict[str, Any]:
        """Main processing wrapper with comprehensive error handling."""
        activity = {'Monad_Faucet_Portal': None}

        try:
            logger.info("Initiating faucet claim for %s", wallet_address)
            result = MonadFaucet.process_claim(driver, wallet_address)
            activity['Monad_Faucet_Portal'] = result

            if result.get("status") == "require_morkie_id":
                logger.info("Redirecting for Morkie ID registration")
                MetaMaskHelper.open_tab(driver, MORKIE_ID_URL)
                MetaMaskHelper.open_tab(driver, "https://app.1inch.io/#/1/simple/swap/1:ETH/8453:ETH")

            logger.info("Claim completed with status: %s", result.get('status', 'unknown'))
            return activity

        except Exception as e:
            logger.critical("Fatal process error: %s", str(e))
            activity['Monad_Faucet_Portal'] = {
                "status": "process_failed",
                "message": str(e),
                "wallet_address": wallet_address
            }
            return activity