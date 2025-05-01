import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait

from SeleniumUtilities.selenium_utilities import SeleniumUtilities
from config import logger
from meta_mask import open_tab
import random

# Constants with descriptive names
MAX_RETRIES = 5
BASE_RETRY_DELAY = 3
FAUCET_URL = "https://faucet.morkie.xyz/monad"
MORKIE_ID_URL = "https://morkie.xyz/id"

# Message patterns for checking various states
MESSAGE_PATTERNS = {
    "transaction": {
        "xpath": "/html/body/section/div/div/section[1]/div/p[3]",
        "contains": "Transaction"  # Partial match
    },
    "require_morkie_id": {
        "xpath": "/html/body/section/div/div/section[1]/div/p[2]",
        "text": "You need a Morkie ID to claim faucet."
    },
    "limit_reached": {
        "xpath": "/html/body/section/div/div/section[1]/div/p[2]",
        "starts_with": "Claim limit reached."
    },
    "failed": {
        "xpath": "/html/body/section/div/div/section[1]/div/p[2]",
        "text": "Transaction failed. Please try again later."
    },
    "success": {
        "xpath": "//p[contains(text(), 'Success!')]",
        "contains": "Success!"
    }
}


def exponential_backoff(retry_count, base_delay=BASE_RETRY_DELAY, max_delay=60):
    """
    Calculate delay with exponential backoff and random jitter.

    Args:
        retry_count: Current retry number
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds

    Returns:
        Delay time in seconds
    """
    delay = min(base_delay * (2 ** retry_count), max_delay)
    # Add jitter (±20%)
    jitter = random.uniform(0.8, 1.2)
    return delay * jitter

def input_eth_address(driver, mm_address):
    """
    Input Ethereum address into the appropriate field.

    Args:
        driver: Selenium WebDriver instance
        mm_address: Ethereum address to enter

    Returns:
        True if input succeeded, False otherwise
    """
    try:
        # Try multiple selector strategies for better resilience
        selectors = [
            "//input[@placeholder='EVM Address']",
            "//input[@placeholder='Enter your wallet address']",
            "//input[contains(@placeholder, 'Address')]",
            "//div[contains(@class, 'address-input')]//input"
        ]

        for selector in selectors:
            input_field = SeleniumUtilities.find_element_safely(driver, By.XPATH, selector)
            if input_field:
                input_field.clear()
                input_field.send_keys(mm_address)
                logger.debug(f"ETH Address '{mm_address}' successfully entered")
                return True

        logger.debug("Input field for address not found with any selector")
        return False
    except Exception as e:
        logger.debug(f"Error entering ETH address: {e}")
        return False


def check_message_patterns(driver, wait_time=5):
    """
    Check for various message patterns and determine result status.

    Args:
        driver: WebDriver instance
        wait_time: Time to wait for messages to appear

    Returns:
        dict: Result with status and additional information
    """
    result = {"status": "unknown", "message": None}

    try:
        # Wait briefly for any message to appear
        time.sleep(1)

        # Check for transaction element first (success case)
        for pattern_name in ["transaction", "success"]:
            pattern = MESSAGE_PATTERNS.get(pattern_name)
            print(f"pattern: {pattern}")
            if not pattern:
                continue

            try:
                element = WebDriverWait(driver, wait_time).until(
                    EC.presence_of_element_located((By.XPATH, pattern["xpath"]))
                )

                # If it's a transaction pattern, try to extract hash
                if pattern_name == "transaction" and "Transaction" in element.text:
                    # Find the link element which should be a child
                    try:
                        link_element = element.find_element(By.TAG_NAME, "a")
                        transaction_hash = link_element.get_attribute("title")

                        if transaction_hash:
                            return {
                                "status": "success",
                                "message": "Transaction successful",
                                "transaction_hash": transaction_hash
                            }
                    except:
                        # Even if we can't find the link, a transaction message is good news
                        return {
                            "status": "probable_success",
                            "message": element.text
                        }
                # For success message
                elif pattern_name == "success" and "Success" in element.text:
                    return {
                        "status": "success",
                        "message": element.text
                    }
            except:
                # Skip to next pattern if this one isn't found
                continue

        # If we don't find a success pattern, check for error patterns
        for pattern_name in ["require_morkie_id", "limit_reached", "failed"]:
            pattern = MESSAGE_PATTERNS.get(pattern_name)
            if not pattern:
                continue

            try:
                element = WebDriverWait(driver, 1).until(
                    EC.presence_of_element_located((By.XPATH, pattern["xpath"]))
                )

                element_text = element.text

                # Check for exact text match
                if "text" in pattern and element_text == pattern["text"]:
                    return {
                        "status": pattern_name,
                        "message": element_text
                    }

                # Check for starts_with match
                if "starts_with" in pattern and element_text.startswith(pattern["starts_with"]):
                    return {
                        "status": pattern_name,
                        "message": element_text
                    }

                # Check for contains match
                if "contains" in pattern and pattern["contains"] in element_text:
                    return {
                        "status": pattern_name,
                        "message": element_text
                    }
            except:
                # Skip to next pattern if this one isn't found
                continue

    except Exception as e:
        logger.debug(f"Error checking message patterns: {e}")
        result["message"] = str(e)

    return result


