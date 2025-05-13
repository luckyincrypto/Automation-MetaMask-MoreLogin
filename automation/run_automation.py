import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta
import random
from config import logger, AUTO_MODE, MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES
import sys


# Получаем абсолютный путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent  # automation/ -> ../
# Пути
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def run_powershell_script(script_name):
    """Универсальный запуск PS скриптов из папки automation/"""
    script_path = PROJECT_ROOT / "automation" / script_name
    try:
        # Запускаем PowerShell от имени администратора
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", f"Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{script_path}\"' -Verb RunAs -Wait"],
            capture_output=True,
            text=True,
            check=True
        )
        if "SUCCESS" in result.stdout:
            logger.info(f"Скрипт {script_path} выполнен успешно: {result.stdout}")
            return True
        else:
            logger.error(f"Ошибка в {script_name}:\n{result.stderr}")
            return False
    except subprocess.CalledProcessError as e:
        logger.error(f"Сбой выполнения {script_name}:\n{e.stderr}")
        logger.warning("\n Выполните действия для запуска скрипта в автоматическом режиме: \n"
                       "Если в файле config.yaml есть AUTO_MODE: true, \n"
                       "то выполните один раз для перехода в автоматический запуск скрипта.\n"
                       "   1) Запустите PowerShell от имени администратора\n"
                       "   2) Перейдите в директорию проекта: (для примера) cd D:/crypto/Automation-MetaMask-MoreLogin\n"
                       "   3) Активируйте виртуальное окружение: ./.venv/Scripts/Activate\n"
                       "   4) Запустите скрипт: python main.py (для windows) или python3 main.py (для linux)\n")
        return False

def get_random_interval():
    """Генерирует случайный интервал между запусками в минутах"""
    return random.randint(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)

def check_auto_mode():
    """Проверяет режим работы и завершает скрипт если AUTO_MODE: false и скрипт запущен из Task Scheduler"""
    if not AUTO_MODE:
        # Проверяем наличие флага --scheduled-task в аргументах командной строки
        is_scheduled_task = "--scheduled-task" in sys.argv
        logger.debug(f"Проверка запуска из Task Scheduler: {is_scheduled_task}")

        if is_scheduled_task:
            logger.info("AUTO_MODE отключен и скрипт запущен из Task Scheduler. Завершение работы.")
            # Удаляем задачу из планировщика
            temp_script = PROJECT_ROOT / "automation" / "temp_uninstall.ps1"
            with open(temp_script, "w", encoding='utf-8') as f:
                f.write("""#Requires -RunAsAdministrator

# Проверяем права администратора
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Требуются права администратора"
    exit 1
}

$taskName = "AutoMetaMaskMoreLogin"
$taskFolder = "\\Automation-MetaMask-MoreLogin\\"

# Проверяем существование задачи
Write-Host "Проверка существования задачи..."
$task = Get-ScheduledTask -TaskName $taskName -TaskPath $taskFolder -ErrorAction SilentlyContinue
if ($task) {
    Write-Host "Задача найдена, пытаемся удалить..."
    try {
        Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskFolder -Confirm:$false -ErrorAction Stop
        Write-Host "Задача успешно удалена"
    } catch {
        Write-Host "Ошибка при удалении задачи: $_"
        Write-Host "Детали ошибки:"
        Write-Host "  Сообщение: $($_.Exception.Message)"
        Write-Host "  Тип: $($_.Exception.GetType().FullName)"
        Write-Host "  Код: $($_.Exception.HResult)"
        exit 1
    }
} else {
    Write-Host "Задача не найдена в пути: $taskFolder"
    # Пробуем найти задачу в других местах
    Write-Host "Поиск задачи в других папках..."
    $allTasks = Get-ScheduledTask | Where-Object { $_.TaskName -eq $taskName }
    if ($allTasks) {
        foreach ($foundTask in $allTasks) {
            Write-Host "Найдена задача в пути: $($foundTask.TaskPath)"
            try {
                Unregister-ScheduledTask -TaskName $taskName -TaskPath $foundTask.TaskPath -Confirm:$false -ErrorAction Stop
                Write-Host "Задача успешно удалена из пути: $($foundTask.TaskPath)"
            } catch {
                Write-Host "Ошибка при удалении задачи из пути $($foundTask.TaskPath): $_"
                Write-Host "Детали ошибки:"
                Write-Host "  Сообщение: $($_.Exception.Message)"
                Write-Host "  Тип: $($_.Exception.GetType().FullName)"
                Write-Host "  Код: $($_.Exception.HResult)"
            }
        }
    } else {
        Write-Host "Задача не найдена нигде в Task Scheduler"
    }
}

Write-Host "SUCCESS"
""")
            if run_powershell_script("temp_uninstall.ps1"):
                temp_script.unlink(missing_ok=True)
                logger.info("Задача успешно удалена из Task Scheduler")
                sys.exit(0)
            else:
                logger.error("Не удалось удалить задачу из Task Scheduler")
                sys.exit(1)
        else:
            logger.info("AUTO_MODE отключен, но скрипт запущен вручную. Продолжаем работу в интерактивном режиме.")

