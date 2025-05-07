# Стандартные библиотеки
import os
import random
import secrets
import string
import sys
import time
import traceback
from datetime import datetime

# Внешние библиотеки
import asyncio
import openpyxl
from openpyxl import Workbook
from openpyxl.utils.exceptions import InvalidFileException
from selenium.common.exceptions import WebDriverException

# Локальные модули
from faucet_morkie.faucet_morkie import MonadFaucet
from lava_moat import modify_file_runtimelavamoat
from meta_mask import MetaMaskHelper
from create_mm_wallet import create_wallet
from config import logger, DATA_BASE_PATH, WORKSHEET_NAME, DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT
from MoreLogin.browser_manager import BrowserManager



from database import Database
from datetime import datetime

# Инициализация базы данных
db = Database(
    dbname=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD,
    host=DB_HOST,
    port=DB_PORT,
)


async def read_user_list_file(
    worksheet_mm, start_account, end_account, mix_profiles, workbook_mm
):
    """Чтение данных из Excel-файла."""
    profiles = []
    logger.debug(
        f"[DATABASE READ] Чтение из базы данных Excel-файла. От {start_account} до {end_account}."
    )
    for row in range(start_account, end_account + 1):
        if row is None:
            logger.warning("Переменная row не инициализирована.")
        try:
            unique_id = int(worksheet_mm.cell(row=row + 1, column=1).value)
            password = worksheet_mm.cell(row=row + 1, column=2).value
            seed = worksheet_mm.cell(row=row + 1, column=3).value
            mm_address = worksheet_mm.cell(row=row + 1, column=4).value
            private_key = worksheet_mm.cell(row=row + 1, column=5).value
            if password is None and seed:
                password = create_password()
                worksheet_mm.cell(row=row + 1, column=2).value = password
                workbook_mm.save(DATA_BASE_PATH)
                logger.update(
                    f"[NEW PASSWORD] Для профиля № {unique_id} создан новый пароль."
                )
            if seed is None:
                seed, mm_address, private_key = create_wallet()
                password = worksheet_mm.cell(row=row + 1, column=2).value = (
                    create_password()
                )  # create a new password,
                # if there was an old one, it will be cancelled for the new wallet
                worksheet_mm.cell(row=row + 1, column=3).value = seed
                worksheet_mm.cell(row=row + 1, column=4).value = mm_address
                worksheet_mm.cell(row=row + 1, column=5).value = private_key
                workbook_mm.save(DATA_BASE_PATH)
                logger.update(
                    f"\n[NEW PASSWORD & ETH WALLET ADDRESS] Для профиля № {unique_id}, address: {mm_address} and password\n"
                )
            if mm_address is None:
                logger.warning(
                    f"\nВ Базе нет адреса ETH wallet для профиля № {unique_id}."
                    f" При успешном входе в профиль и МетаMask, "
                    f"адрес ETH wallet автоматически будет добавлен в базу."
                )
            profiles.append(
                [
                    unique_id,
                    password,
                    seed,
                    mm_address,
                    private_key,
                    worksheet_mm,
                    workbook_mm,
                    row,
                ]
            )
        except Exception as e:
            logger.error(f"Ошибка чтения данных: {traceback.format_exc()}")
    if mix_profiles.lower() == "y":
        random.shuffle(profiles)
        logger.info(f"[SHUFFLE] Профили перемешаны.")
    return profiles