def extract_transaction_hash(driver, wait_time=10):
    """
    Try multiple approaches to find the transaction hash.

    Args:
        driver: WebDriver instance
        wait_time: Maximum time to wait for the transaction element

    Returns:
        str or None: Transaction hash if found, None otherwise
    """
    # List of XPath patterns to try
    transaction_patterns = [
        # Primary pattern from MESSAGE_PATTERNS
        MESSAGE_PATTERNS["transaction"]["xpath"] + "/a",
        # Alternate pattern based on HTML structure
        "//p[contains(text(), 'Transaction:')]/a",
        # More general pattern
        "//a[contains(@href, 'socialscan.io/tx/')]"
    ]

    try:
        # Wait for transaction information to appear (up to wait_time seconds)
        WebDriverWait(driver, wait_time).until(
            EC.presence_of_element_located((By.XPATH, "//p[contains(text(), 'Transaction:')]"))
        )

        # Try each pattern
        for xpath in transaction_patterns:
            try:
                link_element = driver.find_element(By.XPATH, xpath)
                transaction_hash = link_element.get_attribute("title")
                if transaction_hash:
                    logger.debug(f"Found transaction hash: {transaction_hash}")
                    return transaction_hash
            except:
                continue

    except TimeoutException:
        logger.debug(f"Transaction element not found after {wait_time} seconds")
    except Exception as e:
        logger.debug(f"Error extracting transaction hash: {e}")

    return None


def claim_mon_token(driver, wallet_address):
    """
    Process for claiming MON token with complete message handling.

    Args:
        driver: WebDriver instance
        wallet_address: Ethereum wallet address to receive tokens

    Returns:
        dict: Result containing status, message, and transaction hash if successful
    """
    # Open the faucet page
    driver.get(FAUCET_URL)
    logger.debug(f"Opened tab: {FAUCET_URL}")
    # Начальное ожидание загрузки страницы
    time.sleep(2)

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            if retry_count > 0:
                logger.debug(f"Повторная попытка {retry_count}/{MAX_RETRIES}")
                driver.refresh()
                time.sleep(2)

            # Find and click the Claim $MON button
            claim_button = SeleniumUtilities.find_button_by_text(driver, 'Claim $MON')
            if SeleniumUtilities.click_safely(claim_button):
                logger.debug("Claim $MON button successfully clicked")
            else:
                logger.debug("Не удалось найти или нажать кнопку Claim $MON")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue

            # Enter the wallet address
            time.sleep(1)  # Короткое ожидание появления поля ввода
            if not input_eth_address(driver, wallet_address):
                logger.debug("Не удалось ввести ETH-адрес")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue

            # Find and click the Send button
            send_button = SeleniumUtilities.find_button_by_text(driver, 'Send')
            if SeleniumUtilities.click_safely(send_button):
                logger.debug("Send button successfully clicked")
            else:
                logger.debug("Не удалось найти или нажать кнопку Send")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue

            # Wait a moment for the result to appear
            time.sleep(3)

            # Check all message patterns first
            result = check_message_patterns(driver)

            # If the status is success, but we don't have a hash yet, try to extract it
            if result["status"] in ["success", "probable_success", "transaction"] and "transaction_hash" not in result:
                transaction_hash = extract_transaction_hash(driver)
                if transaction_hash:
                    result["transaction_hash"] = transaction_hash

            # Add wallet address to result for database storage
            result["wallet_address"] = wallet_address

            return result

        except Exception as e:
            logger.debug(f"Error in claim_mon_token: {e}")
            # Если не найдено распознаваемых сообщений
            logger.debug("Не найдено распознаваемых сообщений, повторяем попытку...")
            retry_count += 1
            time.sleep(exponential_backoff(retry_count))


def morkie_xyz(driver, mm_address):
    """
    Main wrapper function for processing the token retrieval from Morkie faucet.

    Args:
        driver: Selenium WebDriver instance
        mm_address: Ethereum address to receive tokens

    Returns:
        dict: Result of the token retrieval process
    """
    result = claim_mon_token(driver, mm_address)

    # Check if we need to handle special cases based on the result
    if result["status"] == "require_morkie_id":
        logger.debug("Morkie ID required. Redirecting to ID creation page...")
        open_tab(driver, MORKIE_ID_URL)
        open_tab(driver, "https://app.1inch.io/#/1/simple/swap/1:ETH/8453:ETH")
        return result

    return result