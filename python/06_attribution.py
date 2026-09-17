import os
import sqlite3

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_FILE = os.path.join(BASE_DIR, "data", "ecommerce.db")
SQL_DIR = os.path.join(BASE_DIR, "sql")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def read_sql(filename):
    with open(os.path.join(SQL_DIR, filename), "r", encoding="utf-8") as f:
        query = f.read()
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def category_attribution():
    df = read_sql("05_attribution_category.sql")
    pivot = df.pivot_table(
        index="category_id",
        columns="day",
        values="buy_events",
        aggfunc="sum",
    ).reset_index()
    pivot.columns = ["category_id", "buy_1201", "buy_1202"]
    pivot = pivot.fillna(0)
    pivot["buy_delta"] = pivot["buy_1202"] - pivot["buy_1201"]
    total_delta = pivot["buy_delta"].sum()
    pivot["contribution"] = pivot["buy_delta"] / total_delta
    pivot = pivot.sort_values("contribution", ascending=False).reset_index(drop=True)

    path = os.path.join(OUTPUT_DIR, "attribution_category.csv")
    pivot.to_csv(path, index=False, encoding="utf-8-sig")
    print("类目归因（购买增量）: 总购买增量", int(total_delta))
    print(pivot.head(10).to_string(index=False))
    print("已保存:", path)


def hour_attribution():
    df = read_sql("06_attribution_hour.sql")
    pivot = df.pivot_table(
        index="hour",
        columns="day",
        values="buy_events",
        aggfunc="sum",
    ).reset_index()
    pivot.columns = ["hour", "buy_1201", "buy_1202"]
    pivot = pivot.fillna(0)
    pivot["buy_delta"] = pivot["buy_1202"] - pivot["buy_1201"]
    total_delta = pivot["buy_delta"].sum()
    pivot["contribution"] = pivot["buy_delta"] / total_delta
    pivot = pivot.sort_values("contribution", ascending=False).reset_index(drop=True)

    path = os.path.join(OUTPUT_DIR, "attribution_hour.csv")
    pivot.to_csv(path, index=False, encoding="utf-8-sig")
    print("\n时段归因（购买增量）: 总购买增量", int(total_delta))
    print(pivot.head(10).to_string(index=False))
    print("已保存:", path)


def user_segment_attribution():
    df = read_sql("07_attribution_user_segment.sql")
    counts = dict(zip(df["segment"], df["users"]))
    both = int(counts.get("both_days", 0))
    gained = int(counts.get("gained_1202_only", 0))
    lost = int(counts.get("lost_1201_only", 0))
    dau_1201 = both + lost
    dau_1202 = both + gained

    rows = [
        {
            "segment": "both_days",
            "users_1201": both,
            "users_1202": both,
            "delta_contribution": 0,
            "share_1202": both / dau_1202 if dau_1202 else 0,
        },
        {
            "segment": "gained_1202_only",
            "users_1201": 0,
            "users_1202": gained,
            "delta_contribution": gained,
            "share_1202": gained / dau_1202 if dau_1202 else 0,
        },
        {
            "segment": "lost_1201_only",
            "users_1201": lost,
            "users_1202": 0,
            "delta_contribution": -lost,
            "share_1202": 0,
        },
    ]
    out = pd.DataFrame(rows)

    path = os.path.join(OUTPUT_DIR, "attribution_user_segment.csv")
    out.to_csv(path, index=False, encoding="utf-8-sig")
    print("\n用户 DAU 增量拆解:")
    print(out.to_string(index=False))
    print("12 月 1 日 DAU:", dau_1201)
    print("12 月 2 日 DAU:", dau_1202)
    print("净增量:", int(out["delta_contribution"].sum()))
    print("已保存:", path)


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    category_attribution()
    hour_attribution()
    user_segment_attribution()


if __name__ == "__main__":
    main()
