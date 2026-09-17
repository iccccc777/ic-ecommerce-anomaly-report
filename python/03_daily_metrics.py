import os
import sqlite3

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "ecommerce.db")
SQL_FILE = os.path.join(BASE_DIR, "sql", "02_daily_metrics.sql")
OUTPUT_FILE = os.path.join(BASE_DIR, "outputs", "daily_metrics.csv")


def main():
    with open(SQL_FILE, "r", encoding="utf-8") as f:
        query = f.read()

    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")

    print("指标结果:")
    print(df.to_string(index=False))
    print("\n已保存:", OUTPUT_FILE)


if __name__ == "__main__":
    main()
