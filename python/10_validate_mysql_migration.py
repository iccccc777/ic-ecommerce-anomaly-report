import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_OUTPUTS = BASE_DIR / "outputs"
DEFAULT_MYSQL_OUTPUTS = BASE_DIR / "outputs" / "mysql"


def parse_args():
    parser = argparse.ArgumentParser(
        description="对比 SQLite 基线与 MySQL 迁移结果。"
    )
    parser.add_argument(
        "--sqlite-dir",
        default=str(DEFAULT_SQLITE_OUTPUTS),
        help="SQLite 结果目录。",
    )
    parser.add_argument(
        "--mysql-dir",
        default=str(DEFAULT_MYSQL_OUTPUTS),
        help="MySQL 迁移结果目录。",
    )
    return parser.parse_args()


def read_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


def compare_file(
    sqlite_dir,
    mysql_dir,
    filename,
    sort_by,
    numeric_columns,
):
    sqlite = read_csv(Path(sqlite_dir) / filename)
    mysql = read_csv(Path(mysql_dir) / filename)

    if list(sqlite.columns) != list(mysql.columns):
        raise AssertionError(
            f"{filename} 列不一致: "
            f"SQLite={list(sqlite.columns)}, MySQL={list(mysql.columns)}"
        )

    for column in numeric_columns:
        if column in sqlite.columns:
            sqlite[column] = pd.to_numeric(sqlite[column])
        if column in mysql.columns:
            mysql[column] = pd.to_numeric(mysql[column])

    sqlite = sqlite.sort_values(sort_by).reset_index(drop=True)
    mysql = mysql.sort_values(sort_by).reset_index(drop=True)
    pd.testing.assert_frame_equal(
        sqlite,
        mysql,
        check_dtype=False,
        rtol=1e-5,
        atol=1e-6,
    )
    print(f"PASS {filename}: {len(mysql):,} rows")


def main():
    args = parse_args()
    checks = [
        (
            "daily_metrics.csv",
            ["day"],
            ["dau", "pv", "fav", "cart", "buy", "buy_to_pv", "buy_per_dau"],
        ),
        (
            "anomaly_detection.csv",
            ["day"],
            [
                "dau",
                "pv",
                "buy",
                "dau_prev_week",
                "pv_prev_week",
                "buy_prev_week",
                "dau_ma3",
                "dau_pct_to_ma",
                "dau_pct_to_prev_week",
                "dau_zscore",
                "pv_ma3",
                "pv_pct_to_ma",
                "pv_pct_to_prev_week",
                "pv_zscore",
                "buy_ma3",
                "buy_pct_to_ma",
                "buy_pct_to_prev_week",
                "buy_zscore",
            ],
        ),
        (
            "funnel.csv",
            ["behavior_type"],
            ["event_count", "user_count", "user_to_pv"],
        ),
        (
            "retention.csv",
            ["first_day", "day_diff"],
            ["cohort_size", "retained_users", "retention_rate"],
        ),
        (
            "attribution_category.csv",
            ["category_id"],
            ["buy_1201", "buy_1202", "buy_delta", "contribution"],
        ),
        (
            "attribution_hour.csv",
            ["hour"],
            ["buy_1201", "buy_1202", "buy_delta", "contribution"],
        ),
        (
            "attribution_user_segment.csv",
            ["segment"],
            ["users_1201", "users_1202", "delta_contribution", "share_1202"],
        ),
    ]

    for filename, sort_by, numeric_columns in checks:
        compare_file(
            args.sqlite_dir,
            args.mysql_dir,
            filename,
            sort_by,
            numeric_columns,
        )

    print("MySQL migration validation passed.")


if __name__ == "__main__":
    main()
