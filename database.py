import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json
from datetime import datetime

from config import logger


class Database:
    def __init__(self, dbname, user, password, host='localhost', port='5432'):
        self.conn_params = {
            'dbname': dbname,
            'user': user,
            'password': password,
            'host': host,
            'port': port
        }
        self._create_tables()

    def _connect(self):
        return psycopg2.connect(**self.conn_params)

    def _create_tables(self):
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS activities (
                    id SERIAL PRIMARY KEY,
                    activity_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    message TEXT,
                    wallet_address VARCHAR(42) NOT NULL,
                    transaction_hash VARCHAR(66),
                    next_attempt TIMESTAMP,
                    attempt INTEGER NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details JSONB
                );

                -- Индексы для ускорения поиска
                CREATE INDEX IF NOT EXISTS idx_activity_type ON activities (activity_type);
                CREATE INDEX IF NOT EXISTS idx_wallet_address ON activities (wallet_address);
                CREATE INDEX IF NOT EXISTS idx_status ON activities (status);
                CREATE INDEX IF NOT EXISTS idx_timestamp ON activities (timestamp);
                CREATE INDEX idx_row_number ON activities(row_number);
            """)
            conn.commit()

    def insert_activity(self, row, activity_data):
        """Добавляет активность с указанием номера строки"""
        if not isinstance(activity_data, dict) or 'activity_type' not in activity_data:
            for activity_type, data in activity_data.items():
                flat_data = {
                    'activity_type': activity_type,
                    'row_number': row,  # Добавляем номер строки
                    **data
                }
                self._insert_single_activity(flat_data)
        else:
            activity_data['row_number'] = row  # Добавляем номер строки
            self._insert_single_activity(activity_data)

    def _insert_single_activity(self, data):
        """Вставляет одну запись с номером строки"""
        required = ['activity_type', 'status', 'wallet_address', 'row_number']
        if not all(field in data for field in required):
            raise ValueError(f"Missing required fields: {required}")

        # Собираем только дополнительные поля для JSON
        json_data = {
            k: v for k, v in data.items()
            if k not in [
                'activity_type', 'status', 'wallet_address',
                'message', 'transaction', 'next_claim', 'attempt', 'row_number'
            ]
        }

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO activities (
                    activity_type, status, message, wallet_address,
                    transaction_hash, next_attempt, attempt, details, row_number
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['activity_type'],
                data['status'],
                data.get('message'),
                data['wallet_address'],
                data.get('transaction'),
                data.get('next_claim'),
                data.get('attempt', 1),
                Json(json_data) if json_data else None,  # Только дополнительные данные
                data['row_number']  # Номер строки
            ))
            conn.commit()

    def get_activities(self, filters=None):
        """
        Получает активности с возможностью фильтрации
        filters = {
            'activity_type': 'Monad_Faucet_Portal',
            'wallet_address': '0x...',
            'status': 'success',
            'date_from': '2025-05-01',
            'date_to': '2025-05-31'
        }
        """
        with self._connect() as conn, conn.cursor() as cur:
            base_query = "SELECT * FROM activities WHERE 1=1"
            params = []

            if filters:
                if 'activity_type' in filters:
                    base_query += " AND activity_type = %s"
                    params.append(filters['activity_type'])

                if 'wallet_address' in filters:
                    base_query += " AND wallet_address = %s"
                    params.append(filters['wallet_address'])

                if 'status' in filters:
                    base_query += " AND status = %s"
                    params.append(filters['status'])

                if 'date_from' in filters:
                    base_query += " AND timestamp >= %s"
                    params.append(filters['date_from'])

                if 'date_to' in filters:
                    base_query += " AND timestamp <= %s"
                    params.append(filters['date_to'])

            base_query += " ORDER BY timestamp DESC"
            cur.execute(base_query, params)
            return cur.fetchall()

    def get_last_activity(self, wallet_address, activity_type=None):
        """
        Получает последнюю активность для кошелька
        (опционально фильтрует по типу активности)
        """
        with self._connect() as conn, conn.cursor() as cur:
            query = "SELECT * FROM activities WHERE wallet_address = %s"
            params = [wallet_address]

            if activity_type:
                query += " AND activity_type = %s"
                params.append(activity_type)

            query += " ORDER BY timestamp DESC LIMIT 1"
            cur.execute(query, params)
            return cur.fetchone()

    def get_activities_by_row(self, row):
        """Получает все активности для указанной строки"""
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM activities 
                WHERE row_number = %s
                ORDER BY timestamp DESC
            """, (row,))
            return cur.fetchall()

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def get_profile_status(self, row):
        """
        Возвращает статус профиля и время следующей попытки (если статус не success)
        :param row: Номер строки/профиля
        :return: dict {'row': int, 'status': str, 'next_attempt': datetime или None}
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    row_number,
                    status,
                    next_attempt
                FROM activities
                WHERE row_number = %s
                ORDER BY timestamp DESC
                LIMIT 1
            """, (row,))

            result = cur.fetchone()

            if not result:
                return None

            return {
                'row': result[0],
                'status': result[1],
                'next_attempt': result[2]
            }

    def get_profiles_status(self, rows):
        """
        Возвращает статусы для нескольких профилей
        :param rows: Список номеров строк
        :return: Список dict {'row': int, 'status': str, 'next_attempt': datetime}
        """
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                SELECT DISTINCT ON (row_number)
                    row_number,
                    status,
                    next_attempt
                FROM activities
                WHERE row_number = ANY(%s)
                ORDER BY row_number, timestamp DESC
            """, (rows,))

            return [
                {'row': r[0],
                 'status': r[1],
                 'next_attempt': r[2]}
                for r in cur.fetchall()
            ]




