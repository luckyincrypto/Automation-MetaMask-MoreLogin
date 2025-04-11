# Automation-MetaMask-MoreLogin

## Описание проекта
**Automation-MetaMask-MoreLogin** — это инструмент автоматизации, который интегрирует приложение MetaMask (extension) в браузерный профиль антидетект браузера **MoreLogin**. 
Цель проекта — обеспечить удобную и безопасную работу с MetaMask крипто-кошельком в условиях динамической автоматизации.

### Основные функции:
- Инициализация браузерных профилей через API **MoreLogin**.
- Автоматизация взаимодействия с расширением MetaMask.
- Поддержка мультипрофильной работы для повышения анонимности и удобства.

---

## 🚀 Установка проекта


### 1️⃣ Клонируйте репозиторий:

Скачиваем проект с GitHub в заранее подготовленную директорию.
Из этой директории запускаем терминал (Comand Line Interface, CLI) PowerShell, CMD, Git Bash или др.
Вводим команду, клонируем репозиторий.

```bash
git clone https://github.com/твой_аккаунт/Automation-MetaMask-MoreLogin.git
```


### 2️⃣ В Этой директории создайте виртуальное окружение:
```bash
python -m venv venv
```
и активируйте его:
```bash
source venv/bin/activate # для Linux/Mac
```
или
```bash
venv\Scripts\activate    # для Windows
```
### 3️⃣ Установите библиотеки, зависимости:
```bash
pip install -r requirements.txt
```


## Настройка скрипта

#### 1. Создайте файл .env (используйте образец .env-exampl) и добавьте нужные переменные окружения:

- APPID='your-api-key-goes-here'            берем из MoreLogin ![img.png](img.png)
- SECRETKEY='your-secret-key-goes-here'     берем из MoreLogin
- ENCRYPTKEY='your-encrypt-key-goes-here'   берем из MoreLogin ![img_1.png](img_1.png)

- DATA_BASE='DB-example.xlsx'               название вашей Базы Данных с паролями и сид фразами от MetaMask.
- WORKSHEET_NAME='Sheet'                    название листа в Екселе.

Если нет файла Базы данных, то создается автоматически с новыми паролями, сид фразами, адресами и приватными ключами.
В любой момент времени можно поменять пароли и сид фразы, не зависимо, на свои.
Тогда при следующем запуске браузерного профиля произойдет перелогирование в MetaMask под новыми паролями или сид фразами.
Если поля будут пустыми, то создадутся новые пароли и/или сид фразы с соответствующими адресами и приватными ключами.

#### 2. В файле конфигурации config.yaml замените на свое значение path_local_cashe. Это путь по умолчанию к папке, где хранится кэш профилей временных файлов. ![img_4.png](img_4.png)
 
 
## Использование

После настройки запускайте ключевой скрипт:
```bash
python main.py 
```
или run 'main' (Shift+F10) из IDE


## Требования
- Python версии 3.13 или выше. https://www.python.org/downloads/release/python-3130/
- IDE (Pycharm: https://www.jetbrains.com/pycharm/ или VS Code: https://code.visualstudio.com/)
- Антидетект браузер **MoreLogin**, скачать: https://www.morelogin.com/?from=AANRkwFFphIV. Morelogin является самым безопасным, наиболее подходящим для работы в команде и предлагает наилучшую экономическую эффективность.
- Расширение **MetaMask** установленное в **MoreLogin** (во вкладке: Расширение & Приложение) ![img_2.png](img_2.png) ![img_3.png](img_3.png)
- ссылка на сам **MetaMask**: https://chromewebstore.google.com/detail/metamask/nkbihfbeogaeaoehlefnkodbefgpgknn 
**Важно! -> ID: nkbihfbeogaeaoehlefnkodbefgpgknn**



## Информация взятая из источников:
- https://www.morelogin.com/?from=AANRkwFFphIV
- https://support.morelogin.com/en/articles/10204806-browser-profile
- https://github.com/MoreLoginBrowser/MoreLogin-API-Demos
- https://www.selenium.dev/documentation/webdriver/

