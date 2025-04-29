import time
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from config import logger
from meta_mask import open_tab

# Константы с описательными именами
MAX_RETRIES = 5
BASE_RETRY_DELAY = 3
FAUCET_URL = "https://faucet.morkie.xyz/monad"
MORKIE_ID_URL = "https://morkie.xyz/id"

# Шаблоны сообщений для проверки различных состояний
MESSAGE_PATTERNS = {
    "success": {
        "xpath": "/html/body/section/div/div/section[1]/div/div[2]/p",
        "text": "Success! Check your wallet."
    },
    "transaction": {
        "xpath": "/html/body/section/div/div/section[1]/div/p[3]",
        "contains": "Transaction"  # Частичное совпадение
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
    }
}


def wait_for_element(driver, by, selector, timeout=10, check_visibility=True):
    """
    Wait for an element to be present/visible on the page and return it.

    Args:
        driver: Selenium WebDriver instance
        by: By method to locate element
        selector: Selector string
        timeout: Maximum wait time in seconds
        check_visibility: Whether to wait for visibility or just presence

    Returns:
        WebElement if found, None otherwise
    """
    try:
        wait = WebDriverWait(driver, timeout)
        condition = EC.visibility_of_element_located if check_visibility else EC.presence_of_element_located
        element = wait.until(condition((by, selector)))
        return element
    except TimeoutException:
        logger.debug(f"Element '{selector}' not found after {timeout} seconds")
        return None


def find_element_safely(driver, by, selector):
    """
    Find an element safely without raising exceptions.

    Args:
        driver: Selenium WebDriver instance
        by: By method to locate element
        selector: Selector string

    Returns:
        WebElement if found, None otherwise
    """
    try:
        return driver.find_element(by, selector)
    except NoSuchElementException:
        logger.debug(f"Element '{selector}' not found")
        return None
    except Exception as e:
        logger.debug(f"Error finding element '{selector}': {e}")
        return None


def find_button_by_text(driver, text):
    """
    Find a button containing the specified text.

    Args:
        driver: Selenium WebDriver instance
        text: Text to search for in button

    Returns:
        Button WebElement if found, None otherwise
    """
    xpath = f"//button[contains(text(), '{text}')]"
    return find_element_safely(driver, By.XPATH, xpath)


def click_safely(element, retry_count=3, delay=1):
    """
    Attempt to click an element safely, with retries.

    Args:
        element: WebElement to click
        retry_count: Number of retries if click fails
        delay: Delay between retries in seconds

    Returns:
        True if click succeeded, False otherwise
    """
    if not element:
        return False

    for attempt in range(retry_count):
        try:
            element.click()
            return True
        except ElementClickInterceptedException:
            if attempt < retry_count - 1:
                time.sleep(delay)
            else:
                logger.debug(f"Button click intercepted after {retry_count} attempts")
                return False
        except Exception as e:
            logger.debug(f"Error clicking element: {e}")
            return False


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
            "//input[contains(@placeholder, 'Address')]",
            "//div[contains(@class, 'address-input')]//input"
        ]

        for selector in selectors:
            input_field = find_element_safely(driver, By.XPATH, selector)
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


def check_success_message_combo(driver):
    """
    Проверяет комбинацию сообщений об успехе и транзакции.

    Args:
        driver: Экземпляр Selenium WebDriver

    Returns:
        Текст сообщения об успехе, если найдено, иначе None
    """
    # Сначала проверяем сообщение об успехе
    success_pattern = MESSAGE_PATTERNS["success"]
    success_element = wait_for_element(driver, By.XPATH, success_pattern["xpath"], timeout=5)

    if success_element and success_element.text == success_pattern["text"]:
        # Если нашли успех, проверяем наличие информации о транзакции
        transaction_pattern = MESSAGE_PATTERNS["transaction"]
        transaction_element = find_element_safely(driver, By.XPATH, transaction_pattern["xpath"])

        if transaction_element and transaction_pattern["contains"] in transaction_element.text:
            logger.debug(f"Найдена комбинация сообщений об успехе и транзакции: '{success_element.text}'")
            return success_element.text
        else:
            logger.debug(f"Найдено сообщение об успехе, но без информации о транзакции: '{success_element.text}'")
            return success_element.text

    return None