def schedule_next_run():
    """Основная функция управления расписанием, задачами Планировщика"""
    logger.debug(f"AUTO_MODE:, {AUTO_MODE}")
    if AUTO_MODE:
        # Устанавливаем задание с рандомным интервалом
        logger.info("Устанавливаем задание запуска скрипта с рандомным интервалом")
        interval_minutes = get_random_interval()
        next_run_time = datetime.now() + timedelta(minutes=interval_minutes)
        logger.info(f"Запланирован следующий запуск через {interval_minutes} минут (в {next_run_time.strftime('%Y-%m-%d %H:%M:%S')})")

        # Создаем временный PS скрипт для установки задачи с интервалом
        temp_script = PROJECT_ROOT / "automation" / "temp_install.ps1"
        with open(temp_script, "w", encoding='utf-8') as f:
            f.write(f"""#Requires -RunAsAdministrator

$taskName = "AutoMetaMaskMoreLogin"
$taskFolder = "\\Automation-MetaMask-MoreLogin\\"
$projectRoot = "{PROJECT_ROOT}"
$logPath = "$projectRoot\\automation\\task_log.txt"
$description = "Автоматический запуск скрипта MetaMask с интервалом {interval_minutes} минут. Следующий запуск: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"

# Создаем BAT-файл для надежного запуска
$batContent = @"
@echo off
chcp 65001 > nul
call "$projectRoot\\.venv\\Scripts\\activate.bat"
python "$projectRoot\\main.py" --scheduled-task >> "$logPath" 2>&1
"@
$batContent | Out-File "$projectRoot\\automation\\run_task.bat" -Encoding UTF8

# Создаем папку для задач если её нет
$taskFolderPath = $taskFolder.TrimEnd('\')
$taskFolderExists = Get-ScheduledTask -TaskPath $taskFolderPath -ErrorAction SilentlyContinue
if (-not $taskFolderExists) {{
    $null = New-Item -Path "C:\\Windows\\System32\\Tasks$taskFolderPath" -ItemType Directory -Force
    if ($?) {{
        Write-Host "Папка $taskFolderPath успешно создана"
    }} else {{
        Write-Host "Ошибка при создании папки $taskFolderPath"
        exit 1
    }}
}}

# Создаем задачу
$action = New-ScheduledTaskAction `
    -Execute "cmd.exe" `
    -Argument "/c `"$projectRoot\\automation\\run_task.bat`"" `
    -WorkingDirectory $projectRoot

$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes({interval_minutes})

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Days 365) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$principal = New-ScheduledTaskPrincipal `
    -UserId (whoami) `
    -LogonType Interactive `
    -RunLevel Highest

# Регистрируем задачу
Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskFolder -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $taskName `
    -TaskPath $taskFolder `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Description $description `
    -Force

Write-Host "SUCCESS"
""")

        if not run_powershell_script("temp_install.ps1"):
            logger.error("Не удалось установить задание в Планировщике")
        else:
            logger.info("Задание успешно установлено в Планировщике")

        # Удаляем временный скрипт
        temp_script.unlink(missing_ok=True)
    else:
        # Удаляем задание если AUTO_MODE выключен
        logger.info("Отключение автоматического режима")
        temp_script = PROJECT_ROOT / "automation" / "temp_uninstall.ps1"
        with open(temp_script, "w", encoding='utf-8') as f:
            f.write("""#Requires -RunAsAdministrator

$taskName = "AutoMetaMaskMoreLogin"
$taskFolder = "\\Automation-MetaMask-MoreLogin\\"

# Удаляем задачу
Unregister-ScheduledTask -TaskName $taskName -TaskPath $taskFolder -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "SUCCESS"
""")
        run_powershell_script("temp_uninstall.ps1")
        temp_script.unlink(missing_ok=True)
        logger.info("Задание успешно удалено из Планировщика")