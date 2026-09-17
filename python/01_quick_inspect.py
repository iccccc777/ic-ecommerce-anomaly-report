import os

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_FILE = os.path.join(BASE_DIR, "data", "UserBehavior_raw.csv")
COLUMNS = ["user_id", "item_id", "category_id", "behavior_type", "timestamps"]


def main():
    print("数据文件:", RAW_FILE)
    print("文件大小 GB:", round(os.path.getsize(RAW_FILE) / 1024**3, 3))

    print("\n前 5 行原始内容:")
    with open(RAW_FILE, "r", encoding="utf-8", errors="replace") as f:
        for i in range(5):
            print(f"  {i + 1}: {f.readline().strip()}")

    df = pd.read_csv(
        RAW_FILE,
        nrows=200_000,
        header=None,
        names=COLUMNS,
        dtype={
            "user_id": "int64",
            "item_id": "int64",
            "category_id": "int64",
            "behavior_type": "object",
            "timestamps": "int64",
        },
    )
    df["datetime"] = pd.to_datetime(df["timestamps"], unit="s")

    print("\n抽样 20 万行的快速检查:")
    print("总行数:", len(df))
    print("唯一用户数:", df["user_id"].nunique())
    print("唯一商品数:", df["item_id"].nunique())
    print("唯一类目数:", df["category_id"].nunique())
    print("行为类型分布:")
    print(df["behavior_type"].value_counts().to_string())
    print("时间范围:", df["datetime"].min(), "到", df["datetime"].max())


if __name__ == "__main__":
    main()
