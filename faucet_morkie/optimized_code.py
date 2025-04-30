import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
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


# def find_element_safely(driver, by, selector, timeout=10):
#     """
#     Find an element safely without raising exceptions.
#     If timeout > 0, will wait for the element to appear, otherwise checks immediately.
#
#     Args:
#         driver: Selenium WebDriver instance
#         by: By method to locate element
#         selector: Selector string
#         timeout: Time to wait for element (seconds)
#
#     Returns:
#         WebElement if found, None otherwise
#     """
#     try:
#         if timeout > 0:
#             # Use WebDriverWait if timeout is specified
#             wait = WebDriverWait(driver, timeout)
#             return wait.until(EC.presence_of_element_located((by, selector)))
#         else:
#             # Immediate check without waiting
#             return driver.find_element(by, selector)
#     except (NoSuchElementException, TimeoutException):
#         logger.debug(f"Element '{selector}' not found after {timeout} seconds")
#         return None
#     except Exception as e:
#         logger.debug(f"Error finding element '{selector}': {e}")
#         return None
#
#
# def find_button_by_text(driver, text, timeout=10):
#     """
#      the expression is universal and can be used in any Selenium code to find buttons by text content
#      without needing to modify the XPath.
#
#     Find a button containing the specified text.
#
#     Args:
#         driver: Selenium WebDriver instance
#         text: Text to search for in button
#
#     Returns:
#         Button WebElement if found, None otherwise
#     """
#     if not text or text.strip() == "":
#         logger.debug("Empty text provided for button search")
#         return None
#
#     xpath = f"//button[contains(normalize-space(text()), '{text}')]"
#     return find_element_safely(driver, By.XPATH, xpath, timeout=timeout)


# def click_safely(element, retry_count=3, base_delay=1, jitter_range=(0.8, 1.2), exp_factor=2):
#     """
#     Attempt to click an element safely, with exponential backoff retries.
#
#     Args:
#         element: WebElement to click
#         retry_count: Number of retries if click fails
#         base_delay: Base delay between retries in seconds
#
#     Returns:
#         True if click succeeded, False otherwise
#     """
#     if not element:
#         logger.error("Element is None, cannot click")
#         return False
#
#     for attempt in range(retry_count):
#         try:
#             element.click()
#             logger.debug(f"Element clicked successfully on attempt {attempt + 1}")
#             return True
#         except ElementClickInterceptedException:
#             if attempt < retry_count - 1:
#                 # Use exponential backoff for increasing delays between retries
#                 retry_delay = base_delay * (exp_factor ** attempt)
#                 # Add some random jitter (±20%)
#                 jitter = random.uniform(*jitter_range)
#                 time.sleep(retry_delay * jitter)
#                 continue
#             else:
#                 logger.debug(f"Button click intercepted after {retry_count} attempts")
#                 return False
#         except Exception as e:
#             logger.debug(f"Error clicking element: {e}")
#             return False
#
#     return False




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
            if not pattern:
                continue

            try:
                # Using find_element_safely with timeout instead of direct WebDriverWait
                element = SeleniumUtilities.find_element_safely(driver, By.XPATH, pattern["xpath"], timeout=wait_time)

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
                element = SeleniumUtilities.find_element_safely(driver, By.XPATH, pattern["xpath"], timeout=1)

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
        SeleniumUtilities.find_element_safely(driver, By.XPATH, "//p[contains(text(), 'Transaction:')]", timeout=wait_time)

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


def claim_mon_token(driver, wallet_address, max_retries=MAX_RETRIES):
    """
    Process for claiming MON token with complete message handling.
    Implements retry logic with exponential backoff.

    Args:
        driver: WebDriver instance
        wallet_address: Ethereum wallet address to receive tokens
        max_retries: Maximum number of retry attempts

    Returns:
        dict: Result containing status, message, and transaction hash if successful
    """
    try:
        for retry in range(max_retries):
            try:
                # Open the faucet page
                driver.get(FAUCET_URL)
                logger.debug(f"Opened tab: {FAUCET_URL}")

                # Find and click the Claim $MON button (with timeout)
                claim_button = SeleniumUtilities.find_button_by_text(driver, 'Claim $MON')

                if SeleniumUtilities.click_safely(claim_button):
                    logger.debug("Claim $MON button successfully clicked")
                else:
                    logger.debug(f"Failed to click Claim button, attempt {retry + 1}/{max_retries}")
                    if retry < max_retries - 1:
                        # Calculate backoff delay for next retry
                        delay = (2 ** retry) * BASE_RETRY_DELAY * random.uniform(0.8, 1.2)
                        time.sleep(delay)
                        continue
                    return {"status": "error", "message": "Failed to click Claim button after multiple attempts"}

                # Enter the wallet address
                if not input_eth_address(driver, wallet_address):
                    logger.debug(f"Failed to enter wallet address, attempt {retry + 1}/{max_retries}")
                    if retry < max_retries - 1:
                        delay = (2 ** retry) * BASE_RETRY_DELAY * random.uniform(0.8, 1.2)
                        time.sleep(delay)
                        continue
                    return {"status": "error", "message": "Failed to enter wallet address after multiple attempts"}

                # Find and click the Send button
                send_button = SeleniumUtilities.find_button_by_text(driver, 'Send')

                if SeleniumUtilities.click_safely(send_button):
                    logger.debug("Send button successfully clicked")
                else:
                    logger.debug(f"Failed to click Send button, attempt {retry + 1}/{max_retries}")
                    if retry < max_retries - 1:
                        delay = (2 ** retry) * BASE_RETRY_DELAY * random.uniform(0.8, 1.2)
                        time.sleep(delay)
                        continue
                    return {"status": "error", "message": "Failed to click Send button after multiple attempts"}

                # Success if we get here - no need to continue retry loop
                break

            except Exception as e:
                logger.debug(f"Error during claim attempt {retry + 1}: {e}")
                if retry < max_retries - 1:
                    delay = (2 ** retry) * BASE_RETRY_DELAY * random.uniform(0.8, 1.2)
                    time.sleep(delay)
                    continue
                return {"status": "error", "message": f"Error after {max_retries} attempts: {str(e)}",
                        "wallet_address": wallet_address}

        # After successful button clicks, wait for result
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
        return {"status": "error", "message": str(e), "wallet_address": wallet_address}


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
        return result

    return result