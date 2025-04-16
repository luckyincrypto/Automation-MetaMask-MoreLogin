import os
import sys

from config import path_local_cashe, logger


# Функция для проверки и изменения содержимого файла
def modify_file_runtimelavamoat(env_id):
    file_path_for_version_mm = os.path.join('{}/chrome_{}/Default/Extensions/nkbihfbeogaeaoehlefnkodbefgpgknn/'.format(path_local_cashe, env_id))
    # logger.debug(f" (modify_file_runtimelavamoat) MetaMask's list of versions: {os.listdir(file_path_for_version_mm)}")

    while True:
        try:
            if len(os.listdir(file_path_for_version_mm)) > 0:
                version_mm_latest = os.listdir(file_path_for_version_mm)[-1]
                logger.info(
                    f" (modify_file_runtimelavamoat) Последняя установленная версия MetaMask: {version_mm_latest}")
                break
        except FileNotFoundError:
            logger.error('Проверте путь к директории локального кэша path_local_cashe в config.yaml файле. Путь указан не верно!')
            sys.exit(1)  # Завершение программы с кодом ошибки 1

    file_path = os.path.join(
        '{}/chrome_{}/Default/Extensions/nkbihfbeogaeaoehlefnkodbefgpgknn/{}/scripts/runtime-lavamoat.js'
        .format(path_local_cashe, env_id, version_mm_latest))
    # Проверяем, существует ли файл
    if not os.path.isfile(file_path):
        logger.error(f" (modify_file_runtimelavamoat) Файл не найден: {file_path}. Выход.")
        sys.exit(1)  # Завершение программы с кодом ошибки 1

    with open(file_path, "r", encoding="utf-8") as file:
        lines = file.readlines()
    if ('const {' in lines[94] and
            'scuttleGlobalThis,' in lines[95] and
            '} = {"scuttleGlobalThis":{"enabled":true,' in lines[96]):

        # Замена "enabled":true на "enabled":false
        lines[96] = lines[96].replace('"enabled":true', '"enabled":false')

        with open(file_path, "w", encoding="utf-8") as file:
            file.writelines(lines)
        logger.debug(" (modify_file_runtimelavamoat) Изменения в файле runtime-lavamoat.js успешно сохранены.")
        return True
    elif ('const {' in lines[94] and
            'scuttleGlobalThis,' in lines[95] and
            '} = {"scuttleGlobalThis":{"enabled":false,' in lines[96]):
        logger.debug(f" (modify_file_runtimelavamoat) файл runtime-lavamoat.js в кэше профиля Env ID: {env_id} "
                    f"соответствует условию автоматизации MetaMask.")
    else:
        logger.error(" (modify_file_runtimelavamoat) Строки 95, 96, 97 не соответствуют указанным условиям.")
