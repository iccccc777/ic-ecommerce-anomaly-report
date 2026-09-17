import csv
import os
import sqlite3
import zlib


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "UserBehavior_raw.csv")
SAMPLE_FILE = os.path.join(BASE_DIR, "data", "UserBehavior_sample.csv")
DB_FILE = os.path.join(BASE_DIR, "data", "ecommerce.db")
SAMPLE_RATE = 0.02
USER_HASH_DIVISOR = 10000
USER_HASH_KEEP = int(SAMPLE_RATE * USER_HASH_DIVISOR)


def keep_user(user_id):
    # 按 user_id 的稳定哈希做用户级抽样，保证同一份原始数据可复现。
    digest = zlib.crc32(str(user_id).encode("utf-8"))
    return digest % USER_HASH_DIVISOR < USER_HASH_KEEP


def create_schema(conn):
    conn.executescript(
        """
        DROP VIEW IF EXISTS behavior_clean;
        DROP TABLE IF EXISTS dim_user;
        DROP TABLE IF EXISTS dim_item;
        DROP TABLE IF EXISTS dim_category;
        DROP TABLE IF EXISTS behavior;
        CREATE TABLE behavior (
            user_id INTEGER,
            item_id INTEGER,
            category_id INTEGER,
            behavior_type TEXT,
            timestamps INTEGER
        );
        """
    )


def build_sample_and_db():
    os.makedirs(os.path.dirname(SAMPLE_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    create_schema(conn)

    batch = []
    sample_count = 0
    malformed = 0
    raw_count = 0
    sampled_users = set()

    with open(RAW_FILE, "r", encoding="utf-8", errors="replace", newline="") as fin:
        with open(SAMPLE_FILE, "w", encoding="utf-8", newline="") as fout:
            writer = csv.writer(fout)

            for line_no, line in enumerate(fin, start=1):
                raw_count += 1

                row = line.rstrip("\n").split(",")
                if len(row) != 5:
                    malformed += 1
                    continue

                try:
                    user_id = int(row[0])
                    item_id = int(row[1])
                    category_id = int(row[2])
                    behavior_type = row[3]
                    timestamps = int(row[4])
                except ValueError:
                    malformed += 1
                    continue

                if not keep_user(user_id):
                    continue

                writer.writerow(row)
                batch.append(
                    (
                        user_id,
                        item_id,
                        category_id,
                        behavior_type,
                        timestamps,
                    )
                )
                sample_count += 1
                sampled_users.add(user_id)

                if len(batch) >= 10_000:
                    conn.executemany(
                        "INSERT INTO behavior VALUES (?, ?, ?, ?, ?)",
                        batch,
                    )
                    batch.clear()

                if line_no % 10_000_000 == 0:
                    print(f"已扫描 {line_no:,} 行，已抽样 {sample_count:,} 行")

    if batch:
        conn.executemany("INSERT INTO behavior VALUES (?, ?, ?, ?, ?)", batch)

    conn.executescript(
        """
        CREATE INDEX idx_behavior_user ON behavior(user_id, timestamps);
        CREATE INDEX idx_behavior_cat ON behavior(category_id, timestamps);
        CREATE INDEX idx_behavior_time ON behavior(timestamps);

        CREATE VIEW behavior_clean AS
        SELECT *
        FROM behavior
        WHERE date(timestamps, 'unixepoch', '+8 hours')
              BETWEEN '2017-11-25' AND '2017-12-03';

        CREATE TABLE dim_user AS
        SELECT
            user_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT date(timestamps, 'unixepoch', '+8 hours')) AS active_days,
            MIN(timestamps) AS first_ts,
            MAX(timestamps) AS last_ts
        FROM behavior_clean
        GROUP BY user_id;

        CREATE TABLE dim_item AS
        SELECT
            item_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT user_id) AS user_count
        FROM behavior_clean
        GROUP BY item_id;

        CREATE TABLE dim_category AS
        SELECT
            category_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT user_id) AS user_count
        FROM behavior_clean
        GROUP BY category_id;
        """
    )

    print("\n抽样文件:", SAMPLE_FILE)
    print("数据库文件:", DB_FILE)
    print("原始行数:", raw_count)
    print("抽样行数:", sample_count)
    print("抽样用户数:", len(sampled_users))
    print("异常行数:", malformed)

    print("\n行为类型分布:")
    for row in conn.execute(
        "SELECT behavior_type, COUNT(*) FROM behavior GROUP BY behavior_type ORDER BY COUNT(*) DESC"
    ):
        print(f"  {row[0]}: {row[1]:,}")

    print("唯一用户数:", conn.execute("SELECT COUNT(DISTINCT user_id) FROM behavior").fetchone()[0])
    print("唯一商品数:", conn.execute("SELECT COUNT(DISTINCT item_id) FROM behavior").fetchone()[0])
    print("唯一类目数:", conn.execute("SELECT COUNT(DISTINCT category_id) FROM behavior").fetchone()[0])

    conn.close()


if __name__ == "__main__":
    build_sample_and_db()
