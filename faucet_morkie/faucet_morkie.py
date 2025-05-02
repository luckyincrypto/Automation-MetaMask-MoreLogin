import datetime
import time
import random
import re
from datetime import datetime, timedelta

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
    @staticmethod
    def exponential_backoff(retry_count, base_delay=BASE_RETRY_DELAY, max_delay=60):
        """Calculate delay with exponential backoff and random jitter."""
        delay = min(base_delay * (2 ** retry_count), max_delay)
        return delay * random.uniform(0.8, 1.2)

    @staticmethod
    def input_eth_address(driver, mm_address):
        """Input Ethereum address using SeleniumUtilities with robust verification."""
        selectors = [
            "//input[contains(@placeholder, 'EVM Address')]",
            "//input[contains(@placeholder, 'Enter your EVM Address')]",
            "//input[contains(@aria-label, 'Ethereum address')]",
            "//input[@type='text' and contains(@class, 'border-gray-300')]"
        ]

        for selector in selectors:
            input_field = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector, timeout=10)
            if not input_field:
                continue

            try:
                # Clear field thoroughly
                input_field.click()
                input_field.clear()
                for _ in range(3):  # Extra cleanup
                    input_field.send_keys(Keys.BACKSPACE)
                    input_field.send_keys(Keys.DELETE)
                    time.sleep(0.1)

                # Type address carefully
                for char in mm_address:
                    input_field.send_keys(char)
                    time.sleep(0.05)

                # Verify input
                current_value = SeleniumUtilities.find_element_safely(
                    driver, By.XPATH,
                    f"{selector}[@value='{mm_address}']"
                )

                if current_value:
                    logger.debug(f"Successfully entered ETH address: {mm_address}")
                    return True

                # Fallback verification
                current_value = input_field.get_attribute('value')
                if current_value and current_value.lower() == mm_address.lower():
                    logger.debug(f"Verified address via get_attribute: {mm_address}")
                    return True

                logger.warning(f"Address mismatch. Expected: {mm_address}, Got: {current_value}")

            except Exception as e:
                logger.debug(f"Error with selector {selector}: {str(e)}")
                continue

        logger.error("Failed to input ETH address after all attempts")
        return False

    @staticmethod
    def extract_transaction_hash(driver):
        """Extract transaction hash using SeleniumUtilities."""
        patterns = [
            "//div[contains(@class, 'bg-green-900')]//a[contains(@href, 'socialscan.io/tx/')]",
            "//a[contains(@href, 'socialscan.io/tx/')]",
            "//div[contains(text(), 'Transaction:')]//a"
        ]

        for pattern in patterns:
            element = SeleniumUtilities.find_element_safely(driver, By.XPATH, pattern)
            if element:
                href = element.get_attribute("href")
                if href and "/tx/" in href:
                    return href.split("/tx/")[-1]
                if element.text and len(element.text) >= 10:
                    return element.text
        return None

    @staticmethod
    def parse_wait_time(wait_str):
        """Parse wait time string (e.g. '16h 55m') into timedelta."""
        try:
            hours = 0
            minutes = 0

            if 'h' in wait_str:
                hours = int(re.search(r'(\d+)h', wait_str).group(1))
            if 'm' in wait_str:
                minutes = int(re.search(r'(\d+)m', wait_str).group(1))

            return timedelta(hours=hours, minutes=minutes)
        except Exception as e:
            logger.error(f"Error parsing wait time: {str(e)}")
            return None

    @staticmethod
    def check_result_status(driver):
        """Check status using only SeleniumUtilities methods."""
        status_checks = [
            ("success", "//div[contains(@class, 'bg-green-900') and contains(., 'Success!')]"),
            ("limit_exceeded", "//div[contains(@class, 'bg-yellow-900') and contains(., 'Claim limit exceeded')]"),
            ("require_morkie_id", "//p[contains(text(), 'You need a Morkie ID')]"),
            ("limit_reached", "//p[starts-with(text(), 'Claim limit reached')]"),
            ("failed", "//p[contains(text(), 'Transaction failed')]"),
            ("probable_success", "//div[contains(text(), 'Transaction:')]")
        ]

        for status, xpath in status_checks:
            element = SeleniumUtilities.find_element_safely(driver, By.XPATH, xpath)
            if element:
                result = {"status": status, "message": element.text.strip()}

                if status == "limit_exceeded":
                    wait_match = re.search(r'in (\d+h \d+m)', element.text)
                    if wait_match:
                        wait_str = wait_match.group(1)
                        wait_delta = MonadFaucet.parse_wait_time(wait_str)
                        if wait_delta:
                            # Добавляем 3 минуты буфера к времени ожидания
                            next_claim = datetime.now() + wait_delta + timedelta(minutes=3)
                            result["next_claim"] = next_claim.strftime("%Y-%m-%d %H:%M:%S")
                            logger.debug(f"Next claim available at: {result['next_claim']}")

                if status in ("success", "probable_success"):
                    tx_hash = MonadFaucet.extract_transaction_hash(driver)
                    if tx_hash:
                        result["transaction_hash"] = tx_hash

                return result

        return {"status": "unknown", "message": "No status message detected"}

    @staticmethod
    def claim_mon_token(driver, wallet_address):
        """Complete claim process using SeleniumUtilities."""
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(FAUCET_URL)
                time.sleep(2)

                # Pre-check for immediate status
                # pre_check = MonadFaucet.check_result_status(driver)
                # if pre_check["status"] != "unknown":
                #     pre_check["wallet_address"] = wallet_address
                #     return pre_check

                # Handle claim button
                claim_btn = SeleniumUtilities.find_button_by_text(driver, 'Claim $MON')
                if not claim_btn or not SeleniumUtilities.click_safely(claim_btn):
                    raise Exception("Claim button interaction failed")

                # Input address
                time.sleep(1)
                if not MonadFaucet.input_eth_address(driver, wallet_address):
                    raise Exception("Address input failed")

                # Handle send button
                send_btn = SeleniumUtilities.find_button_by_text(driver, 'Send')
                if not send_btn or not SeleniumUtilities.click_safely(send_btn):
                    raise Exception("Send button interaction failed")

                # Check result with retries
                result = None
                for _ in range(5):
                    result = MonadFaucet.check_result_status(driver)
                    if result["status"] != "unknown":
                        break
                    time.sleep(1)

                if not result or result["status"] == "unknown":
                    raise Exception("No valid result detected")

                result["wallet_address"] = wallet_address
                return result

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    delay = MonadFaucet.exponential_backoff(attempt)
                    logger.debug(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                    driver.refresh()
                else:
                    return {
                        "status": "error",
                        "message": str(e),
                        "wallet_address": wallet_address
                    }

        return {
            "status": "max_retries_exceeded",
            "message": f"Failed after {MAX_RETRIES} attempts",
            "wallet_address": wallet_address
        }

    @staticmethod
    def process(driver, wallet_address):
        """Main processing wrapper."""
        activity = {'Monad_Faucet_Portal': None}

        try:
            result = MonadFaucet.claim_mon_token(driver, wallet_address)
            activity['Monad_Faucet_Portal'] = result

            if result.get("status") == "require_morkie_id":
                logger.debug("Redirecting for Morkie ID...")
                MetaMaskHelper.open_tab(driver, MORKIE_ID_URL)
                MetaMaskHelper.open_tab(driver, "https://app.1inch.io/#/1/simple/swap/1:ETH/8453:ETH")

        except Exception as e:
            logger.critical(f"Process failed: {str(e)}")
            activity['Monad_Faucet_Portal'] = {
                "status": "process_failed",
                "message": str(e),
                "wallet_address": wallet_address
            }

        return activity