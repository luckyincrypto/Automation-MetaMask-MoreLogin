import platform
import time
import traceback
import pyperclip

from selenium.webdriver import ActionChains, Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common import NoSuchElementException
from selenium.common.exceptions import WebDriverException

from config import logger


def check_wallet_mm(driver, mm_address):
    driver.refresh()
    url_version_mm = 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#'
    driver.get(url=url_version_mm)
    try:
        data_testid = "app-header-copy-button"
        path_css_selector = f'[data-testid={data_testid}]'
        logger.debug(f' (check_wallet_mm) Проверяем страницу на btn [Copy to clipboard]')
        driver.implicitly_wait(10)
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
        logger.debug(f' (check_wallet_mm) Btn [Copy to clipboard] pressed success')
        wallet_mm_from_brauser_extension = pyperclip.paste()
        return wallet_mm_from_brauser_extension
    except Exception:
        traceback.print_exc()
        logger.error(f' (check_wallet_mm) Btn [Copy to clipboard] Exception')

def check_mm_data_base(driver, mm_address, row, workbook_mm, worksheet_mm, FILE_PATH):
    wallet_mm_from_browser_extension = check_wallet_mm(driver, mm_address)
    if wallet_mm_from_browser_extension == mm_address:
        logger.warning(f' (check_wallet_mm) Адреса в БД и в расширениях браузера МетаМаск совпадают. OK!')
        return wallet_mm_from_browser_extension
    elif mm_address and wallet_mm_from_browser_extension and mm_address != wallet_mm_from_browser_extension:
        logger.warning(
            f' (check_mm_data_base) Profile №: {row}, Адреса в БД: {mm_address} и в расширениях браузера МетаМаск: {wallet_mm_from_browser_extension} НЕ совпадают.\n'
            f' Адрес ETH wallet автоматически будет исправлен в базе данных.\n')
        worksheet_mm.cell(row=row + 1, column=4).value = wallet_mm_from_browser_extension
        workbook_mm.save(FILE_PATH)
        logger.warning(f' (check_mm_data_base) Profile №: {row}, Адрес МетаМаск в БД исправлен!')
        return wallet_mm_from_browser_extension
    else:
        if not mm_address and wallet_mm_from_browser_extension:
            logger.warning(f' (check_mm_data_base) Profile №: {row}, Адрес МетаМаск в БД отсутствует')
            worksheet_mm.cell(row=row + 1, column=4).value = wallet_mm_from_browser_extension
            workbook_mm.save(FILE_PATH)
            logger.warning(f' (check_mm_data_base) Profile №: {row}, Адрес МетаМаск в БД добавлен!')
            return wallet_mm_from_browser_extension

def version_mm(driver):
    driver.refresh()
    url_version_mm = 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#settings/about-us'
    driver.get(url=url_version_mm)
    def check_version_mm(driver):
        try:
            path_class_name = "info-tab__item"
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, path_class_name)))
            metamask_version = driver.find_element(By.CLASS_NAME, path_class_name).text
            logger.warning(f' (version_mm) MetaMask msg: {metamask_version}')
            return metamask_version
        except Exception:
            logger.error(f' (version_mm) check_version_mm Exception')
            return False
    check_version_mm(driver)

def open_tab(driver, url):
    driver.switch_to.new_window()
    driver.get(url=url)
    logger.debug(f' (open_tab) tab is open: {url} ')

def unlock(driver):
    if check_page_url(driver, url='chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#unlock'):
        try:
            data_testid = "unlock-page"
            path_css_selector = f'[data-testid={data_testid}]'
            # Ожидание видимости элемента
            logger.debug(f' (unlock) Waiting for unlock-page')
            if WebDriverWait(driver, 35).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, path_css_selector))
            ):
                # phrase = element.text
                logger.debug(f' (unlock) True')
                return True

        except NoSuchElementException as e:
            traceback.print_exc()
            logger.error(f" (unlock) NoSuchElementException: {e}")
        except WebDriverException as e:
            traceback.print_exc()
            logger.error(f' (unlock) WebDriverException: {e}')
    else:
        return False