def get_user_input():
    """Получение параметров от пользователя с улучшенной обработкой ввода и логированием."""
    print(
        'Начало ввода параметров от пользователя.\n Закрыть профиль по окончании?\n Да - "Y", оставить открытым - "Enter"\n'
    )
    mode_close_profile_or_not = input().strip().lower()
    if mode_close_profile_or_not.lower() == "y":
        print("Профиль будет закрыт после завершения работы скрипта.\n")
    else:
        print("Профиль останется открытым после завершения работы скрипта.\n")
    while True:
        try:
            # print(f"С какого аккаунта начать, No: \n")
            start_account = int(input(f"С какого аккаунта начать, No: \n"))
            # print("Каким аккаунтом завершить, No: \n")
            end_account = int(input("Каким аккаунтом завершить, No: \n"))
            if 0 < start_account <= end_account:
                break
            else:
                logger.error(
                    "Не корректный ввод. Конечный аккаунт должен быть больше или равен начальному."
                )
        except ValueError:
            logger.error("Ошибка! Введите числовые значения.")

    logger.info(f"Запуск профилей от {start_account} до {end_account}.")
    time.sleep(0.2)
    mix_profiles = "no"
    delay_from_to = []
    if start_account != end_account:
        mix_profiles = (
            input("\nПеремешивать кошельки? Yes-Y / No-Enter: \n").strip().lower()
        )
        if mix_profiles == "y":
            print("Профили будут перемешаны перед запуском.")
        else:
            print("Профили будут запущены в порядке их создания.")
        delay_execution = (
            input("\nДобавить задержку между профилями? Yes-Y / No-Enter: \n")
            .strip()
            .lower()
        )
        if delay_execution == "y":
            while True:
                delay_from_to = input(
                    "Введите задержку выполнения (от, до) секунд, через запятую: "
                ).split(",")
                try:
                    if len(delay_from_to) == 2 and float(delay_from_to[0]) < float(
                        delay_from_to[1]
                    ):
                        print(
                            f"Задержка установлена в диапазоне от {delay_from_to[0]} до {delay_from_to[1]} секунд."
                        )
                        break
                    else:
                        logger.error(
                            "Не корректный диапазон. Повторите ввод, например: 10,60"
                        )
                        time.sleep(0.2)
                except ValueError:
                    logger.error("Ошибка! Введите корректные числовые значения")
                    time.sleep(0.2)
        else:
            print("Задержка отсутствует.")
    return (
        start_account,
        end_account,
        mix_profiles,
        delay_from_to,
        mode_close_profile_or_not,
    )


start_account, end_account, mix_profiles, delay_from_to, mode_close_profile_or_not = (
    get_user_input()
)


def create_password():
    password = f"{''.join(secrets.choice(string.ascii_letters + string.digits + string.punctuation) for i in range(22))}"
    return password


async def operationEnv(
    driver, seed, env_id, password, mm_address, worksheet_mm, workbook_mm, row, file_path
):
    """Основная операция."""
    try:
        logger.debug(
            f" (operationEnv) STEP 2 <<< Запуск Env ID: {env_id} Основная операция >>>"
        )
        driver.refresh()
        driver.maximize_window()
        await asyncio.sleep(1)

        # Используем методы через экземпляр MetaMaskHelper
        helper = MetaMaskHelper(driver)
        helper.delete_others_windows()

        if modify_file_runtimelavamoat(env_id):
            wallet_mm_from_browser_extension = helper.meta_mask(
                seed,
                password,
                mm_address,
                row,
                workbook_mm,
                worksheet_mm,
                file_path,
            )
            logger.debug(
                f"wallet_mm_from_browser_extension: {wallet_mm_from_browser_extension}, type: {type(wallet_mm_from_browser_extension)}"
            )

            # Тут нужно будет написать остальные шаги по работе с профилем, автоматизации на различных сайтах.

            result = MonadFaucet.process(driver, wallet_mm_from_browser_extension)
            db.insert_activity(result)
            print("\nВсе успешные активности:")
            print(db.get_activities({'status': 'success'}))
            db.close()

            # print(f'Result of: {result}')
            helper.open_tab(f"https://testnet.monadexplorer.com/address/{wallet_mm_from_browser_extension}")
            helper.open_tab("https://debank.com/profile/" + wallet_mm_from_browser_extension)


            # project_1(driver)  # для примера только
            # project_2(driver)  # для примера только
            # project_3(driver)  # для примера только


            return True
        else:
            logger.error(
                f" (operationEnv) ERROR: Не удалось запустить (modify_file_runtimelavamoat) Env ID: {env_id}\n"
                f"Повторяем попытку, производим перезапуск Profile Env ID: {env_id}"
            )
            return False
    except WebDriverException as e:
        logger.error(f" (operationEnv) ERROR WebDriverException: {e}")
        return False


