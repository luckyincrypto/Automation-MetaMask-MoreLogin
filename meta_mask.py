# Стандартные библиотеки
import platform
import time
import traceback

# Сторонние библиотеки
import pyperclip
from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.common.by import By

# Локальные модули
from config import logger
from SeleniumUtilities.selenium_utilities import SeleniumUtilities


class MetaMaskHelper(SeleniumUtilities):
    def __init__(self, driver):
        self.driver = driver
        self.base_url = "chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#"

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
        """Заполнение сид-фразы."""
        try:
            fields = [
                self.find_element_safely(
                    self.driver,
                    By.ID,
                    f"import-srp__srp-word-{i}"
                ) for i in range(12)
            ]

            if all(fields):
                if platform.system() == "Darwin":
                    keys = Keys.COMMAND
                else:
                    keys = Keys.CONTROL

                pyperclip.copy(seed)
                ActionChains(self.driver).key_down(keys).send_keys("v").key_up(keys).perform()
                logger.debug("(fill_seed) Сид-фраза вставлена")
                return True

        except Exception as e:
            logger.error(f"(fill_seed) Ошибка: {e}")

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

        welcome = self.find_element_safely(
            self.driver,
            By.CLASS_NAME,
            "onboarding-welcome",
            timeout=35
        )

        if welcome:
            logger.info("(get_started) Начало работы с MetaMask")
            return True

        return False

    def onboard_page(self, seed, password):
        """Процесс импорта кошелька."""
        # Согласие с условиями
        self.click_safely(
            self.find_element_safely(
                self.driver,
                By.ID,
                "onboarding__terms-checkbox"
            )
        )

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
                "//button[contains(text(), 'Got it')]",
                timeout=3
            )

            if got_it_btn:
                got_it_btn.click()
                logger.debug("(pop_up_window_close) Всплывающее окно закрыто")
                return True

        except Exception:
            logger.debug("(pop_up_window_close) Всплывающее окно не найдено")
            return False

    def starting_metamask(self, seed, password):
        """Основной процесс запуска MetaMask."""
        self.delete_others_windows()
        self.open_tab(f"{self.base_url}unlock")

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
                self.pop_up_window_close()
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


