import sqlite3
from datetime import datetime, timedelta
import json
from typing import Optional, List, Dict, TypedDict, Any, Tuple, Union
from contextlib import contextmanager
from config import DB_NAME, logger, config
from faucet_morkie.faucet_morkie import MonadFaucet


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
                    logger.debug("Соединение с базой данных закрыто")
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
                        row_number INTEGER NOT NULL,
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
                    "CREATE INDEX IF NOT EXISTS idx_row ON activities(row_number)",
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

    def _parse_activity_record(self, record) -> ActivityRecord:
        """Преобразует сырую запись из БД в ActivityRecord"""
        try:
            details = json.loads(record['details'])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Error parsing details JSON: {e}")
            details = {}

        return {
            'row': record['row_number'],
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
                SELECT id, row_number, details
                FROM activities
                WHERE json_valid(details) = 0
            """)
            invalid_json = cursor.fetchall()
            if invalid_json:
                logger.error(f"Found {len(invalid_json)} records with invalid JSON in details")
                return False

            # Проверяем корректность timestamp
            cursor = conn.execute("""
                SELECT id, row_number, timestamp
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

    def should_process_activity_with_connection(self, conn, row: int, wallet_address: str) -> Tuple[bool, str]:
        """
        Проверяет, нужно ли выполнять активность для профиля используя существующее соединение.
        Возвращает кортеж (нужно_ли_выполнять, причина)
        """
        try:
            cursor = conn.execute("""
                SELECT * FROM activities
                WHERE row_number = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (row,))

            last_activity = cursor.fetchone()
            if last_activity:
                last_activity = self._parse_activity_record(last_activity)

            # Если нет записей для профиля
            if not last_activity:
                logger.update(f"Для Профиля № {row} не найдено предыдущих активностей в базе данных '{self.db_path}'")
                return True, "No previous activities found"

            # Проверяем адрес кошелька
            if last_activity['wallet_address'] != wallet_address:
                logger.warning(f"Несоответствие адреса кошелька для Профиля № {row}. БД: {last_activity['wallet_address']}, Текущий: {wallet_address}")
                return True, "Wallet address changed"

            current_time = datetime.now()

            # Если последняя активность успешна
            if last_activity['status'] == 'success':
                try:
                    last_success_time = datetime.fromisoformat(last_activity['timestamp'])
                    next_allowed_time = last_success_time + timedelta(hours=24, minutes=3)

                    if current_time >= next_allowed_time:
                        logger.update(f"Для Профиля № {row} прошло 24ч 3м с последнего успеха в базе данных '{self.db_path}'")
                        return True, "24h 3m passed since last success"
                    logger.debug(f"Для Профиля № {row} ожидание до {next_allowed_time}")
                    return False, f"Waiting until {next_allowed_time}"
                except ValueError as e:
                    logger.error(f"Ошибка парсинга временной метки для Профиля № {row}: {e}")
                    return True, "Invalid timestamp format"

            # Если превышен лимит
            if last_activity['status'] == 'limit_exceeded':
                if not last_activity['next_attempt']:
                    logger.warning(f"Для Профиля № {row} не установлено время следующей попытки при превышении лимита")
                    return True, "No next attempt time set for limit_exceeded"

                try:
                    next_attempt = datetime.fromisoformat(last_activity['next_attempt'])
                    if current_time >= next_attempt:
                        logger.update(f"Для Профиля № {row} достигнуто время следующей попытки в базе данных '{self.db_path}'")
                        return True, "Next attempt time reached"
                    logger.debug(f"Для Профиля № {row} ожидание до следующей попытки: {next_attempt}")
                    return False, f"Waiting until next attempt: {next_attempt}"
                except (ValueError, TypeError) as e:
                    logger.error(f"Ошибка парсинга времени следующей попытки для Профиля № {row}: {e}")
                    return True, "Invalid next_attempt time format"

            # Для других статусов
            logger.warning(f"Неожиданный статус для Профиля № {row}: {last_activity['status']}")
            return True, f"Unexpected status: {last_activity['status']}"
        except DatabaseError as e:
            logger.error(f"Ошибка базы данных в should_process_activity: {e}")
            return True, f"Database error: {e}"

    def insert_activity_with_connection(self, conn, row: int, activity_data: Dict[str, Any]):
        """Вставляет активность с указанием номера строки используя существующее соединение"""
        try:
            self._validate_activity_data(activity_data)
            activity_data['row_number'] = row

            conn.execute("""
                INSERT INTO activities (
                    row_number, activity_type, status, wallet_address,
                    next_attempt, details
                ) VALUES (:row_number, :activity_type, :status, :wallet_address,
                         :next_attempt, :details)
            """, {
                'row_number': row,
                'activity_type': activity_data['activity_type'],
                'status': activity_data['status'],
                'wallet_address': activity_data['wallet_address'],
                'next_attempt': activity_data.get('next_claim'),
                'details': json.dumps(activity_data)
            })
            message = activity_data.get('message', '')
            logger.update(f"Активность успешно добавлена для Профиля № {row}: {activity_data['activity_type']} - {activity_data['status']} - {message}")
        except (sqlite3.Error, ValueError) as e:
            logger.error(f"Ошибка добавления активности для Профиля № {row}: {e}")
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
                    WHERE row_number = ?
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
                        SELECT row_number, MAX(timestamp) as max_ts
                        FROM activities
                        WHERE row_number IN ({','.join(['?'] * len(rows))})
                        GROUP BY row_number
                    ) b ON a.row_number = b.row_number AND a.timestamp = b.max_ts
                """, rows)

                return [self._parse_activity_record(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting profiles status: {e}")
            raise DatabaseError(f"Failed to get profiles status: {e}")

    def should_process_activity(self, row: int, wallet_address: str) -> Tuple[bool, str]:
        """
        Проверяет, нужно ли выполнять активность для профиля.
        Возвращает кортеж (нужно_ли_выполнять, причина)
        """
        try:
            with self._get_connection() as conn:
                return self.should_process_activity_with_connection(conn, row, wallet_address)
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
                            SELECT id, ROW_NUMBER() OVER (
                                PARTITION BY row_number ORDER BY timestamp DESC
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


def process_activity(driver, wallet_mm_from_browser_extension, row):
    try:
        db = SQLiteDatabase()
        with db._get_connection() as conn:
            # Проверяем целостность данных
            if not db.check_data_integrity_with_connection(conn):
                logger.warning("Data integrity check failed, attempting to continue")

            # Проверяем, нужно ли выполнять активность
            should_process, reason = db.should_process_activity_with_connection(conn, row, wallet_mm_from_browser_extension)

            if not should_process:
                logger.info(f"Skipping activity for Профиль № {row}: {reason}")
                return

            # Если статус неожиданный, проверяем настройки
            if "Unexpected status" in reason:
                if not config.ACTIVITY_SETTINGS['AUTO_PROCESS_UNEXPECTED_STATUS']:
                    logger.warning(f"Unexpected status for Профиль № {row}. Reason: {reason}")
                    user_choice = input("Do you want to process this activity? (y/n): ").lower()
                    if user_choice != 'y':
                        logger.info("Activity skipped by user")
                        return

            # Выполняем активность
            try:
                result = MonadFaucet.process(driver, wallet_mm_from_browser_extension)
                print("Результат выполнения активности:", result)
                # Сохраняем результат
                db.insert_activity_with_connection(conn, row, result)
                logger.update(f"Activity processed and saved for Профиль № {row}")
            except Exception as e:
                logger.error(f"Error processing activity for Профиль № {row}: {e}")
                raise
    except DatabaseError as e:
        logger.error(f"Database error in process_activity: {e}")
        raise


def check_database_content():
    """Проверяет и выводит содержимое базы данных"""
    try:
        with SQLiteDatabase() as db:
            with db._get_connection() as conn:
                # Получаем все записи, отсортированные по времени
                cursor = conn.execute("""
                    SELECT row_number, activity_type, status, wallet_address,
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
                        f"\nПрофиль № {record['row_number']}\n"
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


# if __name__ == "__main__":
#     # Если файл запущен напрямую, показываем содержимое базы данных
#     check_database_content()