import numpy as np
import pandas as pd


WEEKDAY_NAMES = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
ANOMALY_THRESHOLD = 1.5
STRONG_THRESHOLD = 2.0
METRICS = ["dau", "pv", "buy"]


def build_anomaly_table(daily):
    df = daily.copy()
    df["day"] = pd.to_datetime(df["day"])
    df = df.sort_values("day").reset_index(drop=True)
    df["weekday"] = df["day"].dt.weekday.map(lambda value: WEEKDAY_NAMES[value])

    previous = df[["day", *METRICS]].copy()
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
    for metric in METRICS:
        # 只使用判断日之前的 3 天，避免当天异常反向抬高自己的基线。
        df[f"{metric}_ma3"] = (
            df[metric].shift(1).rolling(3, min_periods=1).mean()
        )
        df[f"{metric}_pct_to_ma"] = (
            (df[metric] - df[f"{metric}_ma3"])
            / df[f"{metric}_ma3"]
            * 100
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
    max_absolute_z = df[
        ["dau_zscore", "pv_zscore", "buy_zscore"]
    ].abs().max(axis=1)
    df["anomaly_level"] = np.where(
        max_absolute_z > STRONG_THRESHOLD,
        "strong",
        np.where(df["is_anomaly"], "mild", "normal"),
    )
    return df
