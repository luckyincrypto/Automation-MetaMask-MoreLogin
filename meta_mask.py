# Стандартные библиотеки
import platform
import time
import traceback
from pprint import pprint

# Сторонние библиотеки
import pyperclip
from selenium.common import WebDriverException
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Локальные модули
from config import logger
from SeleniumUtilities.selenium_utilities import SeleniumUtilities


def compare_addresses(full_address: str, short_address: str, prefix_length: int = 4,
                      suffix_length: int = 4) -> bool:
    """
    Сравнивает полный адрес с сокращенным форматом 0x...

    :param full_address: Полный адрес (например, "0x0F8009b1dE7fF721A66Eb36c64eA11b2b8847801")
    :param short_address: Сокращенный адрес (например, "0x0F80...7801")
    :param prefix_length: Сколько символов после "0x" брать из начала
    :param suffix_length: Сколько символов брать из конца
    :return: True, если адреса совпадают по шаблону
    """
    # Проверяем базовый формат
    if not full_address.startswith("0x") or not short_address.startswith("0x"):
        return False

    # Извлекаем части из полного адреса
    clean_full = full_address[2:]  # Убираем "0x"
    prefix = clean_full[:prefix_length]
    suffix = clean_full[-suffix_length:]

    # Формируем ожидаемый сокращенный адрес
    expected_short = f"0x{prefix}...{suffix}".lower()  # Приводим к нижнему регистру для унификации

    # Приводим оба адреса к одному регистру и сравниваем
    return expected_short == short_address.lower()


