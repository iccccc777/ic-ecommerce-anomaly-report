import argparse
import csv
import os
import sqlite3
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pymysql


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE = BASE_DIR / "data" / "ecommerce.db"
DEFAULT_SQL_DIR = BASE_DIR / "sql" / "mysql"
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs" / "mysql"
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
ANOMALY_THRESHOLD = 1.5
STRONG_THRESHOLD = 2.0


def load_env():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def parse_args():
    load_env()
    parser = argparse.ArgumentParser(
        description="将 SQLite 行为抽样迁移到 MySQL 8 并生成方言结果。"
    )
    parser.add_argument(
        "--sqlite-db",
        default=str(DEFAULT_SQLITE),
        help="SQLite 数据库路径。",
    )
    parser.add_argument(
        "--sql-dir",
        default=str(DEFAULT_SQL_DIR),
        help="MySQL 方言 SQL 目录。",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="MySQL 结果输出目录。",
    )
    parser.add_argument("--mysql-host", default=os.getenv("MYSQL_HOST", "127.0.0.1"))
    parser.add_argument(
        "--mysql-port",
        type=int,
        default=int(os.getenv("MYSQL_PORT", "3306")),
    )
    parser.add_argument("--mysql-user", default=os.getenv("MYSQL_USER", "root"))
    parser.add_argument(
        "--mysql-password",
        default=os.getenv("MYSQL_PASSWORD", ""),
    )
    parser.add_argument(
        "--mysql-database",
        default=os.getenv("MYSQL_DATABASE", "ic_ecommerce"),
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="删除并重建目标数据库。",
    )
    return parser.parse_args()


def mysql_connection(args, database=None):
    return pymysql.connect(
        host=args.mysql_host,
        port=args.mysql_port,
        user=args.mysql_user,
        password=args.mysql_password,
        database=database,
        charset="utf8mb4",
        autocommit=True,
        local_infile=True,
    )


def execute_script(conn, sql_path):
    sql = Path(sql_path).read_text(encoding="utf-8")
    with conn.cursor() as cursor:
        for statement in sql.split(";"):
            statement = statement.strip()
            if statement:
                cursor.execute(statement)


def export_behavior_to_tsv(sqlite_path, tsv_path):
    source = sqlite3.connect(f"file:{Path(sqlite_path).as_posix()}?mode=ro", uri=True)
    count = 0
    try:
        with open(tsv_path, "w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
            cursor = source.execute(
                """
                SELECT user_id, item_id, category_id, behavior_type, timestamps
                FROM behavior
                ORDER BY user_id, timestamps, item_id, behavior_type
                """
            )
            for row in cursor:
                writer.writerow(row)
                count += 1
    finally:
        source.close()
    return count


def load_behavior(conn, tsv_path):
    mysql_path = Path(tsv_path).as_posix()
    with conn.cursor() as cursor:
        cursor.execute(
            """
            LOAD DATA LOCAL INFILE %s
            INTO TABLE behavior
            CHARACTER SET utf8mb4
            FIELDS TERMINATED BY '\t'
            LINES TERMINATED BY '\n'
            (user_id, item_id, category_id, behavior_type, timestamps)
            """,
            (mysql_path,),
        )


def rebuild_dimensions(conn):
    statements = [
        """
        TRUNCATE TABLE dim_user
        """,
        """
        INSERT INTO dim_user (
            user_id, behavior_count, active_days, first_ts, last_ts
        )
        SELECT
            user_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT event_day) AS active_days,
            MIN(timestamps) AS first_ts,
            MAX(timestamps) AS last_ts
        FROM behavior_clean
        GROUP BY user_id
        """,
        """
        TRUNCATE TABLE dim_item
        """,
        """
        INSERT INTO dim_item (item_id, behavior_count, user_count)
        SELECT
            item_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT user_id) AS user_count
        FROM behavior_clean
        GROUP BY item_id
        """,
        """
        TRUNCATE TABLE dim_category
        """,
        """
        INSERT INTO dim_category (category_id, behavior_count, user_count)
        SELECT
            category_id,
            COUNT(*) AS behavior_count,
            COUNT(DISTINCT user_id) AS user_count
        FROM behavior_clean
        GROUP BY category_id
        """,
    ]
    with conn.cursor() as cursor:
        for statement in statements:
            cursor.execute(statement)


def build_anomaly_table(daily):
    df = daily.copy()
    df["day"] = pd.to_datetime(df["day"])
    df = df.sort_values("day").reset_index(drop=True)
    df["weekday"] = df["day"].dt.weekday.map(lambda value: WEEKDAY_NAMES[value])

    previous = df[["day", "dau", "pv", "buy"]].copy()
    previous["day"] = previous["day"] + pd.Timedelta(days=7)
    previous = previous.rename(
        columns={
            "dau": "dau_prev_week",
            "pv": "pv_prev_week",
            "buy": "buy_prev_week",
        }
    )
    df = df.merge(previous, on="day", how="left")

    sample_size = len(df)
    for metric in ["dau", "pv", "buy"]:
        df[f"{metric}_ma3"] = df[metric].rolling(3, min_periods=1).mean()
        df[f"{metric}_pct_to_ma"] = (
            (df[metric] - df[f"{metric}_ma3"]) / df[f"{metric}_ma3"] * 100
        )
        df[f"{metric}_pct_to_prev_week"] = (
            (df[metric] - df[f"{metric}_prev_week"])
            / df[f"{metric}_prev_week"]
            * 100
        )

        total = df[metric].sum()
        total_square = (df[metric] ** 2).sum()
        leave_one_out_mean = (total - df[metric]) / (sample_size - 1)
        leave_one_out_variance = (
            total_square
            - df[metric] ** 2
            - (sample_size - 1) * leave_one_out_mean**2
        ) / (sample_size - 2)
        leave_one_out_std = np.sqrt(leave_one_out_variance.clip(lower=0))
        df[f"{metric}_zscore"] = (
            df[metric] - leave_one_out_mean
        ) / leave_one_out_std
        df[f"{metric}_anomaly"] = (
            df[f"{metric}_zscore"].abs() > ANOMALY_THRESHOLD
        )

    df["is_anomaly"] = (
        df["dau_anomaly"] | df["pv_anomaly"] | df["buy_anomaly"]
    )
    max_absolute_z = df[["dau_zscore", "pv_zscore", "buy_zscore"]].abs().max(axis=1)
    df["anomaly_level"] = np.where(
        max_absolute_z > STRONG_THRESHOLD,
        "strong",
        np.where(df["is_anomaly"], "mild", "normal"),
    )
    return df


def export_query(conn, sql_path, output_path):
    sql = Path(sql_path).read_text(encoding="utf-8")
    with conn.cursor() as cursor:
        cursor.execute(sql)
        columns = [item[0] for item in cursor.description]
        rows = cursor.fetchall()
    frame = pd.DataFrame(rows, columns=columns)
    for column in frame.columns:
        values = frame[column].dropna()
        if not values.empty and values.map(lambda value: isinstance(value, Decimal)).all():
            frame[column] = frame[column].astype(float)
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output_path, index=False, encoding="utf-8-sig")
    return frame