async def restart_browser_profile(driver, env_id, unique_id, env_name, count):
    """Перезапуск профиля браузера при ошибках"""
    if count > 3:
        logger.critical(
            f"\n{"#" * 20} (main_flow), (operationEnv), Не удачный запуск №: {count}! Profile №: {unique_id}, Env_Name: {env_name}, Env ID: {env_id},"
            f"Env ID: {env_id} будет остановлен и закрыт. {"#" * 20}"
        )
        sys.exit(1)
    else:
        # Закрываем драйвер и останавливаем профиль
        await asyncio.sleep(5)
        if driver in globals():
            driver.quit()
        await BrowserManager.stop_browser_profile(env_id)
        logger.warning(
            f"\n (main_flow), (operationEnv) Не удачный запуск №: {count}! Повторный запуск через 5 секунд! Profile №: {unique_id}, Env_Name: {env_name}, Env ID: {env_id}"
        )
    return count


async def main_flow(
    env_id,
    seed,
    password,
    env_name,
    unique_id,
    mm_address,
    worksheet_mm,
    workbook_mm,
    row,

):
    """Основной рабочий процесс для одного профиля."""
    driver = None
    count = 0
    try:
        while True:
            if count <= 3:
                await asyncio.sleep(5)
            # Запуск профиля
            debug_url, driver_path = await BrowserManager.start_browser_profile(env_id)
            if not debug_url and not driver_path:
                count += 1
                # MetaMaskHelper(driver).delete_others_windows()
                await restart_browser_profile(driver, env_id, unique_id, env_name, count)
            # Логирование запуска профиля
            logger.warning(
                f"\n{"#" * 20} (main_flow) SCRIPT STARTED Profile №: {unique_id}, Env_Name: {env_name}, Env ID: {env_id} {"#" * 20}\n"
            )
            # Создание драйвера
            driver = await BrowserManager.create_web_driver(debug_url, driver_path)
            # Устанавливаем глобальное время ожидания в 10 секунды
            driver.implicitly_wait(10)
            # Основные операции
            logger.debug(
                f" (main_flow) STEP 1 <<< Начало работы в Profile №: {unique_id}, Env_Name: {env_name}, Env ID: {env_id} >>>"
            )
            if await operationEnv(driver, seed, env_id, password, mm_address, worksheet_mm, workbook_mm, row, DATA_BASE_PATH):
                break

            count = await restart_browser_profile(driver, env_id, unique_id, env_name, count)

    except Exception as e:
        logger.error(
            f" (main_flow) ERROR in Profile №: {unique_id}, Env_Name: {env_name}, Env ID: {env_id}, Ошибка: {e}"
        )
        traceback.print_exc()

    finally:
        # Завершаем профиль корректно
        if driver and mode_close_profile_or_not.lower() == "y":
            close_tabs = MetaMaskHelper(driver)
            close_tabs.delete_others_windows()
            driver.quit()
            await BrowserManager.stop_browser_profile(env_id)


