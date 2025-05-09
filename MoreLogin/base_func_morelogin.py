import time
import hashlib
import random
import string
import requests
from typing import Dict, Any
from config import logger


def requestHeader(appId: str, secretKey: str) -> Dict[str, str]:
    """
    Создает заголовки для веб-запроса к API MoreLogin

    Args:
        appId: ID приложения
        secretKey: Секретный ключ

    Returns:
        Dict[str, str]: Словарь с заголовками запроса
    """
    nonceId = generateNonceId()
    md5Str = md5Encode(nonceId, appId, secretKey)
    return {"X-Api-Id": appId, "Authorization": md5Str, "X-Nonce-Id": nonceId}


def generateRandom(length: int = 6) -> str:
    """
    Генерирует случайную строку заданной длины

    Args:
        length: Длина строки (по умолчанию 6)

    Returns:
        str: Случайная строка
    """
    characters = string.ascii_letters + string.digits
    random_string = "".join(random.choice(characters) for _ in range(length))
    return random_string


def generateNonceId() -> str:
    """
    Генерирует глобально уникальный ID

    Returns:
        str: Уникальный ID
    """
    return str(int(time.time() * 1000)) + generateRandom()


def md5Encode(nonceId: str, appId: str, secretKey: str) -> str:
    """
    Вычисляет MD5-хеш для подписи запроса

    Args:
        nonceId: Уникальный ID
        appId: ID приложения
        secretKey: Секретный ключ

    Returns:
        str: MD5-хеш
    """
    md5 = hashlib.md5()
    md5.update((appId + nonceId + secretKey).encode("utf-8"))
    return md5.hexdigest()


def postRequest(url: str, data: Dict[str, Any], headers: Dict[str, str]) -> requests.Response:
    """
    Отправляет POST-запрос к API

    Args:
        url: URL для запроса
        data: Данные для отправки
        headers: Заголовки запроса

    Returns:
        requests.Response: Ответ от сервера

    Raises:
        requests.RequestException: При ошибке запроса
    """
    try:
        headers["Content-Type"] = "application/json"
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Ошибка POST-запроса: {e}")
        raise


def getRequest(url: str, headers: Dict[str, str]) -> requests.Response:
    """
    Отправляет GET-запрос к API

    Args:
        url: URL для запроса
        headers: Заголовки запроса

    Returns:
        requests.Response: Ответ от сервера

    Raises:
        requests.RequestException: При ошибке запроса
    """
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response
    except requests.RequestException as e:
        logger.error(f"Ошибка GET-запроса: {e}")
        raise
