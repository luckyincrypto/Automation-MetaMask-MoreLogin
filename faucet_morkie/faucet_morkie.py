import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from config import logger  # Локальные модули
from meta_mask import open_tab

# Константы
MAX_RETRIES = 5
BASE_RETRY_DELAY = 3
FAUCET_URL = "https://faucet.morkie.xyz/monad"


# Функция для поиска элемента с ожиданием
def wait_for_element(driver, by, selector, timeout=10, check_visibility=True):
    """Ожидает появления элемента и возвращает его"""
    try:
        wait = WebDriverWait(driver, timeout)
        if check_visibility:
            element = wait.until(EC.visibility_of_element_located((by, selector)))
        else:
            element = wait.until(EC.presence_of_element_located((by, selector)))
        return element
    except TimeoutException:
        logger.debug(f"Element {selector} not found after {timeout} seconds")
        return None


# Функция для поиска кнопки по тексту - более простой подход
def find_button_by_text(driver, text):
    """Находит кнопку, содержащую указанный текст"""
    try:
        # XPath селектор для поиска кнопки, содержащей текст
        xpath = f"//button[contains(text(), '{text}')]"
        return driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        logger.debug(f"Button with text '{text}' not found.")
        return None
    except Exception as e:
        logger.debug(f"Error finding button with text '{text}': {e}")
        return None


# Функция для ввода ETH адреса
def input_eth_address(driver, mm_address):
    """Вводит ETH адрес в поле с placeholder 'EVM Address'"""
    try:
        # Поиск по атрибуту placeholder
        input_field = driver.find_element(By.XPATH, "//input[@placeholder='EVM Address']")
        input_field.clear()
        input_field.send_keys(mm_address)
        logger.debug(f"ETH Address '{mm_address}' successfully entered.")
        return True
    except NoSuchElementException:
        logger.debug("Input field for address not found.")
        return False
    except Exception as e:
        logger.debug(f"Error while entering ETH address: {e}")
        return False


# Объединенная функция для проверки различных сообщений
def check_message(driver, message_type):
    """Проверяет наличие различных типов сообщений"""
    xpaths = {
        "success": "/html/body/section/div/div/section[1]/div/div[2]/p",
        "transaction": "/html/body/section/div/div/section[1]/div/p[3]",
        "limit": "/html/body/section/div/div/section[1]/div/p[2]"
    }

    expected_texts = {
        "success": "Success! Check your wallet.",
        "transaction": "Transaction",  # Частичное совпадение
        "limit": "Claim limit reached."  # Начало сообщения
    }

    retry_texts = {
        "limit": "Transaction failed. Please try again later."
    }

    try:
        xpath = xpaths.get(message_type)
        if not xpath:
            logger.debug(f"Unknown message type: {message_type}")
            return None

        message_element = wait_for_element(driver, By.XPATH, xpath)
        if not message_element:
            return None

        message_text = message_element.text

        # Проверка на сообщение для повторной попытки
        if message_type in retry_texts and message_text == retry_texts[message_type]:
            logger.debug(f"Retry message detected: {message_text}")
            return "retry"

        # Проверка на ожидаемый текст сообщения
        expected = expected_texts.get(message_type)
        if expected:
            if message_type == "transaction" and expected in message_text:
                logger.debug(f"{message_type.capitalize()} message found: {message_text}")
                return message_text
            elif message_type == "limit" and message_text.startswith(expected):
                logger.debug(f"{message_type.capitalize()} message found: {message_text}")
                return message_text
            elif message_text == expected:
                logger.debug(f"{message_type.capitalize()} message found: {message_text}")
                return message_text

        logger.debug(f"Unexpected {message_type} message content: {message_text}")
        return None

    except TimeoutException:
        logger.debug(f"{message_type.capitalize()} message not found")
        return None
    except Exception as e:
        logger.debug(f"Error checking {message_type} message: {e}")
        return None


# Основная функция для выполнения процесса
def claim_mon_Faucet_Portal(driver, mm_address):
    """Выполняет процесс получения токенов с faucet.morkie.xyz"""
    open_tab(driver, FAUCET_URL)
    driver.implicitly_wait(5)  # Уменьшено время ожидания для оптимизации

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Поиск и нажатие кнопки "Claim $MON"
            claim_mon_button = find_button_by_text(driver, "Claim $MON")
            if not claim_mon_button:
                logger.debug("Claim $MON button not found, retrying...")
                retry_count += 1
                time.sleep(BASE_RETRY_DELAY)
                continue

            claim_mon_button.click()
            logger.debug("Claim $MON button clicked")

            # Ввод ETH адреса
            if not input_eth_address(driver, mm_address):
                logger.debug("Failed to input ETH address, retrying...")
                retry_count += 1
                time.sleep(BASE_RETRY_DELAY)
                continue

            # Поиск и нажатие кнопки Send
            send_button = find_button_by_text(driver, "Send")
            if not send_button:
                logger.debug("Send button not found, retrying...")
                retry_count += 1
                time.sleep(BASE_RETRY_DELAY)
                continue

            send_button.click()
            logger.debug("Send button clicked")

            # Проверка различных сообщений
            message_types = ["success", "transaction", "limit"]
            for msg_type in message_types:
                result = check_message(driver, msg_type)
                if result == "retry":
                    logger.debug(f"Need to retry due to {msg_type} message")
                    break
                elif result:
                    logger.debug(f"Successful {msg_type} message: {result}")
                    return result

            # Если мы дошли сюда, значит нужно повторить попытку
            logger.debug("No definitive message found, retrying...")
            retry_count += 1
            # Экспоненциальная задержка для избежания блокировки
            time.sleep(BASE_RETRY_DELAY * (2 ** retry_count / 2))

        except Exception as e:
            logger.debug(f"Error in claim process: {e}")
            retry_count += 1
            time.sleep(BASE_RETRY_DELAY * retry_count)

    logger.debug(f"Max retries ({MAX_RETRIES}) reached without success")
    return None
