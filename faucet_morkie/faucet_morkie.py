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
        """Input Ethereum address with verification."""
        selectors = [
            "//input[contains(@placeholder, 'EVM Address')]",
            "//input[contains(@placeholder, 'Enter your EVM Address')]",
            "//input[contains(@aria-label, 'Ethereum address')]",
            "//input[@type='text' and contains(@class, 'border-gray-300')]"
        ]

        for selector in selectors:
            input_field = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector)
            if input_field:
                try:
                    input_field.clear()
                    for _ in range(3):
                        input_field.send_keys(Keys.BACKSPACE)
                        time.sleep(0.1)

                    for char in mm_address:
                        input_field.send_keys(char)
                        time.sleep(0.05)

                    if input_field.get_attribute('value').lower() == mm_address.lower():
                        return True
                except Exception as e:
                    logger.debug(f"Error inputting address: {str(e)}")
        return False

    @staticmethod
    def parse_wait_time(wait_str):
        """Parse wait time string into timedelta."""
        try:
            hours = int(re.search(r'(\d+)h', wait_str).group(1)) if 'h' in wait_str else 0
            minutes = int(re.search(r'(\d+)m', wait_str).group(1)) if 'm' in wait_str else 0
            return timedelta(hours=hours, minutes=minutes)
        except Exception as e:
            logger.error(f"Error parsing wait time: {str(e)}")
            return None

    @staticmethod
    def check_final_status(driver):
        """Check only final status after sending transaction."""
        status_patterns = {
            "limit_exceeded": "//div[contains(@class, 'bg-yellow-900') and contains(., 'Claim limit exceeded')]",
            "limit_reached": "//p[starts-with(text(), 'Claim limit reached')]",
            "require_morkie_id": "//p[contains(text(), 'You need a Morkie ID')]",
            "success": "//div[contains(@class, 'bg-green-900')]//a[contains(@href, 'socialscan.io/tx/')]",
            "failed": "//p[contains(text(), 'Transaction failed')]"
        }

        for status, pattern in status_patterns.items():
            element = SeleniumUtilities.find_element_safely(driver, By.XPATH, pattern, timeout=3)
            if element:
                result = {
                    "status": status,
                    "message": element.text.strip()
                }

                if status == "limit_exceeded":
                    wait_match = re.search(r'in (\d+h \d+m)', element.text)
                    if wait_match:
                        wait_delta = MonadFaucet.parse_wait_time(wait_match.group(1))
                        if wait_delta:
                            result["next_claim"] = (datetime.now() + wait_delta).strftime("%Y-%m-%d %H:%M:%S")

                if status == "success":
                    href = element.get_attribute("href")
                    if href and "/tx/" in href:
                        result["transaction"] = href.split("/tx/")[-1]

                return result

        return {"status": "unknown"}

    @staticmethod
    def process_claim(driver, wallet_address):
        """Optimized claim processing logic."""
        for attempt in range(MAX_RETRIES):
            try:
                driver.get(FAUCET_URL)
                time.sleep(2)

                # Try to click Claim button if address field not present
                address_field = SeleniumUtilities.find_element_safely(
                    driver, By.XPATH,
                    "//input[contains(@placeholder, 'EVM Address')]",
                    timeout=3
                )

                if not address_field:
                    claim_btn = SeleniumUtilities.find_button_by_text(driver, 'Claim $MON')
                    if claim_btn and SeleniumUtilities.click_safely(claim_btn):
                        time.sleep(1)

                # Input address
                if not MonadFaucet.input_eth_address(driver, wallet_address):
                    raise Exception("Failed to input address")

                # Click Send button
                send_btn = SeleniumUtilities.find_button_by_text(driver, 'Send')
                if not send_btn or not SeleniumUtilities.click_safely(send_btn):
                    raise Exception("Failed to click Send button")

                # Check final result with short timeout
                time.sleep(3)
                status = MonadFaucet.check_final_status(driver)

                if status["status"] in ["success", "limit_exceeded", "limit_reached", "require_morkie_id"]:
                    status["wallet_address"] = wallet_address
                    return status

                if status["status"] == "failed":
                    raise Exception("Transaction failed, retrying")

                raise Exception("Unknown status after sending")

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < MAX_RETRIES - 1:
                    time.sleep(MonadFaucet.exponential_backoff(attempt))
                    driver.refresh()

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
            result = MonadFaucet.process_claim(driver, wallet_address)
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