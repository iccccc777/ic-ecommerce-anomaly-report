import os
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTGRES_SQL_DIR = ROOT / "sql" / "postgresql"
REQUIRED_SQL_FILES = [
    "01_schema.sql",
    "02_daily_metrics.sql",
    "03_funnel.sql",
    "04_retention.sql",
    "05_attribution_category.sql",
    "06_attribution_hour.sql",
    "07_attribution_user_segment.sql",
]
SQLITE_ONLY_TOKENS = [
    "strftime",
    "unixepoch",
    "julianday",
    "PRAGMA",
]
BEIJING = timezone(timedelta(hours=8))


def beijing_ts(year, month, day, hour):
    return int(datetime(year, month, day, hour, tzinfo=BEIJING).timestamp())


class PostgresMigrationTest(unittest.TestCase):
    def test_dialect_files_exist(self):
        for filename in REQUIRED_SQL_FILES:
            self.assertTrue(
                (POSTGRES_SQL_DIR / filename).is_file(),
                f"missing PostgreSQL SQL file: {filename}",
            )

    def test_postgres_queries_do_not_contain_sqlite_only_functions(self):
        for filename in REQUIRED_SQL_FILES:
            sql = (POSTGRES_SQL_DIR / filename).read_text(encoding="utf-8")
            upper_sql = sql.upper()
            for token in SQLITE_ONLY_TOKENS:
                self.assertNotIn(
                    token.upper(),
                    upper_sql,
                    f"{filename} contains SQLite-only token: {token}",
                )


class PostgresMigrationIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        port = os.getenv("POSTGRES_TEST_PORT")
        if not port:
            raise unittest.SkipTest("POSTGRES_TEST_PORT is not configured")

        import psycopg

        cls.psycopg = psycopg
        cls.database = os.getenv("POSTGRES_TEST_DATABASE", "ic_ecommerce_test")
        cls.connection_args = {
            "host": os.getenv("POSTGRES_TEST_HOST", "127.0.0.1"),
            "port": int(port),
            "user": os.getenv("POSTGRES_TEST_USER", "postgres"),
            "password": os.getenv("POSTGRES_TEST_PASSWORD", "postgres"),
        }

        admin = psycopg.connect(
            dbname="postgres",
            autocommit=True,
            **cls.connection_args,
        )
        with admin.cursor() as cursor:
            cursor.execute(f'DROP DATABASE IF EXISTS "{cls.database}"')
            cursor.execute(f'CREATE DATABASE "{cls.database}"')
        admin.close()

        cls.conn = psycopg.connect(
            dbname=cls.database,
            autocommit=True,
            **cls.connection_args,
        )
        schema = (POSTGRES_SQL_DIR / "01_schema.sql").read_text(encoding="utf-8")
        with cls.conn.cursor() as cursor:
            for statement in schema.split(";"):
                if statement.strip():
                    cursor.execute(statement)

        rows = [
            (1, 101, 201, "pv", beijing_ts(2017, 11, 25, 10)),
            (1, 101, 201, "buy", beijing_ts(2017, 11, 25, 11)),
            (2, 102, 202, "pv", beijing_ts(2017, 11, 25, 12)),
            (3, 103, 203, "pv", beijing_ts(2017, 12, 1, 10)),
            (3, 103, 203, "buy", beijing_ts(2017, 12, 1, 11)),
            (4, 104, 204, "pv", beijing_ts(2017, 12, 2, 10)),
            (4, 104, 204, "buy", beijing_ts(2017, 12, 2, 11)),
            (3, 103, 203, "pv", beijing_ts(2017, 12, 2, 12)),
            (5, 105, 205, "pv", beijing_ts(2017, 12, 3, 13)),
            (6, 106, 206, "pv", beijing_ts(2017, 12, 1, 14)),
            (7, 107, 207, "pv", beijing_ts(2017, 11, 25, 20)),
        ]
        with cls.conn.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO behavior
                    (user_id, item_id, category_id, behavior_type, timestamps)
                VALUES (%s, %s, %s, %s, %s)
                """,
                rows,
            )

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "conn"):
            cls.conn.close()

    def run_query(self, filename):
        sql = (POSTGRES_SQL_DIR / filename).read_text(encoding="utf-8")
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [item.name for item in cursor.description]
            return columns, cursor.fetchall()

    def test_daily_metrics_preserve_business_definition(self):
        columns, rows = self.run_query("02_daily_metrics.sql")
        result = [dict(zip(columns, row)) for row in rows]
        by_day = {row["day"]: row for row in result}

        self.assertEqual(by_day["2017-11-25"]["dau"], 3)
        self.assertEqual(by_day["2017-11-25"]["pv"], 3)
        self.assertEqual(by_day["2017-11-25"]["buy"], 1)
        self.assertEqual(by_day["2017-12-02"]["dau"], 2)

    def test_funnel_counts_distinct_users(self):
        columns, rows = self.run_query("03_funnel.sql")
        result = {row[0]: dict(zip(columns, row)) for row in rows}

        self.assertEqual(result["pv"]["user_count"], 7)
        self.assertEqual(result["buy"]["user_count"], 3)

    def test_user_segment_net_delta(self):
        columns, rows = self.run_query("07_attribution_user_segment.sql")
        result = {row[0]: dict(zip(columns, row)) for row in rows}

        self.assertEqual(result["both_days"]["users_1201"], 1)
        self.assertEqual(result["gained_1202_only"]["users_1202"], 1)
        self.assertEqual(result["lost_1201_only"]["users_1201"], 1)

    def test_view_is_independent_of_session_time_zone(self):
        expected = "2017-11-25"
        for time_zone in ("UTC", "Asia/Shanghai"):
            with self.conn.cursor() as cursor:
                cursor.execute(f"SET TIME ZONE '{time_zone}'")
                cursor.execute(
                    """
                    SELECT event_day
                    FROM behavior_clean
                    WHERE user_id = 7
                    ORDER BY id
                    LIMIT 1
                    """
                )
                self.assertEqual(cursor.fetchone()[0], expected)

        with self.conn.cursor() as cursor:
            cursor.execute("SET TIME ZONE 'UTC'")


if __name__ == "__main__":
    unittest.main()