def check_message(driver, message_type):
    """
    Проверяет наличие различных типов сообщений на странице.

    Args:
        driver: Экземпляр Selenium WebDriver
        message_type: Тип сообщения для проверки

    Returns:
        Текст сообщения, если найдено, иначе None
    """
    # Специальная обработка для типа "success", которая также проверяет "transaction"
    if message_type == "success":
        return check_success_message_combo(driver)

    if message_type not in MESSAGE_PATTERNS:
        logger.debug(f"Неизвестный тип сообщения: {message_type}")
        return None

    pattern = MESSAGE_PATTERNS[message_type]
    element = wait_for_element(driver, By.XPATH, pattern["xpath"], timeout=5)

    if not element:
        return None

    message_text = element.text

    # Применяем различные стратегии сопоставления в зависимости от типа шаблона
    if "text" in pattern and message_text == pattern["text"]:
        logger.debug(f"Точное совпадение для {message_type}: '{message_text}'")
        return message_text
    elif "contains" in pattern and pattern["contains"] in message_text:
        logger.debug(f"Частичное совпадение для {message_type}: '{message_text}'")
        return message_text
    elif "starts_with" in pattern and message_text.startswith(pattern["starts_with"]):
        logger.debug(f"Совпадение по префиксу для {message_type}: '{message_text}'")
        return message_text

    logger.debug(
        f"Элемент сообщения найден, но содержимое не соответствует шаблону для {message_type}: '{message_text}'")
    return None


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
    import random
    delay = min(base_delay * (2 ** retry_count), max_delay)
    # Add jitter (±20%)
    jitter = random.uniform(0.8, 1.2)
    return delay * jitter


def claim_mon_faucet(driver, mm_address):
    """
    Основная функция для получения токенов $MON с фаусета.

    Args:
        driver: Экземпляр Selenium WebDriver
        mm_address: Ethereum-адрес для получения токенов

    Returns:
        Сообщение о результате при успехе, None в противном случае
    """
    logger.debug(f"Начинаем процесс получения токенов для адреса: {mm_address}")
    open_tab(driver, FAUCET_URL)

    # Начальное ожидание загрузки страницы
    time.sleep(2)

    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            # Обновляем страницу только при повторных попытках (не при первой)
            if retry_count > 0:
                logger.debug(f"Повторная попытка {retry_count}/{MAX_RETRIES}")
                driver.refresh()
                time.sleep(2)

            # Шаг 1: Находим и нажимаем кнопку "Claim $MON" с использованием find_button_by_text
            claim_button = find_button_by_text(driver, "Claim $MON")
            if not claim_button or not click_safely(claim_button):
                logger.debug("Не удалось найти или нажать кнопку Claim $MON")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue
            logger.debug("Кнопка Claim $MON успешно нажата")

            # Шаг 2: Вводим ETH-адрес
            time.sleep(1)  # Короткое ожидание появления поля ввода
            if not input_eth_address(driver, mm_address):
                logger.debug("Не удалось ввести ETH-адрес")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue

            # Шаг 3: Находим и нажимаем кнопку Send с использованием find_button_by_text
            send_button = find_button_by_text(driver, "Send")
            if not send_button or not click_safely(send_button):
                logger.debug("Не удалось найти или нажать кнопку Send")
                retry_count += 1
                time.sleep(exponential_backoff(retry_count))
                continue
            logger.debug("Кнопка Send успешно нажата")

            # Шаг 4: Проверяем различные типы сообщений
            time.sleep(2)  # Ожидание сообщения о результате

            # Сначала проверяем комбинацию успеха, потом остальные сообщения
            # Приоритетный порядок проверки сообщений
            result = check_message(driver, "success")
            if result:
                logger.debug(f"Найдено сообщение об успехе: {result}")
                return result

            message_types = ["require_morkie_id", "limit_reached", "failed"]

            for msg_type in message_types:
                result = check_message(driver, msg_type)
                if result:
                    logger.debug(f"Найден тип сообщения '{msg_type}': {result}")
                    return result

            # Если не найдено распознаваемых сообщений
            logger.debug("Не найдено распознаваемых сообщений, повторяем попытку...")
            retry_count += 1
            time.sleep(exponential_backoff(retry_count))

        except Exception as e:
            logger.debug(f"Неожиданная ошибка в процессе получения токенов: {e}")
            retry_count += 1
            time.sleep(exponential_backoff(retry_count))

    logger.debug(f"Достигнуто максимальное количество попыток ({MAX_RETRIES}) без успеха")
    return None


def morkie_xyz(driver, mm_address):
    """
    Основная функция-обертка для обработки процесса получения токенов из фаусета Morkie.

    Args:
        driver: Экземпляр Selenium WebDriver
        mm_address: Ethereum-адрес для получения токенов

    Returns:
        Результат процесса получения токенов
    """
    result = claim_mon_faucet(driver, mm_address)

    # Если требуется Morkie ID, перенаправляем на страницу создания ID
    if result == 'You need a Morkie ID to claim faucet.':
        logger.debug("Требуется Morkie ID. Перенаправляем на страницу создания ID...")
        open_tab(driver, MORKIE_ID_URL)
        return {"status": "requires_morkie_id", "message": result}

    # Обрабатываем другие случаи результатов
    if result and "Success" in result:
        return {"status": "success", "message": result}
    elif result and "limit reached" in result:
        return {"status": "limit_reached", "message": result}
    elif result and "Transaction" in result:
        return {"status": "transaction_in_progress", "message": result}
    else:
        return {"status": "failed", "message": result or "Произошла неизвестная ошибка"}