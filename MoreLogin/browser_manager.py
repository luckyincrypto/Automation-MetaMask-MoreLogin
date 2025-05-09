import sys
from typing import Optional, Tuple
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from config import logger, BASEURL, SECRET_KEY, APP_ID, APP_KEY
from MoreLogin.base_func_morelogin import requestHeader, postRequest


class BrowserManager:
    """Класс для управления браузером через MoreLogin API"""

    @staticmethod
    async def create_web_driver(debug_url: str, web_driver_path: str) -> Chrome:
        """
        Инициализация Chrome WebDriver с заданными параметрами

        Args:
            debug_url: URL для отладки
            web_driver_path: Путь к WebDriver

        Returns:
            Chrome: Инициализированный экземпляр Chrome WebDriver
        """
        options = Options()
        options.add_experimental_option("debuggerAddress", debug_url)
        service = Service(executable_path=web_driver_path)
        return Chrome(service=service, options=options)

    @staticmethod
    async def start_browser_profile(env_id: str) -> Tuple[str, str]:
        """
        Запуск профиля браузера через API MoreLogin

        Args:
            env_id: ID окружения

        Returns:
            Tuple[str, str]: Кортеж из debug URL и пути к WebDriver

        Raises:
            ConnectionError: При ошибке запуска профиля
        """
        try:
            request_path = f"{BASEURL}/api/env/start"
            data = {"envId": env_id, "encryptKey": SECRET_KEY}
            response = postRequest(request_path, data, requestHeader(APP_ID, APP_KEY)).json()

            if response["code"] != 0:
                raise ConnectionError(f"Ошибка запуска профиля: {response['msg']}")

            logger.debug(f"Профиль запущен: {response}")
            return (
                f"127.0.0.1:{response['data']['debugPort']}",
                response["data"]["webdriver"],
            )
        except KeyError as e:
            logger.critical(f"Сервер вернул неполный ответ: {e}")
            raise

    @staticmethod
    async def stop_browser_profile(env_id: str) -> dict:
        """
        Завершение работы профиля браузера

        Args:
            env_id: ID окружения

        Returns:
            dict: Ответ от сервера
        """
        request_path = f"{BASEURL}/api/env/close"
        data = {"envId": env_id, "encryptKey": SECRET_KEY}
        response = postRequest(request_path, data, requestHeader(APP_ID, APP_KEY)).json()
        logger.debug(f"Профиль {env_id} остановлен.")
        return response

    @staticmethod
    async def get_list_browser_profiles(unique_id: int) -> Tuple[str, int, str]:
        """
        Получение списка профилей браузера

        Args:
            unique_id: Уникальный идентификатор профиля

        Returns:
            Tuple[str, int, str]: Кортеж из ID профиля, unique_id и имени профиля

        Raises:
            SystemExit: При ошибке API или отсутствии профиля
        """
        request_path = f"{BASEURL}/api/env/page"
        data = {"pageNo": 1, "pageSize": 100, "envName": "-"}

        try:
            response = postRequest(request_path, data, requestHeader(APP_ID, APP_KEY)).json()
            if response["code"] != 0:
                logger.error(f"Ошибка API: {response['msg']}")
                sys.exit(1)

            for env in response.get("data", {}).get("dataList", []):
                if int(env["envName"][2:]) == unique_id:
                    return str(env["id"]), unique_id, env["envName"]

            logger.error("Профиль не найден. Проверьте unique_id.")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Ошибка подключения: {e}")
            sys.exit(1)


async def more_login():
    global driver
    manager = BrowserManager()
    try:
        profile_info = await manager.get_list_browser_profiles(unique_id=1)
        print("Найден профиль:", profile_info)

        # Пример использования других методов
        debug_url, webdriver_path = await manager.start_browser_profile(profile_info[0])
        print(f"Debug URL: {debug_url}, WebDriver Path: {webdriver_path}")

        driver = await manager.create_web_driver(debug_url, webdriver_path)
        print("Драйвер создан успешно")

        # ... работа с драйвером ...
    except Exception as e:
        logger.error(f" (more_login), Произошла ошибка: {e}")
