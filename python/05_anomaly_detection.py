import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_CSV = os.path.join(BASE_DIR, "outputs", "daily_metrics.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "outputs", "anomaly_detection.csv")
CHART_FILE = os.path.join(BASE_DIR, "outputs", "anomaly_chart.png")
METRICS = ["dau", "pv", "buy"]
WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
ANOMALY_THRESHOLD = 1.5
STRONG_THRESHOLD = 2.0


def main():
    df = pd.read_csv(DAILY_CSV, parse_dates=["day"])
    df = df.sort_values("day").reset_index(drop=True)
    df["weekday"] = df["day"].dt.weekday.map(lambda x: WEEKDAY_NAMES[x])

    # 同星期基线：用 7 天前的同星期值做对比，尽量排除周末效应。
    prev = df[["day", "dau", "pv", "buy"]].copy()
    prev["day"] = prev["day"] + pd.Timedelta(days=7)
    prev = prev.rename(
        columns={
            "dau": "dau_prev_week",
            "pv": "pv_prev_week",
            "buy": "buy_prev_week",
        }
    )
    df = df.merge(prev, on="day", how="left")

    n = len(df)
    for metric in METRICS:
        df[f"{metric}_ma3"] = df[metric].rolling(3, min_periods=1).mean()
        df[f"{metric}_pct_to_ma"] = (
            (df[metric] - df[f"{metric}_ma3"]) / df[f"{metric}_ma3"] * 100
        )
        df[f"{metric}_pct_to_prev_week"] = (
            (df[metric] - df[f"{metric}_prev_week"])
            / df[f"{metric}_prev_week"]
            * 100
        )

        # 留一法 Z-Score：被判断的当天不参与自己的均值/标准差计算。
        total = df[metric].sum()
        total_sq = (df[metric] ** 2).sum()
        mean_loo = (total - df[metric]) / (n - 1)
        var_loo = (total_sq - df[metric] ** 2 - (n - 1) * mean_loo**2) / (n - 2)
        std_loo = np.sqrt(var_loo.clip(lower=0))
        df[f"{metric}_zscore"] = (df[metric] - mean_loo) / std_loo
        df[f"{metric}_anomaly"] = df[f"{metric}_zscore"].abs() > ANOMALY_THRESHOLD

    df["is_anomaly"] = (
        df["dau_anomaly"] | df["pv_anomaly"] | df["buy_anomaly"]
    )
    max_abs_z = df[
        ["dau_zscore", "pv_zscore", "buy_zscore"]
    ].abs().max(axis=1)
    df["anomaly_level"] = np.where(
        max_abs_z > STRONG_THRESHOLD,
        "strong",
        np.where(df["is_anomaly"], "mild", "normal"),
    )

    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)
    df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("异常检测结果:")
    print(
        df[
            [
                "day",
                "weekday",
                "dau",
                "dau_ma3",
                "dau_pct_to_ma",
                "dau_pct_to_prev_week",
                "dau_zscore",
                "buy",
                "buy_ma3",
                "buy_pct_to_ma",
                "buy_pct_to_prev_week",
                "buy_zscore",
                "is_anomaly",
                "anomaly_level",
            ]
        ].to_string(index=False, formatters={"day": lambda x: x.date().isoformat()})
    )
    print("\n已保存:", OUTPUT_CSV)

    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False

    fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=True)
    for ax, metric, title in zip(axes, METRICS, ["DAU", "PV", "购买行为"]):
        ax.plot(df["day"], df[metric], label=metric, marker="o")
        ax.plot(df["day"], df[f"{metric}_ma3"], label=f"{metric} 3-day MA", linestyle="--")
        anomaly = df[df[f"{metric}_anomaly"]]
        ax.scatter(
            anomaly["day"],
            anomaly[metric],
            color="red",
            zorder=5,
            label="anomaly",
        )
        ax.set_title(title)
        ax.legend()
        ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(CHART_FILE, dpi=150)
    print("图表已保存:", CHART_FILE)


if __name__ == "__main__":
    main()
