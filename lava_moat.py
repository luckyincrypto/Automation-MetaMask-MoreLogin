import os
import sys
import time
from typing import Optional, Tuple
from MoreLogin.check_morelogin import metamask_path
from config import logger


def modify_file_runtimelavamoat(env_id: str) -> bool:
    """
    Проверяет и изменяет содержимое файла runtime-lavamoat.js

    Args:
        env_id: ID окружения

    Returns:
        bool: True если изменения успешны, False в случае ошибки
    """
    counter = 0
    start_time = time.time()
    file_path_for_version_mm: Optional[str] = None
    version_mm_latest: Optional[str] = None

    while True:
        try:
            file_path_for_version_mm = metamask_path(env_id)
            if file_path_for_version_mm and len(os.listdir(file_path_for_version_mm)) > 0:
                version_mm_latest = os.listdir(file_path_for_version_mm)[-1]
                elapsed_time = time.time() - start_time
                logger.info(
                    f" (modify_file_runtimelavamoat) Time spent: {elapsed_time:.2f} sec for Cycles: {counter},\n"
                    f"Последняя установленная версия MetaMask: {version_mm_latest} из {os.listdir(file_path_for_version_mm)}"
                )
                break
            else:
                if counter >= 5:
                    elapsed_time_err = time.time() - start_time
                    logger.error(
                        f" (modify_file_runtimelavamoat), Time spent: {elapsed_time_err:.2f} sec for Cycles: {counter},\n"
                        f"Проверьте путь к директории локального кэша path_local_cashe в config.yaml. \n"
                        f"Если путь указан верно значит Extension MetaMask не найден в локальном кэше. "
                        f"MoreLogin не успевает загрузить Extension MetaMask в браузерный профиль, ему что то мешает. \n")

        except FileNotFoundError:
            if counter >= 3:
                elapsed_time_err = time.time() - start_time
                logger.error(
                    f" (modify_file_runtimelavamoat), Time spent: {elapsed_time_err:.2f} sec for Cycles: {counter},\n"
                    f"Проверьте путь к директории локального кэша path_local_cashe в config.yaml. \n"
                    f"Если путь указан верно значит Extension MetaMask не найден в локальном кэше. \n"
                    f"Инициализация Extension MetaMask отсутствует в браузерном профиле!\n"
                    f" Совет! \n"
                    f"  1. Откройте браузерный профиль вручную, дождитесь пока Extension MetaMask будет проинициализирован в браузерном профиле!\n"
                    f"  2. Закройте браузерный профиль вручную и повторите запуск скрипта!\n"
                )
                return False

        counter += 1
        time.sleep(5)

    if not file_path_for_version_mm or not version_mm_latest:
        logger.error("Не удалось получить путь к MetaMask или версию")
        return False

    file_path_runtime_lavamoat = f'{file_path_for_version_mm}{version_mm_latest}/scripts/runtime-lavamoat.js'
    if not os.path.exists(file_path_runtime_lavamoat):
        logger.error(
            f" (modify_file_runtimelavamoat) Файл не найден: {file_path_runtime_lavamoat}. Выход."
        )
        return False

    try:
        with open(file_path_runtime_lavamoat, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if (
            "const {" in lines[94]
            and "scuttleGlobalThis," in lines[95]
            and '} = {"scuttleGlobalThis":{"enabled":true,' in lines[96]
        ):
            # Замена "enabled":true на "enabled":false
            lines[96] = lines[96].replace('"enabled":true', '"enabled":false')

            with open(file_path_runtime_lavamoat, "w", encoding="utf-8") as file:
                file.writelines(lines)
            logger.update(
                " (modify_file_runtimelavamoat) Изменения в файле runtime-lavamoat.js успешно сохранены."
            )
            return True
        elif (
            "const {" in lines[94]
            and "scuttleGlobalThis," in lines[95]
            and '} = {"scuttleGlobalThis":{"enabled":false,' in lines[96]
        ):
            logger.debug(
                f" (modify_file_runtimelavamoat) Файл runtime-lavamoat.js в кэше профиля Env ID: {env_id} соответствует условию автоматизации MetaMask."
            )
            return True
        else:
            logger.error(
                " (modify_file_runtimelavamoat) Строки 94, 95, 96 не соответствуют указанным условиям."
            )
            return False
    except Exception as e:
        logger.error(f" (modify_file_runtimelavamoat) Ошибка при работе с файлом: {e}")
        return False
