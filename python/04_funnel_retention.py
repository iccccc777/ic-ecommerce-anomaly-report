import os
import sqlite3

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "ecommerce.db")
SQL_DIR = os.path.join(BASE_DIR, "sql")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def run_sql(sql_path):
    with open(sql_path, "r", encoding="utf-8") as f:
        query = f.read()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def main():
    funnel = run_sql(os.path.join(SQL_DIR, "03_funnel.sql"))
    pv_users = funnel.loc[funnel["behavior_type"] == "pv", "user_count"].iloc[0]
    funnel["user_to_pv"] = (funnel["user_count"] / pv_users).round(6)
    funnel_path = os.path.join(OUTPUT_DIR, "funnel.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    funnel.to_csv(funnel_path, index=False, encoding="utf-8-sig")

    print("整体漏斗:")
    print(
        funnel[
            ["behavior_type", "event_count", "user_count", "user_to_pv"]
        ].to_string(index=False)
    )
    print("\n已保存:", funnel_path)

    retention = run_sql(os.path.join(SQL_DIR, "04_retention.sql"))
    retention_path = os.path.join(OUTPUT_DIR, "retention.csv")
    retention.to_csv(retention_path, index=False, encoding="utf-8-sig")

    print("\n留存结果（前 20 行）:")
    print(retention.head(20).to_string(index=False))
    print("\n已保存:", retention_path)

    pivot = retention.pivot_table(
        index="first_day",
        columns="day_diff",
        values="retention_rate",
        aggfunc="first",
    )
    pivot = pivot.round(4)
    print("\n留存率透视表:")
    print(pivot.to_string())


if __name__ == "__main__":
    main()
