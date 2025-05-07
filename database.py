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
            """)
            conn.commit()

    # def insert_activity(self, activity_data):
    #     """
    #     Вставляет данные активности в базу данных
    #     Формат activity_data:
    #     {
    #         'activity_type': 'Monad_Faucet_Portal',  # или 'Swap_MON', 'Nft_buy' и т.д.
    #         'status': 'success'|'limit_exceeded'|'failed'|'pending',
    #         'message': '...',
    #         'wallet_address': '0x...',
    #         'transaction': '0x...',  # опционально
    #         'next_claim': '2025-05-07 21:24:30',  # опционально
    #         'attempt': 1
    #     }
    #     """
    #     with self._connect() as conn, conn.cursor() as cur:
    #         query = sql.SQL("""
    #             INSERT INTO activities (
    #                 activity_type, status, message, wallet_address,
    #                 transaction_hash, next_attempt, attempt, details
    #             ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    #         """)
    #
    #         params = (
    #             activity_data['activity_type'],
    #             activity_data['status'],
    #             activity_data.get('message'),
    #             activity_data['wallet_address'],
    #             activity_data.get('transaction'),
    #             activity_data.get('next_claim'),
    #             activity_data.get('attempt', 1),
    #             Json(activity_data)
    #         )
    #
    #         cur.execute(query, params)
    #         conn.commit()
    #         logger.info(f"Inserted activity: {activity_data['activity_type']}")

    def insert_activity(self, activity_data):
        # Если данные пришли в формате {'Monad_Faucet_Portal': {...}}
        if not isinstance(activity_data, dict) or 'activity_type' not in activity_data:
            for activity_type, data in activity_data.items():
                flat_data = {
                    'activity_type': activity_type,
                    **data
                }
                self._insert_single_activity(flat_data)
        else:
            self._insert_single_activity(activity_data)

    def _insert_single_activity(self, data):
        """Вставляет одну запись с плоской структурой"""
        required = ['activity_type', 'status', 'wallet_address']
        if not all(field in data for field in required):
            raise ValueError(f"Missing required fields: {required}")

        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("""
                INSERT INTO activities (
                    activity_type, status, message, wallet_address,
                    transaction_hash, next_attempt, attempt, details
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['activity_type'],
                data['status'],
                data.get('message'),
                data['wallet_address'],
                data.get('transaction'),
                data.get('next_claim'),  # переименовываем next_claim -> next_attempt
                data.get('attempt', 1),
                Json(data)
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

    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()