def enter_password(driver, password):
    try:
        # Ожидаем появления поля ввода
        password_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        # Вводим значение
        password_field.clear()
        password_field.send_keys(password)
        logger.debug(f' (enter_password) Password успешно введен: {password}')
        return True
    except Exception as e:
        logger.error(f' (enter_password) Ошибка при вводе пароля: {e}')
        return False


def click_unlock_button(driver):
    try:
        unlock_button = driver.find_element(By.CSS_SELECTOR, '[data-testid="unlock-submit"]')
        # Нажатие на кнопку
        unlock_button.click()
        logger.debug(" (click_unlock_button) Кнопка [Unlock] успешно нажата")
        return True
    except Exception as e:
        logger.error(f" (click_unlock_button) Exception")
        return False


def check_page_url(driver, url='chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#' ):
    # Получаем текущий URL
    time.sleep(3)
    current_url = driver.current_url
    if current_url == url:
        logger.debug(f' (check_page_url), current_url True: {current_url}')
        return True
    else:
        logger.debug(f' (check_page_url), current_url False: {current_url}')
        return False



def check_password_error(driver):
    if check_page_url(driver):
        return True
    else:
        try:
            # Ожидаем появления ввода неправильного пароля.
            logger.debug(" (check_password_error) Проверяем наличие правильного пароля...")
            error_message = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.ID, "password-helper-text"))
            )
            # Проверяем текст ошибки
            logger.debug(f' (check_password_error) answer msg: {error_message.text}')
            if error_message.text:
                logger.debug(" (check_password_error) Обнаружен неправильный пароль!")
                return False
        except Exception:
            logger.error(" (check_password_error) Exception.")


def click_forgot_password(driver):
    try:
        # Ожидание кликабельности кнопки
        forgot_password_button = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.CLASS_NAME, "unlock-page__link"))
        )
        forgot_password_button.click()
        logger.debug(" (click_forgot_password) Кнопка [Forgot password?] успешно нажата")
        return True
    except Exception:
        logger.error(f"(click_forgot_password) Exception")
        return False

def handle_incorrect_password(driver):
    if not check_password_error(driver):
        logger.debug(" (handle_incorrect_password) Ошибка пароля обнаружена, нажимаем [Forgot password?]...")
        if click_forgot_password(driver):
            logger.debug(" (handle_incorrect_password) Нажата кнопка [Forgot password?] успешно.")
            return True
        else:
            logger.error(" (handle_incorrect_password) Не удалось нажать на [Forgot password?].")
    else:
        logger.debug(" (handle_incorrect_password) Вход в MetaMask успешен.")
        return False

def fill_seed(driver, seed):
    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, 'import-srp__srp-word-0')))
        xpath = '//*[@class="MuiInputBase-input MuiInput-input"]'
        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, xpath))).click()
        logger.debug(f' (fill_seed) click, OK')
    except NoSuchElementException as e:
        logger.error(f' (fill_seed) exception')

    # Определение ОС пользователя
    if platform.system() == 'Darwin':
        # Mac operating system
        pyperclip.copy(seed)
        ActionChains(driver).key_down(u'\ue03d').send_keys('v').key_up(u'\ue03d').perform()
        logger.debug(f' (fill_seed) paste, OK')
    else:
        try:
            pyperclip.copy(seed)
            ActionChains(driver).key_down(Keys.CONTROL).send_keys('v').key_up(Keys.CONTROL).perform()
            logger.debug(f' (fill_seed) input, OK')
        except Exception:
            logger.error(" (fill_seed) Exception")

