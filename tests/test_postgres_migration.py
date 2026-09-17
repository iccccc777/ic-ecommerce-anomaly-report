import unittest
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


if __name__ == "__main__":
    unittest.main()