def migrate(args):
    sqlite_path = Path(args.sqlite_db)
    sql_dir = Path(args.sql_dir)
    output_dir = Path(args.output_dir)
    if not sqlite_path.is_file():
        raise FileNotFoundError(f"SQLite 数据库不存在: {sqlite_path}")

    server = mysql_connection(args)
    with server.cursor() as cursor:
        if args.recreate:
            cursor.execute(f"DROP DATABASE IF EXISTS `{args.mysql_database}`")
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{args.mysql_database}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
        )
    server.close()

    conn = mysql_connection(args, args.mysql_database)
    execute_script(conn, sql_dir / "01_schema.sql")

    temp_handle = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".tsv",
        delete=False,
        encoding="utf-8",
    )
    temp_handle.close()
    tsv_path = Path(temp_handle.name)
    try:
        sqlite_count = export_behavior_to_tsv(sqlite_path, tsv_path)
        load_behavior(conn, tsv_path)
        with conn.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM behavior")
            mysql_count = cursor.fetchone()[0]
        if mysql_count != sqlite_count:
            raise RuntimeError(
                f"行为行数不一致: SQLite={sqlite_count}, MySQL={mysql_count}"
            )

        execute_script(conn, sql_dir / "08_indexes.sql")
        rebuild_dimensions(conn)
        output_dir.mkdir(parents=True, exist_ok=True)

        daily = export_query(
            conn,
            sql_dir / "02_daily_metrics.sql",
            output_dir / "daily_metrics.csv",
        )
        export_query(
            conn,
            sql_dir / "03_funnel.sql",
            output_dir / "funnel.csv",
        )
        export_query(
            conn,
            sql_dir / "04_retention.sql",
            output_dir / "retention.csv",
        )
        export_query(
            conn,
            sql_dir / "05_attribution_category.sql",
            output_dir / "attribution_category.csv",
        )
        export_query(
            conn,
            sql_dir / "06_attribution_hour.sql",
            output_dir / "attribution_hour.csv",
        )
        export_query(
            conn,
            sql_dir / "07_attribution_user_segment.sql",
            output_dir / "attribution_user_segment.csv",
        )

        anomaly = build_anomaly_table(daily)
        anomaly.to_csv(
            output_dir / "anomaly_detection.csv",
            index=False,
            encoding="utf-8-sig",
        )
    finally:
        conn.close()
        tsv_path.unlink(missing_ok=True)

    print(f"MySQL 数据库: {args.mysql_database}")
    print(f"行为行数: {sqlite_count:,}")
    print(f"结果目录: {output_dir}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    migrate(parse_args())