def input_seed_phrase_and_password_restore_vault(driver, seed, password):

    fill_seed(driver, seed)

    def input_password(driver, password):
        def new_password(driver, password):
            try:
                # Ожидаем появления поля ввода New password
                path_id = "password"
                seed_phrase_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, path_id))
                )
                logger.debug(f" (input_password) New password field exists")
                # Вводим значение
                seed_phrase_input.clear()
                seed_phrase_input.send_keys(password)
                logger.debug(f" (new_password) New password успешно введен: {password}")
                return True
            except Exception:
                logger.error(f" (new_password) Exception")

        new_password(driver, password)

        def confirm_password(driver, password):
            try:
                # Ожидаем появления поля ввода Confirm password
                path_id = "confirm-password"
                seed_phrase_input = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, path_id))
                )
                logger.debug(f" (confirm_password) Confirm password field exists")
                # Вводим значение
                seed_phrase_input.clear()
                seed_phrase_input.send_keys(password)
                logger.debug(f" (confirm_password) Confirm password успешно введен: {password}")
                return True
            except Exception:
                logger.error(f" (confirm_password) Exception")

        confirm_password(driver, password)

    input_password(driver, password)

    def click_restore_button(driver):
        try:
            # Ожидание кликабельности кнопки Restore
            path_data_testid = '[data-testid="create-new-vault-submit-button"]'
            forgot_password_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, path_data_testid))
            )
            logger.debug(f" (click_restore_button) [Restore] btn exists")
            forgot_password_button.click()
            logger.debug(" (click_restore_button) Кнопка [Restore] успешно нажата")
            return True
        except Exception:
            logger.error(f" (click_restore_button) Exception")
        return False

    click_restore_button(driver)

def delete_others_windows(driver):
    """Удаление других окон."""
    current_window = driver.current_window_handle
    windows = driver.window_handles
    for window in windows:
        if window != current_window:
            driver.switch_to.window(window)
            driver.close()
    driver.switch_to.window(current_window)

def get_started(driver, env_id):
    if check_page_url(driver, url='chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#onboarding/welcome'):
        logger.debug(" (get_started), on page: Let's get started")
        delete_others_windows(driver)
        driver.refresh()
        try:
            path_class = 'onboarding-welcome'
            if WebDriverWait(driver, 35).until(EC.visibility_of_element_located((By.CLASS_NAME, path_class))):
                logger.info(" (get_started) onboarding-welcome page. Let's get started...")
                return True
        except NoSuchElementException as e:
            traceback.print_exc()
            logger.error(f" (get_started) NoSuchElementException: {e}")
        except WebDriverException as e:
            traceback.print_exc()
            logger.error(f' (get_started) WebDriverException: {e}')

