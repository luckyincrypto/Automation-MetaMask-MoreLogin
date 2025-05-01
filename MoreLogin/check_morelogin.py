import os
import string
from config import logger


def convert_windows_path_to_unix(path):
    """Преобразует путь из Windows-формата в UNIX-формат."""
    return path.replace("\\", "/")


def find_morelogin_cache():
    r"""
    Ищет путь .MoreLogin\cache на всех доступных дисках.

    Returns:
        Список найденных путей для .MoreLogin\cache
    """
    available_drives = [f"{drive}:" for drive in string.ascii_uppercase if os.path.exists(f"{drive}:")]
    found_paths = []
    relative_path = ".MoreLogin\\cache"

    for drive in available_drives:
        # Исправляем построение полного пути
        full_path = os.path.join(drive + "\\", relative_path)
        if os.path.exists(full_path):
            found_paths.append(full_path)

    return found_paths


def find_metamask_extension(path_local_cache, env_id="0"):
    r"""
    Находит путь к расширению MetaMask в Chrome для указанного окружения.

    Args:
        path_local_cache: Путь к локальному кешу берем из MoreLogin .MoreLogin\cache
        env_id: Идентификатор окружения

    Returns:
        Путь к MetaMask в UNIX-формате или None
    """
    extensions_path = os.path.join(
        path_local_cache,
        f"chrome_{env_id}\\Default\\Extensions\\nkbihfbeogaeaoehlefnkodbefgpgknn\\"
    )

    if os.path.exists(extensions_path):
        return convert_windows_path_to_unix(extensions_path)
    else:
        return None


def metamask_path(env_id):
    cache_paths = find_morelogin_cache()

    if not cache_paths:
        logger.error("Путь .MoreLogin\\cache не найден ни на одном диске.")
    else:
        if len(cache_paths) == 1:
            # print(f"Путь найден на одном диске: {cache_paths[0]}")
            selected_path = cache_paths[0]
            logger.info(f"Выбранный путь к локальному кешу: {selected_path}")
        else:
            logger.info("Найдено несколько путей:")
            for i, path in enumerate(cache_paths, start=1):
                print(f"{i}. {path}")

            choice = int(input("Выберите номер пути: ")) - 1
            selected_path = cache_paths[choice]

        # print("Ищем расширение MetaMask...")
        metamask_path = find_metamask_extension(selected_path, env_id)
        if metamask_path:
            logger.debug(f"Путь к MetaMask (UNIX формат): {metamask_path}")
            return metamask_path
        else:
            logger.error(f"Расширение MetaMask не найдено в директории: {selected_path}")


# print(metamask_path('1914353511934009344'))