async def main():
    """Главная функция для обработки всех профилей."""
    count_profile = 0
    script_start_time = datetime.now()
    logger.debug(" (main) Beginning of the script.")

    # Открытие базы данных
    def workbook_worksheet():
        # код для работы с worksheet_mm здесь
        try:
            workbook_mm = openpyxl.load_workbook(DATA_BASE_PATH)
            worksheet_mm = workbook_mm[WORKSHEET_NAME]
            logger.debug(
                f" (workbook_worksheet) DATABASE Рабочий лист базы данных: {worksheet_mm.title}"
            )
            return workbook_mm, worksheet_mm
        except KeyError:
            logger.error(
                f" (workbook_worksheet) Error: Нет доступа к рабочему листу базы данных: {WORKSHEET_NAME}\n"
                f"Проверьте файл переменных окружения .env:\n"
                f" WORKSHEET_NAME \n"
            )
            traceback.print_exc()
            sys.exit(1)  # Завершение программы с кодом ошибки 1
        except InvalidFileException:
            logger.error(
                f" (workbook_worksheet) Error: Неверный формат файла базы данных: {DATA_BASE_PATH}\n"
                f"Проверьте файл переменных окружения .env:\n"
                f" DATA_BASE \n"
            )
            traceback.print_exc()
            sys.exit(1)  # Завершение программы с кодом ошибки 1

    # Проверка существует ли файл с базой данных DB.xlsx
    if os.path.exists(DATA_BASE_PATH):
        # Если файл существует, загружаем его
        logger.debug(f" (main) DATABASE exists: {DATA_BASE_PATH}.")
        workbook_mm, worksheet_mm = workbook_worksheet()
    else:
        # Если файл не существует, создаем новый файл
        logger.update(
            f" (main) DATABASE База данных отсутствует. Создание нового файла базы данных."
        )
        workbook_mm = Workbook()
        worksheet_mm = workbook_mm.active
        worksheet_mm.title = WORKSHEET_NAME  # Установка имени рабочего листа
        worksheet_mm["A1"] = "No"
        worksheet_mm["B1"] = "Password"
        worksheet_mm["C1"] = "Mnemonic"
        worksheet_mm["D1"] = "Address"
        worksheet_mm["E1"] = "Private key"
        # Запись числовых значений от 1 до 100 в первую колонку, начиная со 2-й строки
        for row in range(2, 102):  # от 2 до 101 (включительно)
            worksheet_mm.cell(
                row=row, column=1, value=row - 1
            )  # Заполнение первой колонки нумерация от 1 до 100
        workbook_mm.save(DATA_BASE_PATH)  # Сохранение нового файла
        logger.update(f" (main) DATABASE created new file: {DATA_BASE_PATH}.")
        # код для работы с worksheet_mm загружаем его
        workbook_mm, worksheet_mm = workbook_worksheet()
    # Получаем список профилей
    profiles = await read_user_list_file(
        worksheet_mm, start_account, end_account, mix_profiles, workbook_mm
    )
    logger.info(f" (main) Profiles will be processed: {len(profiles)}.\n")
    for profile in profiles:
        count_profile += 1
        (
            unique_id,
            password,
            seed,
            mm_address,
            private_key,
            worksheet_mm,
            workbook_mm,
            row,
        ) = profile

        # Получение данных профиля
        env_id, unique_id, env_name = await BrowserManager.get_list_browser_profiles(unique_id)

        start_time = datetime.now()
        logger.debug(
            f"\n (main) PROFILE INFO, №: {count_profile} from {len(profiles)}, "
            f"Acc ID: {unique_id}, EnvName: {env_name}, MetaMask address: {mm_address}, Seed: {seed}, "
            f"Password: {password}, Private_key: {private_key}, Row: {row}, Start: {start_time}\n"
        )
        # Основной рабочий процесс
        await main_flow(
            env_id,
            seed,
            password,
            env_name,
            unique_id,
            mm_address,
            worksheet_mm,
            workbook_mm,
            row,
        )
        # Время на выполнения профиля
        profile_duration = datetime.now() - start_time
        logger.warning(
            f"\n{"#" * 20} (main_flow) SCRIPT ENDED Profile №: {unique_id}, Env_Name: {env_name}, "
            f"Env ID: {env_id}, time spent: {profile_duration} {"#" * 20}\n"
        )
        # Задержка между профилями
        if delay_from_to and count_profile != len(profiles):
            delay = random.randint(int(delay_from_to[0]), int(delay_from_to[1]))
            logger.info(f" (main) DELAY: {delay} seconds between next profile.")
            time.sleep(delay)
    # Итоги работы скрипта
    total_duration = datetime.now() - script_start_time
    logger.warning(
        f"\n (main) FINISH. Total time duration spent all profiles: {total_duration}, total profiles: {count_profile}\n{"-" * 90}\n"
    )


if __name__ == "__main__":
    asyncio.run(main())