def onboard_page(driver, seed, password):  # Import exist wallet
    def agree_checkbox(driver):
        try:  # checkbox: I agree to MetaMask's Terms of use
            path_id = "onboarding__terms-checkbox"
            logger.debug(f' (agree_checkbox) Проверяем страницу на присутствие checkbox: {path_id}')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, path_id))).click()
            logger.debug(f' (agree_checkbox) Checkbox was checked')
            return True
        except Exception:
            logger.error(f' (agree_checkbox) Exception')

    agree_checkbox(driver)

    def click_on_import_exist_wallet(driver):
        try:  # Press btn [Import exist wallet]
            data_testid = "onboarding-import-wallet"
            path_css_selector = f'[data-testid={data_testid}]'
            logger.debug(f' (click_on_import_exist_wallet) Проверяем страницу на присутствие btn [Import exist wallet]')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
            logger.debug(f' (click_on_import_exist_wallet) Нажали кнопку btn [Import exist wallet]')
        except Exception:
            logger.error(f' (click_on_import_exist_wallet) Exception')

    click_on_import_exist_wallet(driver)

    def metametrics(driver):
        try:  # Button [No thanks]
            data_testid = "metametrics-no-thanks"
            path_css_selector = f'[data-testid={data_testid}]'
            logger.debug(f' (metametrics) Проверяем страницу на присутствие btn [No thanks]')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
            logger.debug(f' (metametrics) Нажали кнопку btn [No thanks]')
        except Exception:
            logger.error(f' (metametrics) Exception')

    metametrics(driver)

    fill_seed(driver, seed)  # Input seed phrase

    def btn_confirm_secret_recovery_phrase(driver):  # Button [Confirm Secret Recovery Phrase]
        try:
            data_testid = "import-srp-confirm"
            path_css_selector = f'[data-testid={data_testid}]'
            logger.debug(f' (btn_confirm_secret_recovery_phrase) Проверяем страницу на присутствие btn [Confirm Secret Recovery Phrase]')
            WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
            logger.debug(f' (btn_confirm_secret_recovery_phrase) Нажали кнопку btn [Confirm Secret Recovery Phrase]')
        except Exception:
            logger.error(f' (btn_confirm_secret_recovery_phrase) Exception')

    btn_confirm_secret_recovery_phrase(driver)

    def onboarding_create_password(driver, password):
        def onboarding_create_password_check_page(driver):
            try:
                data_testid = "create-password"
                path_css_selector = f'[data-testid={data_testid}]'
                # Ожидание видимости элемента
                if WebDriverWait(driver, 10).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, path_css_selector))).text:
                    logger.debug(f' (onboarding_create_password_check_page) On page onboarding/create-password exists')
                    return True
            except Exception:
                logger.error(f' (onboarding_create_password_check_page) Exception')
                return False

        if onboarding_create_password_check_page(driver):
            def input_password(driver, password):
                def new_password(driver, password):
                    try:
                        # Ожидаем появления поля ввода New password
                        data_testid = "create-password-new"
                        path_css_selector = f'[data-testid={data_testid}]'
                        logger.debug(f' (new_password) Проверяем страницу на присутствие поля ввода New password')
                        new_password_input = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, path_css_selector)))
                        # Вводим значение
                        new_password_input.clear()
                        new_password_input.send_keys(password)
                        logger.debug(f" (new_password) New password успешно введен: {password} onboarding/create-password")
                        return True
                    except Exception:
                        logger.error(f" (new_password) Exception")

                new_password(driver, password)

                def confirm_password(driver, password):
                    try:
                        # Ожидаем появления поля ввода Confirm password
                        data_testid = "create-password-confirm"
                        path_css_selector = f'[data-testid={data_testid}]'
                        logger.debug(f' (confirm_password) Проверяем страницу на присутствие поля ввода Confirm password')
                        confirm_password_input = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, path_css_selector)))
                        # Вводим значение
                        confirm_password_input.clear()
                        confirm_password_input.send_keys(password)
                        logger.debug(f" (confirm_password) Confirm password успешно введен: {password} onboarding/create-password")
                        return True
                    except Exception:
                        logger.error(f" (confirm_password) Exception")

                confirm_password(driver, password)

            input_password(driver, password)

            def checkbox_mm_cannot_recover(driver):
                try:
                    data_testid = 'create-password-terms'
                    path_css_selector = f'[data-testid={data_testid}]'
                    logger.debug(f' (checkbox_mm_cannot_recover) Проверяем страницу на присутствие btn [Import exist wallet]')
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
                except Exception:
                    logger.error(f' (checkbox_mm_cannot_recover) Exception')

            checkbox_mm_cannot_recover(driver)

            def click_import_my_wallet_btn(driver):
                try:
                    data_testid = 'create-password-import'
                    path_css_selector = f'[data-testid={data_testid}]'
                    logger.debug(f' (click_import_my_wallet_btn) Проверяем страницу на присутствие btn [Import my wallet]')
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
                    logger.debug(f' (click_import_my_wallet_btn) Нажали кнопку [Import my wallet]')
                except Exception:
                    logger.error(f' (click_import_my_wallet_btn) Exception')

            click_import_my_wallet_btn(driver)

            def your_wallet_is_ready_check_page(driver):  # Your wallet is ready
                try:
                    data_testid = "creation-successful"
                    path_css_selector = f'[data-testid={data_testid}]'
                    # Ожидание видимости элемента
                    logger.debug(f' (your_wallet_is_ready_check_page) Checking on page onboarding/completion')
                    if WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, path_css_selector))).text:
                        logger.debug(f' (your_wallet_is_ready_check_page) Page onboarding/completion exists')
                        return True
                except Exception:
                    logger.error(f' (your_wallet_is_ready_check_page) Exception')
                    return False

            if your_wallet_is_ready_check_page(driver):
                def click_on_done_btn(driver):
                    try:
                        data_testid = "onboarding-complete-done"
                        path_css_selector = f'[data-testid={data_testid}]'
                        logger.debug(f' (click_on_done_btn) Проверяем страницу на присутствие btn [Done]')
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
                        logger.debug(f' (click_on_done_btn) Нажали кнопку btn [Done]')
                    except Exception:
                        logger.error(f' (click_on_done_btn) Exception')

                click_on_done_btn(driver)

            def pin_extension_check_page(driver):
                try:
                    data_testid = "onboarding-pin-extension"
                    path_css_selector = f'[data-testid={data_testid}]'
                    # Ожидание видимости элемента
                    logger.debug(f' (pin_extension_check_page) Checking on page onboarding/pin-extension')
                    if WebDriverWait(driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, path_css_selector))).text:
                        logger.debug(f' (pin_extension_check_page) Page onboarding/pin-extension exists')
                        return True
                except Exception:
                    logger.error(f' (pin_extension_check_page) Exception')
                    return False

            pin_extension_check_page(driver)

            if pin_extension_check_page(driver):
                def click_on_pin_extension_btn_next(driver):  # pin-extension btn [Next]
                    try:
                        data_testid = "pin-extension-next"
                        path_css_selector = f'[data-testid={data_testid}]'
                        logger.debug(f' (click_on_pin_extension_btn_next) Проверяем страницу на присутствие btn [Next]')
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
                        logger.debug(f' (click_on_pin_extension_btn_next) Нажали кнопку btn [Next]')
                    except Exception:
                        logger.error(f' (click_on_pin_extension_btn_next) Exception')

                click_on_pin_extension_btn_next(driver)

                def click_on_pin_extension_btn_done(driver):  # pin-extension btn [Done]
                    try:
                        data_testid = "pin-extension-done"
                        path_css_selector = f'[data-testid={data_testid}]'
                        logger.debug(f' (click_on_pin_extension_btn_done) Проверяем страницу на присутствие btn [Done]')
                        WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.CSS_SELECTOR, path_css_selector))).click()
                        logger.debug(f' (click_on_pin_extension_btn_done) Нажали кнопку btn [Done]')
                    except Exception:
                        logger.error(f' (click_on_pin_extension_btn_done) Exception')

                click_on_pin_extension_btn_done(driver)

            logger.info(" (onboarding_create_password_check_page) Successfully imported wallet!")


    onboarding_create_password(driver, password)


