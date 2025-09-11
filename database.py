import sqlite3
import sys
from datetime import datetime, timedelta
import json
from pprint import pprint
from typing import Optional, List, Dict, TypedDict, Any, Tuple, Union
from contextlib import contextmanager
from config import DB_NAME, logger, config, DEFAULT_ACTIVITIES
from fantasy.fantasy import Fantasy
from faucet_morkie.faucet_morkie import MonadFaucet
import random
import os

logger.debug(f"Путь к БД активностей: {os.path.abspath(DB_NAME)}")
logger.debug(f"Доступ на запись БД активностей: {os.access(DB_NAME, os.W_OK)}")

class ActivityRecord(TypedDict):
    row: int
    status: str
    next_attempt: Optional[str]
    activity_type: str
    wallet_address: str
    details: Dict[str, Any]
    timestamp: str


class DatabaseError(Exception):
    """Базовый класс для ошибок базы данных"""
    pass


class SQLiteDatabase:
    def __init__(self, db_path: str = DB_NAME):
        self.db_path = db_path
        try:
            self._initialize_db()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise DatabaseError(f"Database initialization failed: {e}")

    def _initialize_db(self):
        """Инициализирует БД при первом подключении"""
        with self._get_connection() as conn:
            try:
                conn.execute("PRAGMA journal_mode=WAL")  # Для лучшей производительности
                conn.execute("PRAGMA foreign_keys=ON")

                # Проверяем существование таблицы activities
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type='table' AND name='activities'
                """)
                if not cursor.fetchone():
                    self._create_tables(conn)
                    logger.update(f"База данных '{self.db_path}' успешно инициализирована")
                else:
                    logger.debug(f"База данных '{self.db_path}' уже инициализирована")
            except sqlite3.Error as e:
                logger.error(f"Ошибка инициализации базы данных: {e}")
                raise DatabaseError(f"Failed to initialize database: {e}")

    @contextmanager
    def _get_connection(self):
        """Контекстный менеджер для соединения"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            logger.debug(f"Установлено соединение с базой данных: {self.db_path}")
            yield conn
        except sqlite3.Error as e:
            logger.error(f"Ошибка соединения с базой данных: {e}")
            raise DatabaseError(f"Failed to connect to database: {e}")
        finally:
            if conn:
                try:
                    conn.close()
                    logger.debug("Соединение с базой данных закрыто\n")
                except sqlite3.Error as e:
                    logger.error(f"Ошибка при закрытии соединения с базой данных: {e}")

    def _create_tables(self, conn):
        """Создает таблицы и индексы"""
        try:
            with conn:
                logger.debug("Создание таблиц базы данных...")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS activities (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        profile_number INTEGER NOT NULL,
                        activity_type TEXT NOT NULL,
                        status TEXT NOT NULL,
                        wallet_address TEXT NOT NULL,
                        next_attempt TIMESTAMP,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        details TEXT NOT NULL
                    )
                """)

                # Создаем индексы атомарно
                indexes = [
                    "CREATE INDEX IF NOT EXISTS idx_row ON activities(profile_number)",
                    "CREATE INDEX IF NOT EXISTS idx_status ON activities(status)",
                    "CREATE INDEX IF NOT EXISTS idx_wallet ON activities(wallet_address)",
                    "CREATE INDEX IF NOT EXISTS idx_type ON activities(activity_type)",
                    "CREATE INDEX IF NOT EXISTS idx_timestamp ON activities(timestamp)"
                ]
                for index_sql in indexes:
                    conn.execute(index_sql)
                logger.update("Таблицы и индексы базы данных успешно созданы")
        except sqlite3.Error as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise DatabaseError(f"Failed to create tables: {e}")

    def _validate_activity_data(self, data: Dict):
        """Проверяет обязательные поля"""
        required = ['activity_type', 'status', 'wallet_address']
        if missing := [field for field in required if field not in data]:
            raise ValueError(f"Missing required fields: {missing}")
        if 'next_attempt' not in data:
            data['next_attempt'] = datetime.now() + timedelta(hours=24)  # По умолчанию через 24 часа значение


    def _parse_activity_record(self, record) -> ActivityRecord:
        """Преобразует сырую запись из БД в ActivityRecord"""
        try:
            details = json.loads(record['details'])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing details JSON: {e}")
            details = {}

        return {
            'row': record['profile_number'],
            'status': record['status'],
            'next_attempt': record['next_attempt'],
            'activity_type': record['activity_type'],
            'wallet_address': record['wallet_address'],
            'details': details,
            'timestamp': record['timestamp']
        }

    def check_data_integrity_with_connection(self, conn) -> bool:
        """Проверяет целостность данных в базе используя существующее соединение"""
        try:
            # Проверяем наличие некорректных JSON в details
            cursor = conn.execute("""
                SELECT id, profile_number, details
                FROM activities
                WHERE json_valid(details) = 0
            """)
            invalid_json = cursor.fetchall()
            if invalid_json:
                logger.error(f"Found {len(invalid_json)} records with invalid JSON in details")
                return False

            # Проверяем корректность timestamp
            cursor = conn.execute("""
                SELECT id, profile_number, timestamp
                FROM activities
                WHERE datetime(timestamp) IS NULL
            """)
            invalid_timestamps = cursor.fetchall()
            if invalid_timestamps:
                logger.error(f"Found {len(invalid_timestamps)} records with invalid timestamps")
                return False

            logger.info("Data integrity check passed successfully")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error checking data integrity: {e}")
            raise DatabaseError(f"Failed to check data integrity: {e}")

    def should_process_activity_with_connection(self, conn, row: int, wallet_address: str,
                                                activity_types: Optional[List[str]], default_activities: Optional[List[str]]) -> \
    tuple[bool, Any, str] | tuple[bool, list[Any]]:
        """
        Проверяет, нужно ли выполнять активность для профиля, используя существующее соединение.

        Универсальная логика:
        - Если `activity_types=None` или пустой список, используем DEFAULT_ACTIVITIES `['Monad_Faucet_Portal', 'Fantasy_Claim_XP']`.
        - Возвращает **только последнюю запись** для каждой активности.

        Возвращает:
        - `Tuple[bool, str]`: флаг выполнения и причина.
        """
        global activity
        activity_type_carry_out_list = []
        try:
            if not activity_types:
                activity_types = default_activities
                logger.debug(f"Using default activities: {activity_types}")
            else:
                logger.debug(f"Using provided activities: {activity_types}")

            # Проверяем наличие записей для профиля
            check_query = "SELECT COUNT(*) as count FROM activities WHERE profile_number = ?"
            cursor = conn.execute(check_query, (row,))
            count = cursor.fetchone()['count']
            logger.debug(f"Total records for profile {row}: {count}")

            # Динамически формируем SQL-запрос
            query = f"""
                SELECT * FROM activities AS a
                WHERE profile_number = ?
                AND activity_type IN ({', '.join(['?' for _ in activity_types])})
                AND timestamp = (
                    SELECT MAX(timestamp) FROM activities AS sub
                    WHERE sub.profile_number = a.profile_number
                    AND sub.activity_type = a.activity_type
                )
                ORDER BY timestamp DESC
            """

            # Выполняем запрос с правильным количеством параметров
            params = [row] + activity_types  # Создаем список параметров: [row, activity_type1, activity_type2, ...]
            logger.debug(f"Executing query with params: {params}")
            cursor = conn.execute(query, params)
            last_activities = cursor.fetchall()

            # Подробное логирование результатов
            if last_activities:
                logger.debug(f"Found {len(last_activities)} activities for profile {row}:")
                for activity in last_activities:
                    logger.debug(f"Activity: type={activity['activity_type']}, status={activity['status']}, timestamp={activity['timestamp']}")
            else:
                logger.debug(f"No activities found for profile {row} with types {activity_types}")

            # Если нет записей, проверяем почему
            if not last_activities:
                # Проверяем записи для профиля без фильтра по activity_type
                check_query = """
                    SELECT activity_type, COUNT(*) as count, MAX(timestamp) as last_timestamp
                    FROM activities
                    WHERE profile_number = ?
                    GROUP BY activity_type
                """
                cursor = conn.execute(check_query, (row,))
                activity_counts = cursor.fetchall()
                logger.debug(f"Activity counts for profile {row}:")
                for count in activity_counts:
                    logger.debug(f"Type: {count['activity_type']}, Count: {count['count']}, Last: {count['last_timestamp']}")

                # Все запрошенные активности должны быть выполнены
                return True, activity_types


            # Преобразуем записи в удобный формат
            parsed_activities = [self._parse_activity_record(activity) for activity in last_activities]
            logger.debug(f"Parsed activities for profile {row}: {parsed_activities}")

            current_time = datetime.now()

            # Проверяем статус последней активности
            for activity in parsed_activities:

                if activity['status'] == 'success':
                    try:
                        last_success_time = datetime.strptime(activity['timestamp'], '%Y-%m-%d %H:%M:%S')
                        next_allowed_time = last_success_time + timedelta(hours=24, minutes=3)

                        if current_time >= next_allowed_time:
                            logger.debug(f"Waiting time passed since last success, {activity['activity_type']} activity will be carried out")
                            activity_type_carry_out_list.append(activity['activity_type'])
                        logger.debug(f"Waiting until {next_allowed_time.strftime('%Y-%m-%d %H:%M:%S')}")

                    except ValueError as e:
                        logger.error(f"Invalid timestamp format, {activity['activity_type']} activity will be carried out")
                        activity_type_carry_out_list.append(activity['activity_type'])


                elif activity['status'] == 'limit_exceeded':
                    try:
                        if activity['next_attempt']:
                            next_attempt = datetime.strptime(activity['next_attempt'], '%Y-%m-%d %H:%M:%S')
                            if current_time >= next_attempt:
                                logger.debug(f"Next attempt time reached, {activity['activity_type']} activity will be carried out")
                                activity_type_carry_out_list.append(activity['activity_type'])

                            logger.debug(f"Waiting until next attempt: {next_attempt.strftime('%Y-%m-%d %H:%M:%S')}")
                        else:
                            logger.warning(f"No next_attempt time for limit_exceeded status in {activity['activity_type']}, activity will be carried out")
                            activity_type_carry_out_list.append(activity['activity_type'])

                    except ValueError as e:
                        logger.error(f" Invalid next_attempt time format, {activity['activity_type']} activity will be carried out")
                        activity_type_carry_out_list.append(activity['activity_type'])


                elif activity['status'] == 'error' or activity['status'] not in ['success', 'limit_exceeded']:
                    logger.warning(f"Неожиданный статус для Профиля № {row}: {activity['status']}")
                    if hasattr(config, 'activity_settings') and config.activity_settings.get(
                            'AUTO_PROCESS_UNEXPECTED_STATUS', True):
                        logger.debug(f"Unexpected status: {activity['status']}, {activity['activity_type']} activity will be carried out")
                        activity_type_carry_out_list.append(activity['activity_type'])

                    logger.debug(f"Unexpected status: {activity['status']} (auto-processing disabled)")

            return True, activity_type_carry_out_list

        except Exception as e:
            logger.error(f"Ошибка базы данных в should_process_activity_with_connection: {e}")
            return True, activity_type_carry_out_list

    def insert_activity_with_connection(self, conn, row: int, activity_data: Dict[str, Any]):
        """Вставляет активность с указанием номера строки используя существующее соединение"""
        try:
            logger.debug(f"Начало вставки данных для Профиля № {row}")

            self._validate_activity_data(activity_data)
            activity_data['profile_number'] = row

            # Создаем копию данных для details, исключая основные поля
            details = activity_data.copy()
            fields_to_exclude = ['profile_number', 'activity_type', 'status', 'wallet_address', 'next_attempt']
            for field in fields_to_exclude:
                details.pop(field, None)

            # Подготовка параметров для вставки
            params = {
                'profile_number': row,
                'activity_type': activity_data['activity_type'],
                'status': activity_data['status'],
                'wallet_address': activity_data['wallet_address'],
                'next_attempt': activity_data.get('next_attempt'),
                'details': json.dumps(details, ensure_ascii=False)
            }

            # Выполнение вставки с использованием локального времени
            cursor = conn.execute("""
                INSERT INTO activities (
                    profile_number, activity_type, status, wallet_address,
                    next_attempt, timestamp, details
                ) VALUES (:profile_number, :activity_type, :status, :wallet_address,
                         :next_attempt, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'), :details)
            """, params)

            # Проверка результата вставки
            if cursor.rowcount != 1:
                raise sqlite3.Error(f"Failed to insert row: {cursor.rowcount} rows affected")

            # Подтверждение транзакции
            conn.commit()
            logger.debug(f"Транзакция подтверждена для Профиля № {row}")

            message = activity_data.get('message', '')
            logger.update(f"Активность успешно добавлена для Профиля № {row}: {activity_data['activity_type']} - {activity_data['status']} - {message}")

            # Проверка вставленной записи
            cursor = conn.execute("""
                SELECT * FROM activities WHERE id = last_insert_rowid()
            """)
            inserted_row = cursor.fetchone()
            if inserted_row:
                logger.debug(f"Проверка вставленной записи: {dict(inserted_row)}")
            else:
                logger.error("Не удалось найти вставленную запись")

        except (sqlite3.Error, ValueError) as e:
            logger.error(f"Ошибка добавления активности для Профиля № {row}: {e}")
            conn.rollback()
            raise DatabaseError(f"Failed to insert activity: {e}")

    def insert_activity(self, row: int, activity_data: Dict[str, Any]):
        """Вставляет активность с указанием номера строки"""
        try:
            with self._get_connection() as conn:
                self.insert_activity_with_connection(conn, row, activity_data)
        except (sqlite3.Error, ValueError) as e:
            logger.error(f"Ошибка добавления активности для Профиля № {row}: {e}")
            raise DatabaseError(f"Failed to insert activity: {e}")

    def get_profile_status(self, row: int) -> Optional[ActivityRecord]:
        """Возвращает последнюю активность профиля"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM activities
                    WHERE profile_number = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (row,))

                if record := cursor.fetchone():
                    return self._parse_activity_record(record)
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting profile status for Профиль № {row}: {e}")
            raise DatabaseError(f"Failed to get profile status: {e}")

    def get_profiles_status(self, rows: List[int]) -> List[ActivityRecord]:
        """Возвращает последние активности для списка профилей"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(f"""
                    SELECT a.* FROM activities a
                    INNER JOIN (
                        SELECT profile_number, MAX(timestamp) as max_ts
                        FROM activities
                        WHERE profile_number IN ({','.join(['?'] * len(rows))})
                        GROUP BY profile_number
                    ) b ON a.profile_number = b.profile_number AND a.timestamp = b.max_ts
                """, rows)

                return [self._parse_activity_record(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting profiles status: {e}")
            raise DatabaseError(f"Failed to get profiles status: {e}")

    def should_process_activity(self, row: int, wallet_address: str, activity_types) -> tuple[bool, str, str] | tuple[
        bool, str]:
        """
        Проверяет, нужно ли выполнять активность для профиля.
        Возвращает кортеж (нужно_ли_выполнять, причина)
        """
        try:
            logger.debug(f"DEFAULT_ACTIVITIES before call: {DEFAULT_ACTIVITIES}")
            with self._get_connection() as conn:
                return self.should_process_activity_with_connection(conn, row, wallet_address, activity_types, DEFAULT_ACTIVITIES)
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в should_process_activity для Профиля № {row}: {e}")
            return True, f"Database error: {e}"

    def cleanup_old_records(self, keep_last: int = 5):
        """Оставляет только N последних записей для каждого профиля"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    DELETE FROM activities
                    WHERE id NOT IN (
                        SELECT id FROM (
                            SELECT id, profile_number() OVER (
                                PARTITION BY profile_number ORDER BY timestamp DESC
                            ) as rn FROM activities
                        ) WHERE rn <= ?
                    )
                """, (keep_last,))
                logger.update(f"Очистка старых записей завершена в базе данных '{self.db_path}'. Оставлено {keep_last} последних записей для каждого профиля")
        except sqlite3.Error as e:
            logger.error(f"Ошибка при очистке старых записей: {e}")
            raise DatabaseError(f"Failed to cleanup old records: {e}")

    def check_data_integrity(self) -> bool:
        """Проверяет целостность данных в базе"""
        try:
            with self._get_connection() as conn:
                return self.check_data_integrity_with_connection(conn)
        except sqlite3.Error as e:
            logger.error(f"Error checking data integrity: {e}")
            raise DatabaseError(f"Failed to check data integrity: {e}")

    def close(self):
        """Для совместимости с контекстным менеджером"""
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get_random_eligible_profile(self, activity_types=None) -> Optional[Tuple[int, str]]:
        """
        Выбирает случайный профиль, готовый к обработке
        Возвращает (row_number, wallet_address) или None если нет подходящих
        """
        try:
            with self._get_connection() as conn:
                # Получаем все профили из базы
                cursor = conn.execute("""
                    SELECT profile_number, MAX(wallet_address) as wallet_address 
                    FROM activities 
                    GROUP BY profile_number
                    ORDER BY profile_number
                """)
                all_profiles = cursor.fetchall()

                if not all_profiles:
                    logger.info("В базе нет профилей для обработки")
                    return None

                eligible_profiles = []
                for profile in all_profiles:
                    row, wallet_address = profile['profile_number'], profile['wallet_address']

                    # Используем существующую логику проверки
                    should_process, activity_type_carry_out_list = self.should_process_activity_with_connection(
                        conn, row, wallet_address, activity_types, DEFAULT_ACTIVITIES
                    )

                    if should_process and activity_type_carry_out_list:
                        eligible_profiles.append((row, wallet_address))
                        logger.debug(f"Профиль {row} подходит для обработки:{activity_type_carry_out_list}")
                    else:
                        logger.debug(f"Профиль {row} не подходит: {activity_type_carry_out_list}")

                if not eligible_profiles:
                    logger.info("Нет профилей, готовых к обработке")
                    return None

                # Выбираем случайный профиль из подходящих
                selected_row, selected_wallet = random.choice(eligible_profiles)
                logger.info(
                    f"Выбран случайный профиль для обработки: № {selected_row}, "
                    f"адрес: {selected_wallet[:6]}...{selected_wallet[-4:]}"
                )

                return selected_row, selected_wallet

        except sqlite3.Error as e:
            logger.error(f"Ошибка при выборе профиля: {str(e)}")
            return None


def process_activity(driver, wallet_mm_from_browser_extension, row, activity_types):
    logger.info(f"Начало обработки Профиль № {row}, адрес: {wallet_mm_from_browser_extension}")
    try:
        db = SQLiteDatabase()
        with db._get_connection() as conn:
            # Проверяем целостность данных
            if not db.check_data_integrity_with_connection(conn):
                logger.warning("Data integrity check failed, attempting to continue")

            # activity_type_carry_out_list = []

            # Проверяем, нужно ли выполнять активность
            should_process, activity_type_carry_out_list = db.should_process_activity_with_connection(conn, row, wallet_mm_from_browser_extension, activity_types, DEFAULT_ACTIVITIES)
            logger.debug(f"Проверка необходимости обработки: should_process={should_process}, "
                         f"activity_type_carry_out={activity_type_carry_out_list}")

            if not should_process:
                logger.update(f"Пропуск активности для Профиль № {row}.")
                return False


            # Обрабатываем каждую активность из списка или из DEFAULT_ACTIVITIES
            for activity_type in activity_types or DEFAULT_ACTIVITIES:
                try:
                    for activity_type_carry_out in list(set(activity_type_carry_out_list)):
                        if activity_type_carry_out == activity_type:
                            logger.debug(f"Активность {activity_type} для Профиля № {row}")

                            if activity_type == 'Monad_Faucet_Portal':
                                logger.debug(f"Активность {activity_type}. Вызов MonadFaucet.process для Профиля № {row}")
                                result = MonadFaucet.process(driver, wallet_mm_from_browser_extension)

                            if activity_type == 'Fantasy_Claim_XP':
                                logger.debug(f"Активность {activity_type}. Вызов Fantasy.fantasy для Профиля № {row}")
                                fantasy_instance = Fantasy(driver)
                                result = fantasy_instance.fantasy()

                            # Сохраняем результат
                            logger.debug(f"Начало сохранения результата активности {activity_type} в БД для Профиля № {row}")
                            if result:
                                logger.debug(f"Результат выполнения активности {activity_type} для Профиля № {row}: {result}")
                                # Сохраняем результат
                                db.insert_activity_with_connection(conn, row, result)
                                logger.debug(f"Результат активности {activity_type} успешно сохранен в БД для Профиля № {row}\n")
                            else:
                                logger.warning(f"Активность {activity_type} не вернула результат для Профиля № {row}")

                except Exception as e:
                    logger.error(f"Error processing активности {activity_type} for Профиль № {row}: {e}")
                    # Создаем запись об ошибке
                    error_data = {
                        'activity_type': activity_type,
                        'status': 'error',
                        'wallet_address': wallet_mm_from_browser_extension,
                        'next_attempt': None,
                        'details': {
                            'error': str(e),
                            'timestamp': datetime.now().isoformat()
                        }
                    }
                    db.insert_activity_with_connection(conn, row, error_data)
                    continue  # Продолжаем с следующей активностью

            logger.update(f"Все активности завершены для Профиля № {row}")
            return True

    except DatabaseError as e:
        logger.error(f"Database error in process_activity: {e}")
        raise


def process_random_profile():
    """Обрабатывает случайный подходящий профиль"""
    db = SQLiteDatabase()
    profile = db.get_random_eligible_profile()

    if not profile:
        logger.info("Нет подходящих профилей для обработки")
        sys.exit(0)  # Корректный выход с кодом 0 (успех)

    row, wallet = profile
    logger.info(f"Обработка случайного профиля {row}...")
    return row, wallet



def check_database_content():
    """Проверяет и выводит содержимое базы данных"""
    try:
        with SQLiteDatabase() as db:
            with db._get_connection() as conn:
                # Получаем все записи, отсортированные по времени
                cursor = conn.execute("""
                    SELECT profile_number, activity_type, status, wallet_address,
                           next_attempt, timestamp, details
                    FROM activities
                    ORDER BY timestamp DESC
                """)

                records = cursor.fetchall()
                if not records:
                    logger.info("База данных пуста")
                    return

                logger.info(f"\n{'='*100}\nСодержимое базы данных (всего записей: {len(records)}):\n{'='*100}")

                for record in records:
                    try:
                        details = json.loads(record['details'])
                    except (json.JSONDecodeError, TypeError):
                        details = {}

                    logger.info(
                        f"\nПрофиль № {record['profile_number']}\n"
                        f"Тип активности: {record['activity_type']}\n"
                        f"Статус: {record['status']}\n"
                        f"Адрес: {record['wallet_address']}\n"
                        f"Следующая попытка: {record['next_attempt']}\n"
                        f"Время: {record['timestamp']}\n"
                        f"Детали: {json.dumps(details, indent=2, ensure_ascii=False)}\n"
                        f"{'-'*100}"
                    )
    except Exception as e:
        logger.error(f"Ошибка при проверке содержимого базы данных: {e}")
# Для проверки через Python
def print_all_records(db_path):
    with sqlite3.connect(db_path) as conn:
        logger.info("\nВывод последних 10 записей из БД:\n")
        cursor = conn.cursor()
        logger.info("\nВывод последних 10 записей из БД:\n")
        cursor.execute("SELECT * FROM activities ORDER BY id DESC LIMIT 10")
        # for row in cursor.fetchall():
        #     logger.info(f'row: {row}')
        logger.info(f"Получен результат: {json.dumps(cursor.fetchall(), indent=2)}")


if __name__ == "__main__":
    # Если файл запущен напрямую, показываем содержимое базы данных
    check_database_content()
    # print_all_records(os.path.abspath(DB_NAME))

    db = SQLiteDatabase()
    # info = db.get_profiles_status(rows=[1,2,3,4,5,6,7,8,9,10])
    # for _ in info:
    #     pprint(_)
    # pprint(db.get_profile_status(1))
    # pprint(info)