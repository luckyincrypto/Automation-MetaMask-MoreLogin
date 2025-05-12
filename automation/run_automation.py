import os
from pathlib import Path
import subprocess
from datetime import datetime, timedelta
import random
from config import logger, AUTO_MODE, MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES


# Получаем абсолютный путь к корню проекта
PROJECT_ROOT = Path(__file__).parent.parent  # automation/ -> ../
# Пути
CONFIG_PATH = PROJECT_ROOT / "config.yaml"

def run_powershell_script(script_name):
    """Универсальный запуск PS скриптов из папки automation/"""
    script_path = PROJECT_ROOT / "automation" / script_name
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script_path)],
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
        return False

def get_random_interval():
    """Генерирует случайный интервал между запусками в минутах"""
    return random.randint(MIN_INTERVAL_MINUTES, MAX_INTERVAL_MINUTES)

def schedule_next_run():
    """Основная функция управления расписанием, задачами Планировщика"""
    print("AUTO_MODE:", AUTO_MODE)
    if AUTO_MODE:
        # Устанавливаем задание с рандомным интервалом
        logger.info("Активация автоматического режима")
        interval_minutes = get_random_interval()
        next_run_time = datetime.now() + timedelta(minutes=interval_minutes)
        logger.info(f"Следующий запуск через {interval_minutes} минут (в {next_run_time.strftime('%Y-%m-%d %H:%M:%S')})")

        # Создаем временный PS скрипт для установки задачи с интервалом
        temp_script = PROJECT_ROOT / "automation" / "temp_install.ps1"
        with open(temp_script, "w", encoding='utf-8') as f:
            f.write(f"""#Requires -RunAsAdministrator

$taskName = "AutoMetaMaskMoreLogin"
$projectRoot = "{PROJECT_ROOT}"
$logPath = "$projectRoot\\automation\\task_log.txt"
$description = "Автоматический запуск скрипта MetaMask с интервалом {interval_minutes} минут. Следующий запуск: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}"

# Создаем BAT-файл для надежного запуска
$batContent = @"
@echo off
call "$projectRoot\\.venv\\Scripts\\activate.bat"
python "$projectRoot\\main.py" >> "$logPath" 2>&1
"@
$batContent | Out-File "$projectRoot\\automation\\run_task.bat" -Encoding ASCII

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
Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Register-ScheduledTask `
    -TaskName $taskName `
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
        run_powershell_script("uninstall_task.ps1")
        logger.info("Задание успешно удалено из Планировщика")