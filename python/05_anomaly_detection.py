import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from anomaly_utils import METRICS, build_anomaly_table


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DAILY_CSV = os.path.join(BASE_DIR, "outputs", "daily_metrics.csv")
OUTPUT_CSV = os.path.join(BASE_DIR, "outputs", "anomaly_detection.csv")
CHART_FILE = os.path.join(BASE_DIR, "outputs", "anomaly_chart.png")


def main():
    daily = pd.read_csv(DAILY_CSV, parse_dates=["day"])
    df = build_anomaly_table(daily)

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
        ax.plot(
            df["day"],
            df[f"{metric}_ma3"],
            label=f"{metric} trailing 3-day MA",
            linestyle="--",
        )
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