class MetaMaskHelper(SeleniumUtilities):
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#"
        self.network_manager = self.NetworkManager(self.driver)

    def check_page_url(self, expected_url=None):
        """Проверяет текущий URL страницы."""
        time.sleep(3)
        current_url = self.driver.current_url
        expected = expected_url or self.base_url
        match = current_url == expected
        logger.debug(f"(check_page_url) Current URL: {current_url}, Expected: {expected}, Match: {match}")
        return match

    def check_wallet_mm(self, mm_address):
        """Проверяет адрес кошелька в MetaMask."""
        self.driver.refresh()
        self.driver.get(f"{self.base_url}")

        # Для клика в стороне модального окна, чтобы его закрыть
        # Получить размеры окна браузера
        viewport_width = self.driver.execute_script("return window.innerWidth;")
        viewport_height = self.driver.execute_script("return window.innerHeight;")

        # Вычислить координаты (25% от левого края, 25% от верха)
        x = int(viewport_width * 0.25)
        y = int(viewport_height * 0.25)

        # Добавить красную точку в вычисленных координатах
        self.driver.execute_script(f"""
            var dot = document.createElement('div');
            dot.style.position = 'absolute';
            dot.style.left = '{x}px';
            dot.style.top = '{y}px';
            dot.style.width = '10px';
            dot.style.height = '10px';
            dot.style.backgroundColor = 'red';
            dot.style.zIndex = '9999';
            document.body.appendChild(dot);
        """)
        time.sleep(5)

        # Выполнить клик
        actions_builder = ActionBuilder(self.driver, mouse=PointerInput("mouse", "default"))
        actions_builder.pointer_action.move_to_location(x, y).click()
        actions_builder.perform()
        time.sleep(1)

        try:
            copy_btn = self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="app-header-copy-button"]',
                timeout=15
            )

            if copy_btn and self.click_safely(copy_btn):
                logger.debug("(check_wallet_mm) Кнопка копирования нажата успешно")
                wallet_address = pyperclip.paste()
                return wallet_address

        except Exception as e:
            logger.error(f"(check_wallet_mm) Ошибка: {e}")
            traceback.print_exc()

        return None

    def check_mm_data_base(self, mm_address, row, workbook_mm, worksheet_mm, file_path):
        """Сравнивает адрес кошелька с базой данных и обновляет при необходимости."""
        wallet_from_extension = self.check_wallet_mm(mm_address)

        if not wallet_from_extension:
            logger.error("(check_mm_data_base) Не удалось получить адрес из расширения")
            return None

        if wallet_from_extension == mm_address:
            logger.update(f"(check_mm_data_base) Адреса совпадают: {mm_address} = {wallet_from_extension}")
            return wallet_from_extension

        # Обновление адреса в БД
        worksheet_mm.cell(row=row + 1, column=4).value = wallet_from_extension
        workbook_mm.save(file_path)

        if mm_address:
            logger.update(
                f"(check_mm_data_base) Адрес изменен. Было: {mm_address}, Стало: {wallet_from_extension}"
            )
        else:
            logger.update(
                f"(check_mm_data_base) Адрес добавлен: {wallet_from_extension} в БД."
            )

        return wallet_from_extension

    def version_mm(self):
        """Проверяет версию MetaMask."""
        self.driver.refresh()
        self.driver.get(f"{self.base_url}settings/about-us")

        version_element = self.find_element_safely(
            self.driver,
            By.CLASS_NAME,
            "info-tab__item",
            timeout=10
        )

        if version_element:
            version = version_element.text
            logger.debug(f"(version_mm) Версия MetaMask: {version}")
            return version

        logger.error("(version_mm) Не удалось определить версию")
        return None

    def open_tab(self, url):
        """Открывает новую вкладку."""
        self.driver.switch_to.new_window()
        self.driver.get(url)
        logger.debug(f"(open_tab) Открыта вкладка: {url}")

    def unlock(self):
        """Разблокировка MetaMask."""
        if not self.check_page_url(f"{self.base_url}unlock"):
            return False

        unlock_page = self.find_element_safely(
            self.driver,
            By.CSS_SELECTOR,
            '[data-testid="unlock-page"]',
            timeout=35
        )

        if unlock_page:
            logger.debug("(unlock) Страница разблокировки обнаружена")
            return True

        return False

    def onboarding_unlock(self):
        """Разблокировка MetaMask."""
        if self.check_page_url(f"{self.base_url}onboarding/unlock"):

            onboarding_unlock_page = self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="unlock-password"]',
                timeout=35
            )

            if onboarding_unlock_page:
                logger.debug("(unlock) Страница разблокировки обнаружена")
                return True

        return False

    def enter_password(self, password):
        """Ввод пароля."""
        # Ожидаем появления поля ввода
        password_field = self.find_element_safely(
            self.driver,
            By.ID,
            "password",
            timeout=10
        )
        # Вводим значение
        if password_field:
            password_field.clear()
            password_field.send_keys(password)
            logger.debug("(enter_password) Пароль введен")
            return True

        logger.error("(enter_password) Поле для пароля не найдено")
        return False

    def click_unlock_button(self):
        """Нажатие кнопки разблокировки."""
        return self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="unlock-submit"]'
            )
        )

    def check_password_error(self):
        """Проверка ошибки пароля."""
        error_msg = self.find_element_safely(
            self.driver,
            By.ID,
            "password-helper-text",
            timeout=4
        )

        if error_msg and error_msg.text:
            logger.debug(f"(check_password_error) Ошибка: {error_msg.text}")
            return True

        return False

    def click_forgot_password(self):
        """Нажатие кнопки 'Забыли пароль?'."""
        return self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CLASS_NAME,
                "unlock-page__link",
                timeout=5
            )
        )

    def handle_incorrect_password(self):
        """Обработка неверного пароля."""
        if self.check_password_error():
            if self.click_forgot_password():
                logger.debug("(handle_incorrect_password) Переход к восстановлению MetaMask по сид.")
                return True

        return False

    def fill_seed(self, seed):
        """Заполнение сид-фразы по словам в 12 полей."""
        try:
            # Разбиваем сид-фразу на отдельные слова
            seed_words = seed.split()
            if len(seed_words) != 12:
                logger.error("(fill_seed) Сид-фраза должна содержать ровно 12 слов")
                return False

            # Заполняем каждое поле отдельно
            for i in range(12):
                field = self.find_element_safely(
                    self.driver,
                    By.ID,
                    f"import-srp__srp-word-{i}"
                )
                if field:
                    field.click()  # Нажимаем на поле для очистки
                    field.clear()  # Очищаем поле (если нужно)
                    field.send_keys(seed_words[i])  # Вводим слово напрямую в поле
                    time.sleep(0.1)  # Небольшая пауза между вводом (опционально)
                else:
                    logger.error(f"(fill_seed) Не найдено поле для слова #{i + 1}")
                    return False

            logger.debug("(fill_seed) Сид-фраза успешно введена по словам")
            return True

        except Exception as e:
            logger.error(f"(fill_seed) Критическая ошибка: {e}")
            return False

    def input_seed_phrase_and_password_restore_vault(self, seed, password):
        """Восстановление кошелька с использованием сид-фразы."""
        if not self.fill_seed(seed):
            return False

        # Ввод нового пароля
        new_pass = self.find_element_safely(
            self.driver,
            By.ID,
            "password"
        )
        confirm_pass = self.find_element_safely(
            self.driver,
            By.ID,
            "confirm-password"
        )

        if new_pass and confirm_pass:
            new_pass.clear()
            new_pass.send_keys(password)
            confirm_pass.clear()
            confirm_pass.send_keys(password)
            logger.debug("(input_seed_phrase...) Пароли введены")

            # Нажатие кнопки восстановления
            return self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="create-new-vault-submit-button"]'
                )
            )

        return False

    def delete_others_windows(self):
        """Закрытие всех окон кроме текущего."""
        current_window = self.driver.current_window_handle
        for window in self.driver.window_handles:
            if window != current_window:
                self.driver.switch_to.window(window)
                self.driver.close()
        self.driver.switch_to.window(current_window)
        self.driver.get(self.base_url)

    def get_started(self):
        """Начало работы с MetaMask."""
        if not self.check_page_url(f"{self.base_url}onboarding/welcome"):
            return False


        # Проверка на наличие кнопки "Get started"

        welcome_new = self.find_element_safely(
            self.driver,
            By.CSS_SELECTOR,
            '[data-testid="onboarding-get-started-button"]',
            timeout=35
        )
        if welcome_new:
            welcome_new.click()
            logger.info('(get_started) Начало работы с MetaMask "Get started"')
            return True

        return False

    def onboard_page(self, seed, password):
        """Процесс импорта кошелька."""
        # Согласие с условиями
        if self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="terms-of-use-checkbox"]'
            )
        ):
            logger.info(f'(onboard_page) Согласие с условиями - Success')

        # Scroll down of "Review our Terms of Use"
        if self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="terms-of-use-scroll-button"]'
            )
        ):
            logger.info(f'(onboard_page) Scroll down of "Review our Terms of Use" - Success')

        # Press button "Agree"
        if self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="terms-of-use-agree-button"]'
                )
        ):
            logger.info(f'(onboard_page) Press button "Agree" - Success')

        # Press button "Agree"
        if self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="terms-of-use-agree-button"]'
                )
        ):
            logger.info(f'(onboard_page) Press button "Agree" - Success')


        # Импорт существующего кошелька
        self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="onboarding-import-wallet"]'
            )
        )

        # Отказ от метрики
        self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="metametrics-no-thanks"]'
            )
        )

        # Заполнение сид-фразы
        self.fill_seed(seed)

        # Подтверждение сид-фразы
        self.click_safely(
            self.find_element_safely(
                self.driver,
                By.CSS_SELECTOR,
                '[data-testid="import-srp-confirm"]'
            )
        )

        # Создание пароля
        new_pass = self.find_element_safely(
            self.driver,
            By.CSS_SELECTOR,
            '[data-testid="create-password-new"]'
        )
        confirm_pass = self.find_element_safely(
            self.driver,
            By.CSS_SELECTOR,
            '[data-testid="create-password-confirm"]'
        )

        if new_pass and confirm_pass:
            new_pass.clear()
            new_pass.send_keys(password)
            confirm_pass.clear()
            confirm_pass.send_keys(password)

            # Чекбокс и импорт
            self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="create-password-terms"]'
                )
            )

            self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="create-password-import"]'
                )
            )

            # Завершение
            self.click_safely(
                self.find_element_safely(
                    self.driver,
                    By.CSS_SELECTOR,
                    '[data-testid="onboarding-complete-done"]'
                )
            )

            logger.info("(onboard_page) Кошелек успешно импортирован")
            return True

        return False

    def pop_up_window_close(self):
        """Закрытие всплывающих окон."""
        try:
            got_it_btn = self.find_element_safely(
                self.driver,
                By.XPATH,
                "//button[normalize-space()]",
                # "//button[contains(text(), 'Got it')]",
                timeout=3
            )

            if got_it_btn:
                got_it_btn.click()
                logger.debug("(pop_up_window_close) Всплывающее окно закрыто")
                return True
            return None

        except Exception:
            logger.debug("(pop_up_window_close) Всплывающее окно не найдено")
            return False

    def con_eth_network_window_close(self):
        """Закрытие всплывающих окон."""
        try:
            close_btn = self.find_element_safely(
                self.driver,
                By.CLASS_NAME,
                "page-container__header-close",
                timeout=3
            )

            if close_btn:
                close_btn.click()
                logger.debug("(connect ETH network window close) Всплывающее окно закрыто")
                return True
            return None

        except Exception:
            logger.debug("(pop_up_window_close) Всплывающее окно не найдено")
            return False

    def starting_metamask(self, seed, password):
        """Основной процесс запуска MetaMask."""
        self.delete_others_windows()
        self.open_tab(f"{self.base_url}unlock")

        onboarding_welcome = 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#onboarding/welcome'

        if self.unlock():
            if self.enter_password(password) and self.click_unlock_button():
                self.pop_up_window_close()
                if self.check_page_url():
                    return True

                if self.handle_incorrect_password():
                    logger.info("(starting_metamask) Восстановление кошелька")
                    if self.input_seed_phrase_and_password_restore_vault(seed, password):
                        self.pop_up_window_close()
                        return True

        elif self.get_started():
            logger.info("(starting_metamask) Первоначальная настройка")
            if self.onboard_page(seed, password):
                if self.check_page_url(f"{self.base_url}onboarding/pin-extension"):
                    self.pop_up_window_close()
                    self.pop_up_window_close()
                    self.con_eth_network_window_close()


                time.sleep(5)
                if self.onboarding_unlock():
                    if self.enter_password(password) and self.click_unlock_button():
                        self.pop_up_window_close()
                        if self.check_page_url():
                            return True

                        if self.handle_incorrect_password():
                            logger.info("(starting_metamask) Восстановление кошелька")
                            if self.input_seed_phrase_and_password_restore_vault(seed, password):
                                self.pop_up_window_close()
                                return True
                return True

        return False

    def meta_mask(self, seed, password, mm_address, row, workbook_mm, worksheet_mm, file_path):
        """Основная функция работы с MetaMask."""
        if self.starting_metamask(seed, password):
            # self.version_mm()
            logger.update(f"Версия MM: {self.version_mm()}")
            self.pop_up_window_close()
            return self.check_mm_data_base(
                mm_address,
                row,
                workbook_mm,
                worksheet_mm,
                file_path
            )
        return None

    def handle_metamask_connection(self, driver):
        try:
            # 1. Переключаемся на последнее открытое окно
            driver.switch_to.window(driver.window_handles[-1])
            logger.info(f"Переключение на окно MetaMask, id: {driver.current_window_handle}")

            # 2. Ждем загрузки страницы
            time.sleep(3)
            text_btn = 'Connect' # Текст кнопки подключения
            button_element = SeleniumUtilities.find_button_by_text(driver, text_btn)
            if button_element:
                button_element.click()
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Ошибка подключения MetaMask: {str(e)}")
            return False


    class NetworkManager:
        """Класс для управления сетями с оригинальными селекторами"""
        # NETWORK_DISPLAY = (By.XPATH, '//*[@data-testid="network-display"]')
        NETWORK_DISPLAY = (By.XPATH, '//*[@id="app-content"]/div/div[3]/div/div/div/div[2]/div/div/div/div[1]/div/button/span[1]/div/p')
        # NETWORK_DISPLAY = (By.XPATH, "//*[@id='app-content']/div/div[contains(@class, 'mm-box') and contains(@class, 'multichain-app-header')]/div/div[1]/button/p")
        ADD_CUSTOM_NETWORK_BTN = (By.XPATH, "//button[contains(., 'Add a custom network')]")
        RPC_DROPDOWN = (By.XPATH, '//*[@data-testid="test-add-rpc-drop-down"]')
        EXPLORER_DROPDOWN = (By.XPATH, '//*[@data-testid="test-explorer-drop-down"]')
        CLOSE_BUTTON = (By.XPATH, '//button[@aria-label="Close"]')

        MAIN_FORM_FIELDS = {
            'network_name': (By.ID, "networkName"),  #
            'chain_id': (By.ID, "chainId"),  #
            'currency_symbol': (By.ID, "nativeCurrency"),  #
        }

        def __init__(self, driver):
            self.driver = driver

        def add_custom_network(self):
            """Добавление кастомной сети по оригинальному алгоритму"""
            try:
                logger.info('Шаг 3.1: Нажимаем Add a custom network')
                if not self._click_element(self.ADD_CUSTOM_NETWORK_BTN):
                    logger.debug(f' (add_custom_network), Не удачное нажатие на Add a custom network')
                    return False

                # Шаг 3: Заполняем основные поля
                logger.info('Шаг 3.2: Заполняем основные поля')
                for field, locator in self.MAIN_FORM_FIELDS.items():
                    if not self._fill_field(locator, network_config.get(field, "")):
                        logger.debug(f' (add_custom_network), Не удачное заполнение основных полей')
                        return False

                # Шаг 3.3: Обработка RPC URL
                logger.info('Шаг 3.3: Обработка RPC URL')
                if not self._process_rpc_section():
                    logger.debug(f' (add_custom_network), Не удачное обработка RPC URL')
                    return False

                # Шаг 3.4: Обработка Block Explorer
                logger.info('Шаг 3.4: Обработка Block Explorer')
                if not self._process_explorer_section():
                    logger.debug(f' (add_custom_network), Не удачное обработка Block Explorer')
                    return False

                # Шаг 6: Сохраняем
                logger.info('Шаг 3.5: Сохраняем сеть')
                if self._click_button_by_text("Save"):
                    logger.info('Сеть сохранена успешно ')
                return True

            except Exception as e:
                logger.error(f"Ошибка при добавлении сети: {str(e)}")
                return False

        def _process_rpc_section(self):
            """Обработка секции RPC"""
            if not self._click_element(self.RPC_DROPDOWN):
                return False
            logger.debug(f" (_process_rpc_section), Клик по кнопке <RPC_DROPDOWN> успешен")

            if not self._click_button_by_text("Add RPC URL"):
                return False
            logger.debug(f" (_process_rpc_section), Клик по кнопке <Add RPC URL> успешен")

            # Шаг 3.3.1: Заполняем поле RPC URL
            logger.info('Шаг 3.3.1: Заполняем поле "RPC URL"')
            if not self._fill_field((By.ID, "rpcUrl"), network_config.get('default_rpc_url')):
                logger.debug(f' (_process_rpc_section), Не удачное заполнение поля "RPC URL"')
                return False

            logger.debug(f" (_process_rpc_section), Клик по кнопке <Add URL>")
            if self._click_button_by_text("Add URL"):
                logger.debug(f" (_process_rpc_section), Клик по кнопке <Add URL> успешен")
            return True

        def _process_explorer_section(self):
            """Обработка секции Block Explorer"""
            if not self._click_element(self.EXPLORER_DROPDOWN):
                return False
            logger.debug(f" (_process_explorer_section), Клик по кнопке <EXPLORER_DROPDOWN> успешен")

            if not self._click_button_by_text("Add a block explorer URL"):
                return False
            logger.debug(f" (_process_explorer_section), Клик по кнопке <Add a block explorer URL> успешен")

            # Шаг 3.4.1: Заполняем поле RPC URL
            logger.info('Шаг 3.4.1: Заполняем поле "Add a block explorer URL"')
            block_explorer = (By.ID, "additional-rpc-url")  # locator
            if not self._fill_field(block_explorer, network_config.get('block_explorer_url')):
                logger.debug(f' (_process_explorer_section), Не удачное заполнение поля "Add a block explorer URL"')
                return False

            logger.debug(f" (_process_explorer_section), Клик по кнопке <Add URL>")
            if self._click_button_by_text("Add URL"):
                logger.debug(f" (_process_explorer_section), Клик по кнопке <Add URL> успешен")
            return True


        def _click_element(self, locator, timeout=10):
            element = SeleniumUtilities.find_element_safely(self.driver, *locator, timeout)
            if element and SeleniumUtilities.click_safely(element):
                logger.debug(f' (_click_element), Клик по кнопке успешен')
                return True
            logger.error(f' (_click_element), Клик по кнопке НЕ успешен')
            return False

        def _click_button_by_text(self, text):
            element = SeleniumUtilities.find_button_by_text(self.driver, text)
            if element and SeleniumUtilities.click_safely(element):
                logger.info(f" (_click_button_by_text), Клик по кнопке: <{text}> успешен")
                return True
            return False

        def _fill_field(self, locator, value):
            element = SeleniumUtilities.find_element_safely(self.driver, *locator)
            if element:
                element.clear()
                element.send_keys(value)
                if element.get_attribute("value") == value:
                    logger.debug(f" (_fill_field), Вставка значения: {value} успешна")
                    return True
            return False


        def try_to_find_monad_testnet(self, target_network):

            time.sleep(3)
            class_selector_show_test_networks  = "toggle-button toggle-button--off"
            el_show_test_networks = SeleniumUtilities.get_element(self.driver, class_selector_show_test_networks)

            if el_show_test_networks:
                logger.debug(f' (try_to_find_monad_testnet), Кнопка показа тестовых сетей найдена')

                el_show_test_networks.send_keys(Keys.PAGE_DOWN)  # Прокручиваем страницу вниз
                logger.debug(f' (try_to_find_monad_testnet), Прокручиваем страницу вниз 1')
                el_show_test_networks.send_keys(Keys.PAGE_DOWN)  # Прокручиваем страницу вниз
                logger.debug(f' (try_to_find_monad_testnet), Прокручиваем страницу вниз 1')
                el_show_test_networks.send_keys(Keys.PAGE_DOWN)  # Прокручиваем страницу вниз

                if SeleniumUtilities.click_safely(el_show_test_networks):
                    logger.debug(f' (try_to_find_monad_testnet), Кнопка показа тестовых сетей нажата')

            else:
                logger.warning(f' (try_to_find_monad_testnet), Кнопка показа тестовых сетей НЕ найдена')

            class_list_test_networks_block = "mm-box multichain-network-list-menu"
            main_block = SeleniumUtilities.get_elements(self.driver, class_list_test_networks_block)


            if main_block:
                logger.debug(f' (try_to_find_monad_testnet), main_block получен: {main_block}')
                res_info = SeleniumUtilities.parse_interactive_elements(main_block[0])

                el_res = res_info['elements_info']

                for el in el_res:
                    if target_network in el['text'] and el['tag_name'] == 'p':
                        logger.debug(
                            f" (ensure_monad_testnet_active), Найдена сеть: {el['text']}, в элементе с tag_name: <{el['tag_name']}>")
                        SeleniumUtilities.click_safely(el['element'])
                        logger.info(f" (ensure_monad_testnet_active), Успешно переключились на сеть: {el['text']}")
                        return True


        def ensure_monad_testnet_active(self, target_network):
            """
            Основная функция проверки и установки сети
            Возвращает:
                bool: True - сеть активна, False - ошибка
            """
            try:
                # Шаг 1: Проверка текущей активной сети
                logger.info(f"Шаг 1: Проверка текущей активной сети")
                if self.check_current_network(target_network):
                    logger.info(f" (ensure_monad_testnet_active), Сеть {target_network} уже активна")
                    return True

                time.sleep(2)
                # Шаг 2: Попытка найти сеть в списке
                logger.info(f"Шаг 2: Попытка найти в списке сетей: {target_network}")
                if self.try_to_find_monad_testnet(target_network):
                    return True

                time.sleep(2)
                # Шаг 3: Если сеть не найдена - добавляем
                logger.warning(f"Шаг 3: Сеть {target_network} не найдена, начинаем установку")
                if not self.add_custom_network():
                    logger.error("Ошибка добавления сети")
                    return False

                time.sleep(2)
                # Шаг 4: Повторная проверка после добавления
                logger.info(f"Шаг 4: Повторная проверка после добавления")
                if self.check_current_network(target_network):
                    logger.info(f" (ensure_monad_testnet_active), Сеть {target_network} активна")
                    return True
                time.sleep(2)

                # Шаг 5: Повторная попытка найти сеть в списке
                logger.info(f"Шаг 5: Повторная попытка найти {target_network} в списке сетей")
                if self.try_to_find_monad_testnet(target_network):
                    return True

                logger.error("Не удалось активировать сеть после добавления")
                return False

            except Exception as e:
                logger.error(f"Критическая ошибка: {str(e)}")
                return False

        def check_current_network(self, expected_network):
            """Проверка текущей сети с улучшенной валидацией"""
            try:
                element = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(self.NETWORK_DISPLAY)
                )
                current_network = element.text
                if expected_network in current_network:
                    logger.info(f"Текущая сеть корректна: {current_network}")
                    return True

                logger.warning(f"Обнаружена другая сеть: {current_network}, требуемая сеть: {expected_network}")
                if SeleniumUtilities.click_safely(element):
                    logger.debug(f"Клик по кнопке сети успешен")
                    css_selector = 'section[role="dialog"].mm-modal-content__dialog'
                    if SeleniumUtilities.click_safely(self.driver.find_element(By.CSS_SELECTOR, css_selector)):
                        logger.debug(f"Элемент <Select a network> найден")
                        if element.send_keys(Keys.PAGE_DOWN):  # Прокручиваем страницу вниз
                            logger.info(f"Прокрутка страницы вниз успешна")
                return False

            except Exception as e:
                logger.error(f"Ошибка проверки сети: {str(e)}")
                return False


network_config = {
    'network_name': 'Monad Testnet',
    'default_rpc_url': 'https://testnet-rpc.monad.xyz',
    'chain_id': '10143',
    'currency_symbol': 'MON',
    'block_explorer_url': 'https://testnet.monadexplorer.com'
}


def check_setup_active_network(mm, target_network):
    if mm.network_manager.ensure_monad_testnet_active(target_network):
        logger.info("Monad Testnet успешно активирована\n")
    else:
        logger.error("Не удалось активировать Monad Testnet\n")