def starting_metamask(driver, seed, password, env_id):
    delete_others_windows(driver)
    open_tab(driver, 'chrome-extension://nkbihfbeogaeaoehlefnkodbefgpgknn/home.html#unlock')
    logger.debug(' (starting_metamask) open_tab: unlock opened')

    if unlock(driver):
        logger.info(' (starting_metamask), (unlock), Welcome back! ')
        enter_password(driver, password)
        logger.debug(' (starting_metamask), (unlock), enter_password entered')
        click_unlock_button(driver)
        logger.debug(' (starting_metamask), (unlock), click_unlock_button clicked')
        pop_up_window_close(driver)
        if check_page_url(driver):
            return True
        else:
            if handle_incorrect_password(driver):
                logger.info(' (starting_metamask), (unlock), handle_incorrect_password True\n'
                            'Пароль не верный, авторизация будет через восстановление кошелька, используя сид фразу и пароль из базы данных!')
                input_seed_phrase_and_password_restore_vault(driver, seed, password)
                logger.info(' (starting_metamask), (unlock), (handle_incorrect_password), '
                            '(input_seed_phrase_and_password_restore_vault),\n'
                            'Авторизация успешна, сид фраза и новый пароля успешно введены!')
                pop_up_window_close(driver)
                return True
            else:
                pop_up_window_close(driver)
                return True
    elif get_started(driver, env_id):
        logger.info(' (starting_metamask), (get_started) True')
        onboard_page(driver, seed, password)
        logger.info(' (starting_metamask), (get_started), (onboard_page), done')
        pop_up_window_close(driver)
        return True



def pop_up_window_close(driver):
    driver.implicitly_wait(3)
    try:
        # Проверка наличия всплывающего окна
        popup = driver.find_element(By.CLASS_NAME, "popover-wrap")
        close_button = popup.find_element(By.XPATH, "//button[contains(text(), 'Got it')]")
        close_button.click()
        logger.debug("Всплывающее окно закрыто. [Got it] btn clicked successfully")
    except NoSuchElementException:
        logger.debug("Всплывающее окно не найдено, продолжаем выполнение.")


def meta_mask(driver, seed, password, env_id, mm_address, row, workbook_mm, worksheet_mm, FILE_PATH):
    if starting_metamask(driver, seed, password, env_id):
        version_mm(driver)
        return check_mm_data_base(driver, mm_address, row, workbook_mm, worksheet_mm, FILE_PATH)


