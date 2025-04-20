import os
import sys
import time

from config import path_local_cashe, logger


# Функция для проверки и изменения содержимого файла
def modify_file_runtimelavamoat(env_id):
    counter = 0  # Счетчик циклов
    start_time = time.time()  # Засекаем время начала работы
    while True:
        try:
            file_path_for_version_mm = os.path.join(
                f"{path_local_cashe}/chrome_{env_id}/Default/Extensions/nkbihfbeogaeaoehlefnkodbefgpgknn/"
            )

            if len(os.listdir(file_path_for_version_mm)) > 0:
                version_mm_latest = os.listdir(file_path_for_version_mm)[-1]
                elapsed_time = time.time() - start_time  # Вычисляем затраченное время

                logger.warning(
                    f" (modify_file_runtimelavamoat) Time spent: {elapsed_time:.2f} sec for Cycles: {counter},\n"
                    f"Последняя установленная версия MetaMask: {version_mm_latest} из {os.listdir(file_path_for_version_mm)}"
                )
                break
        except FileNotFoundError:
            if counter >= 6:
                logger.error(
                    "Проверьте путь к директории локального кэша path_local_cashe в config.yaml. Путь указан неверно!")
                sys.exit(1)  # Завершение программы с кодом ошибки 1

            counter += 1
            time.sleep(5)

    file_path = os.path.join(
        f"{path_local_cashe}/chrome_{env_id}/Default/Extensions/nkbihfbeogaeaoehlefnkodbefgpgknn/{version_mm_latest}/scripts/runtime-lavamoat.js"
    )

    if not os.path.isfile(file_path):
        logger.error(f" (modify_file_runtimelavamoat) Файл не найден: {file_path}. Выход.")
        sys.exit(1)   # Завершение программы с кодом ошибки 1

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    if ('const {' in lines[94] and 'scuttleGlobalThis,' in lines[95] and '} = {"scuttleGlobalThis":{"enabled":true,' in
            lines[96]):
        # Замена "enabled":true на "enabled":false
        lines[96] = lines[96].replace('"enabled":true', '"enabled":false')

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)
        logger.debug(" (modify_file_runtimelavamoat) Изменения в файле runtime-lavamoat.js успешно сохранены.")
        return True
    elif ('const {' in lines[94] and 'scuttleGlobalThis,' in lines[
        95] and '} = {"scuttleGlobalThis":{"enabled":false,' in lines[96]):
        logger.debug(
            f" (modify_file_runtimelavamoat) Файл runtime-lavamoat.js в кэше профиля Env ID: {env_id} соответствует условию автоматизации MetaMask.")
    else:
        logger.error(" (modify_file_runtimelavamoat) Строки 94, 95, 96 не соответствуют указанным условиям.")