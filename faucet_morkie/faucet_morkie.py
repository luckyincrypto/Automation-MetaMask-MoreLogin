import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from config import logger  # Локальные модули
from meta_mask import open_tab

# Функция для поиска XPath кнопки по ключевому слову
def find_xpath_btn_by_keyword(driver, keyword):
    try:
        # Ищем все кнопки <button> и проверяем, содержит ли их текст ключевое слово
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for button in buttons:
            if keyword in button.text.strip():
                # Используем JavaScript для вычисления XPath кнопки
                xpath = driver.execute_script("""
                    function getElementXPath(element) {
                        var paths = [];
                        while (element && element.nodeType === Node.ELEMENT_NODE) {
                            var index = 0;
                            var sibling = element.previousSibling;
                            while (sibling) {
                                if (sibling.nodeType === Node.ELEMENT_NODE && sibling.nodeName === element.nodeName) {
                                    index++;
                                }
                                sibling = sibling.previousSibling;
                            }
                            var tagName = element.nodeName.toLowerCase();
                            var pathIndex = (index ? "[" + (index + 1) + "]" : "");
                            paths.unshift(tagName + pathIndex);
                            element = element.parentNode;
                        }
                        return paths.length ? "/" + paths.join("/") : null;
                    }
                    return getElementXPath(arguments[0]);
                """, button)
                logger.debug(f"XPath for button containing keyword '{keyword}': {xpath}")
                return xpath
        logger.debug(f"No button with keyword '{keyword}' found.")
        return None
    except Exception as e:
        logger.debug(f"Error while finding XPath: {e}")
        return None

# Функция для поиска и нажатия кнопки "Claim $MON"
def find_claim_mon_button(driver):
    try:
        xpath = find_xpath_btn_by_keyword(driver, "Claim $MON")
        if xpath:
            button = driver.find_element(By.XPATH, xpath)
            return button
        else:
            logger.debug("Button 'Claim $MON' not found.")
            return None
    except Exception as e:
        logger.debug(f"Error in find_claim_mon_button: {e}")
        return None

# Функция для нажатия кнопки "Claim $MON"
def click_claim_mon_button(button):
    try:
        if button.is_enabled():
            button.click()
            logger.debug("Claim $MON button clicked successfully.")
            return True
        else:
            logger.debug("Claim $MON button is not enabled.")
            return False
    except Exception as e:
        logger.debug(f"Failed to click Claim $MON button. Error: {e}")
        return False

# Функция для поиска поля ввода по placeholder
def find_input_by_placeholder(driver, placeholder_text):
    try:
        # Ищем все поля ввода <input> и проверяем их атрибут placeholder
        inputs = driver.find_elements(By.TAG_NAME, "input")
        for input_field in inputs:
            if input_field.get_attribute("placeholder") == placeholder_text:
                logger.debug(f"Input field with placeholder '{placeholder_text}' found.")
                return input_field
        logger.debug(f"Input field with placeholder '{placeholder_text}' not found.")
        return None
    except Exception as e:
        logger.debug(f"Error while finding input field: {e}")
        return None

# Функция для ввода ETH Address
def input_eth_address(driver, mm_address):
    try:
        input_field = find_input_by_placeholder(driver, "EVM Address")
        if input_field:
            input_field.clear()
            input_field.send_keys(mm_address)
            logger.debug(f"ETH Address '{mm_address}' successfully entered.")
            return True
        else:
            logger.debug("Input field for address not found.")
            return False
    except Exception as e:
        logger.debug(f"Error while entering ETH address: {e}")
        return False

# Функция для поиска кнопки "Send"
def find_claim_button(driver):
    try:
        xpath = find_xpath_btn_by_keyword(driver, "Send")
        if xpath:
            button = driver.find_element(By.XPATH, xpath)
            return button
        else:
            logger.debug("Send button not found.")
            return None
    except Exception as e:
        logger.debug(f"Error in find_claim_button: {e}")
        return None

