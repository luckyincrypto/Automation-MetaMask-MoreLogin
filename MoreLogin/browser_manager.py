import sys
from selenium.webdriver import Chrome
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from config import logger, BASEURL, SECRET_KEY, APP_ID, APP_KEY
from MoreLogin.base_func_morelogin import requestHeader, postRequest


class BrowserManager:
    """Класс для управления браузером через MoreLogin API"""

    @staticmethod
    async def create_web_driver(debug_url: str, web_driver_path: str) -> Chrome:
        """Инициализация Chrome WebDriver с заданными параметрами"""
        options = Options()
        options.add_experimental_option("debuggerAddress", debug_url)
        service = Service(executable_path=web_driver_path)
        return Chrome(service=service, options=options)

    @staticmethod
    async def start_browser_profile(env_id: str) -> tuple[str, str]:
        """Запуск профиля браузера через API MoreLogin"""
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
            # return f"Сервер вернул неполный ответ: {e}"


    @staticmethod
    async def stop_browser_profile(env_id: str) -> dict:
        """Завершение работы профиля браузера"""
        request_path = f"{BASEURL}/api/env/close"
        data = {"envId": env_id, "encryptKey": SECRET_KEY}
        response = postRequest(request_path, data, requestHeader(APP_ID, APP_KEY)).json()
        logger.debug(f"Профиль {env_id} остановлен.")
        return response

    @staticmethod
    async def get_list_browser_profiles(unique_id: int) -> tuple[str, int, str]:
        """Получение списка профилей браузера"""
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

