import os
import string
from typing import List, Optional
from config import logger


def convert_windows_path_to_unix(path: str) -> str:
    """
    Преобразует путь из Windows-формата в UNIX-формат.

    Args:
        path: Путь в Windows-формате

    Returns:
        str: Путь в UNIX-формате
    """
    return path.replace("\\", "/")


def find_morelogin_cache() -> List[str]:
    """
    Ищет путь .MoreLogin\\cache на всех доступных дисках.

    Returns:
        List[str]: Список найденных путей для .MoreLogin\\cache
    """
    available_drives = [f"{drive}:" for drive in string.ascii_uppercase if os.path.exists(f"{drive}:")]
    found_paths = []
    relative_path = ".MoreLogin\\cache"

    for drive in available_drives:
        full_path = os.path.join(drive + "\\", relative_path)
        if os.path.exists(full_path):
            found_paths.append(full_path)

    return found_paths


def find_metamask_extension(path_local_cache: str, env_id: str = "0") -> Optional[str]:
    """
    Находит путь к расширению MetaMask в Chrome для указанного окружения.

    Args:
        path_local_cache: Путь к локальному кешу берем из MoreLogin .MoreLogin\\cache
        env_id: Идентификатор окружения

    Returns:
        Optional[str]: Путь к MetaMask в UNIX-формате или None
    """
    extensions_path = os.path.join(
        path_local_cache,
        f"chrome_{env_id}\\Default\\Extensions\\nkbihfbeogaeaoehlefnkodbefgpgknn\\"
    )

    if os.path.exists(extensions_path):
        return convert_windows_path_to_unix(extensions_path)
    return None


def metamask_path(env_id: str) -> Optional[str]:
    """
    Находит путь к расширению MetaMask для указанного окружения.

    Args:
        env_id: Идентификатор окружения

    Returns:
        Optional[str]: Путь к MetaMask в UNIX-формате или None
    """
    cache_paths = find_morelogin_cache()

    if not cache_paths:
        logger.error("Путь .MoreLogin\\cache не найден ни на одном диске.")
        return None

    if len(cache_paths) == 1:
        selected_path = cache_paths[0]
        logger.info(f"Выбранный путь к локальному кешу: {selected_path}")
    else:
        logger.info("Найдено несколько путей:")
        for i, path in enumerate(cache_paths, start=1):
            print(f"{i}. {path}")

        while True:
            try:
                choice = int(input("Выберите номер пути: ")) - 1
                if 0 <= choice < len(cache_paths):
                    selected_path = cache_paths[choice]
                    break
                else:
                    logger.error(f"Пожалуйста, введите число от 1 до {len(cache_paths)}")
            except ValueError:
                logger.error("Пожалуйста, введите корректное число")

    metamask_path = find_metamask_extension(selected_path, env_id)
    if metamask_path:
        logger.debug(f"Путь к MetaMask (UNIX формат): {metamask_path}")
        return metamask_path

    logger.error(f"Расширение MetaMask не найдено в директории: {selected_path}")
    return None


# print(metamask_path('1914353511934009344'))