# Функция для проверки сообщения успеха
# def check_success_message(driver):
#     try:
#         xpath = "/html/body/section/div/div/section[1]/div/div[2]/p"
#         xpath = "/html/body/section/div/div/section[1]/div/p[2]"
#         success_message = WebDriverWait(driver, 10).until(
#             EC.presence_of_element_located((By.XPATH, xpath))
#         )
#         if success_message.is_displayed() and success_message.text == "Success! Check your wallet.":
#             logger.debug(f"Success message found: {success_message.text}.")
#             return success_message.text
#         else:
#             logger.debug("Unexpected success message content.")
#             return None
#     except TimeoutException:
#         logger.debug("Success message not found.")
#         return None

# Функция для проверки сообщения ограничения

def check_success_message(driver):
    try:
        # XPath для сообщения успеха
        xpath = "/html/body/section/div/div/section[1]/div/div[2]/p"
        success_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )

        # Проверка на наличие и содержание текста сообщения успеха
        if success_message.is_displayed() and success_message.text == "Success! Check your wallet.":
            logger.debug(f"Success message found: {success_message.text}.")
            return success_message.text  # Возвращаем текст сообщения
        else:
            logger.debug("Unexpected success message content.")
            return None

    except TimeoutException:
        logger.debug("Success message not found, retrying process...")
        return "retry"  # Указываем на необходимость повторного поиска

def check_transaction_message(driver):
    try:
        # XPath для сообщения о транзакции
        xpath_transaction = "/html/body/section/div/div/section[1]/div/p[3]"
        transaction_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath_transaction))
        )

        # Проверка на наличие и содержание текста сообщения транзакции
        if transaction_message.is_displayed():
            if "Transaction" in transaction_message.text:
                logger.debug(f"Transaction message found: {transaction_message.text}.")
                return transaction_message.text  # Возвращаем текст сообщения
            else:
                logger.debug("Unexpected transaction message content.")
                return None
        else:
            logger.debug("Transaction message not displayed.")
            return None

    except TimeoutException:
        logger.debug("Transaction message not found, retrying process...")
        return "retry"  # Указываем на необходимость повторного поиска

def check_limit_message(driver):
    try:
        xpath = "/html/body/section/div/div/section[1]/div/p[2]"
        limit_message = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, xpath))
        )
        if limit_message.is_displayed():
            # Проверяем на конкретное сообщение об ошибке
            if limit_message.text.startswith("Claim limit reached."):
                logger.debug(f"Limit message found: {limit_message.text}.")
                return limit_message.text
            elif limit_message.text == "Transaction failed. Please try again later.":
                logger.debug("Transaction failed message detected, retrying process...")
                return "retry"  # Специальное значение для повторного запуска процесса
            else:
                logger.debug("Unexpected limit message content.")
                return None
        else:
            logger.debug("Limit message not displayed.")
            return None
    except TimeoutException:
        logger.debug("Limit message not found.")
        return None


# Основная функция для выполнения процесса
def claim_mon_btn(driver, mm_address):
    open_tab(driver, "https://faucet.morkie.xyz/monad")
    driver.implicitly_wait(10)

    while True:
        button = find_claim_mon_button(driver)
        if button:
            button.click()
            if input_eth_address(driver, mm_address):
                claim_button = find_claim_button(driver)
                if claim_button:
                    claim_button.click()

                    # success_text = check_success_message(driver)
                    # transaction_text = check_transaction_message(driver)
                    # limit_text = check_limit_message(driver)

                    # Обработка сообщений
                    messages = {
                        "success": check_success_message(driver),
                        "transaction": check_transaction_message(driver),
                        "limit": check_limit_message(driver)
                    }
                    for key, value in messages.items():
                        if value == "retry":
                            logger.debug(f"Retrying process for {key} message...")
                            time.sleep(3)
                            continue
                        elif value:
                            logger.debug(f"{key.capitalize()} message processed: {value}")
                            return value





        logger.debug("Retrying process...")
        time.sleep(5)