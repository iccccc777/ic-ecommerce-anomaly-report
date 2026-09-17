import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MYSQL_SQL_DIR = ROOT / "sql" / "mysql"
MIGRATION_SCRIPT = ROOT / "python" / "09_migrate_to_mysql.py"
REQUIRED_SQL_FILES = [
    "01_schema.sql",
    "02_daily_metrics.sql",
    "03_funnel.sql",
    "04_retention.sql",
    "05_attribution_category.sql",
    "06_attribution_hour.sql",
    "07_attribution_user_segment.sql",
    "08_indexes.sql",
]
BEIJING = timezone(timedelta(hours=8))


def beijing_ts(year, month, day, hour):
    return int(datetime(year, month, day, hour, tzinfo=BEIJING).timestamp())


class MySQLMigrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        port = os.getenv("MYSQL_TEST_PORT")
        if not port:
            raise unittest.SkipTest("MYSQL_TEST_PORT is not configured")

        import pymysql

        cls.pymysql = pymysql
        cls.db_name = os.getenv("MYSQL_TEST_DATABASE", "ic_ecommerce_test")
        cls.connection_args = {
            "host": os.getenv("MYSQL_TEST_HOST", "127.0.0.1"),
            "port": int(port),
            "user": os.getenv("MYSQL_TEST_USER", "root"),
            "password": os.getenv("MYSQL_TEST_PASSWORD", ""),
            "charset": "utf8mb4",
            "autocommit": True,
            "local_infile": True,
        }

        server = pymysql.connect(**cls.connection_args)
        with server.cursor() as cursor:
            cursor.execute("SET GLOBAL local_infile = 1")
            cursor.execute(f"DROP DATABASE IF EXISTS `{cls.db_name}`")
            cursor.execute(
                f"CREATE DATABASE `{cls.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
            )
        server.close()

        cls.conn = pymysql.connect(database=cls.db_name, **cls.connection_args)
        schema = (MYSQL_SQL_DIR / "01_schema.sql").read_text(encoding="utf-8")
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
        sql = (MYSQL_SQL_DIR / filename).read_text(encoding="utf-8")
        with self.conn.cursor() as cursor:
            cursor.execute(sql)
            columns = [item[0] for item in cursor.description]
            return columns, cursor.fetchall()

    def test_dialect_files_exist(self):
        for filename in REQUIRED_SQL_FILES:
            self.assertTrue(
                (MYSQL_SQL_DIR / filename).is_file(),
                f"missing MySQL SQL file: {filename}",
            )

    def test_daily_metrics_preserve_business_definition(self):
        columns, rows = self.run_query("02_daily_metrics.sql")
        result = [dict(zip(columns, row)) for row in rows]
        by_day = {row["day"]: row for row in result}

        self.assertEqual(by_day["2017-11-25"]["dau"], 3)
        self.assertEqual(by_day["2017-11-25"]["pv"], 3)
        self.assertEqual(by_day["2017-11-25"]["buy"], 1)
        self.assertEqual(by_day["2017-12-02"]["dau"], 2)
        self.assertEqual(by_day["2017-12-02"]["buy"], 1)

    def test_funnel_counts_distinct_users(self):
        columns, rows = self.run_query("03_funnel.sql")
        result = {row[0]: dict(zip(columns, row)) for row in rows}

        self.assertEqual(result["pv"]["user_count"], 7)
        self.assertEqual(result["buy"]["user_count"], 3)

    def test_view_is_independent_of_session_time_zone(self):
        for time_zone in ("+00:00", "+08:00", "-05:00"):
            with self.conn.cursor() as cursor:
                cursor.execute(f"SET time_zone = '{time_zone}'")
                cursor.execute(
                    """
                    SELECT event_day
                    FROM behavior_clean
                    WHERE user_id = 7
                    ORDER BY id
                    LIMIT 1
                    """
                )
                self.assertEqual(cursor.fetchone()[0], "2017-11-25")

        with self.conn.cursor() as cursor:
            cursor.execute("SET time_zone = '+00:00'")

    def test_user_segment_net_delta(self):
        columns, rows = self.run_query("07_attribution_user_segment.sql")
        result = {row[0]: dict(zip(columns, row)) for row in rows}

        self.assertEqual(result["both_days"]["users_1201"], 1)
        self.assertEqual(result["both_days"]["users_1202"], 1)
        self.assertEqual(result["gained_1202_only"]["users_1202"], 1)
        self.assertEqual(result["lost_1201_only"]["users_1201"], 1)

    def test_migration_script_copies_sqlite_rows_and_exports_reports(self):
        self.assertTrue(MIGRATION_SCRIPT.is_file(), "migration script is missing")

        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            sqlite_path = temp / "fixture.db"
            output_dir = temp / "outputs"
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.execute(
                """
                CREATE TABLE behavior (
                    user_id INTEGER,
                    item_id INTEGER,
                    category_id INTEGER,
                    behavior_type TEXT,
                    timestamps INTEGER
                )
                """
            )
            sqlite_conn.executemany(
                "INSERT INTO behavior VALUES (?, ?, ?, ?, ?)",
                [
                    (1, 101, 201, "pv", beijing_ts(2017, 11, 25, 10)),
                    (1, 101, 201, "buy", beijing_ts(2017, 11, 25, 11)),
                    (2, 102, 202, "pv", beijing_ts(2017, 11, 25, 12)),
                    (3, 103, 203, "pv", beijing_ts(2017, 12, 1, 10)),
                    (3, 103, 203, "buy", beijing_ts(2017, 12, 1, 11)),
                    (4, 104, 204, "pv", beijing_ts(2017, 12, 2, 10)),
                    (4, 104, 204, "buy", beijing_ts(2017, 12, 2, 11)),
                    (3, 103, 203, "pv", beijing_ts(2017, 12, 2, 12)),
                    (5, 105, 205, "pv", beijing_ts(2017, 12, 3, 13)),
                ],
            )
            sqlite_conn.commit()
            sqlite_conn.close()

            env = os.environ.copy()
            env["MYSQL_TEST_PORT"] = os.environ["MYSQL_TEST_PORT"]
            result = subprocess.run(
                [
                    sys.executable,
                    str(MIGRATION_SCRIPT),
                    "--sqlite-db",
                    str(sqlite_path),
                    "--mysql-host",
                    os.getenv("MYSQL_TEST_HOST", "127.0.0.1"),
                    "--mysql-port",
                    os.environ["MYSQL_TEST_PORT"],
                    "--mysql-user",
                    os.getenv("MYSQL_TEST_USER", "root"),
                    "--mysql-password",
                    os.getenv("MYSQL_TEST_PASSWORD", ""),
                    "--mysql-database",
                    "ic_ecommerce_migration_test",
                    "--recreate",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            conn = self.pymysql.connect(
                database="ic_ecommerce_migration_test",
                **self.connection_args,
            )
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM behavior")
                self.assertEqual(cursor.fetchone()[0], 9)
                cursor.execute("SELECT COUNT(*) FROM dim_user")
                self.assertEqual(cursor.fetchone()[0], 5)
            conn.close()

            expected_files = {
                "daily_metrics.csv",
                "anomaly_detection.csv",
                "funnel.csv",
                "retention.csv",
                "attribution_category.csv",
                "attribution_hour.csv",
                "attribution_user_segment.csv",
            }
            actual_files = {path.name for path in output_dir.glob("*.csv")}
            self.assertEqual(actual_files, expected_files)


if __name__ == "__main__":
    unittest.main()
