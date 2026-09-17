import os

import pandas as pd
import streamlit as st


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


@st.cache_data
def load_csv(name):
    return pd.read_csv(os.path.join(OUTPUT_DIR, name))


def load_report():
    calibrated = os.path.join(OUTPUT_DIR, "daily_report_calibrated.md")
    path = (
        calibrated
        if os.path.exists(calibrated)
        else os.path.join(OUTPUT_DIR, "daily_report.md")
    )
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    st.set_page_config(page_title="电商经营异动归因与智能日报", layout="wide")
    st.title("电商经营异动归因与智能日报")

    daily = load_csv("daily_metrics.csv")
    daily["day"] = pd.to_datetime(daily["day"])
    daily = daily.sort_values("day")

    anomaly = load_csv("anomaly_detection.csv")
    funnel = load_csv("funnel.csv")
    retention = load_csv("retention.csv")
    category = load_csv("attribution_category.csv")
    hour = load_csv("attribution_hour.csv")
    users = load_csv("attribution_user_segment.csv")
    report = load_report()

    latest = daily.iloc[-1]
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("DAU", f"{int(latest['dau']):,}")
    c2.metric("PV", f"{int(latest['pv']):,}")
    c3.metric("购买行为", f"{int(latest['buy']):,}")
    c4.metric("购买/浏览转化率", f"{latest['buy_to_pv']:.2%}")

    st.subheader("核心指标趋势")
    trend_left, trend_right = st.columns(2)
    with trend_left:
        st.markdown("**DAU 趋势**")
        st.caption("横轴：日期；纵轴：活跃用户数")
        st.line_chart(daily.set_index("day")[["dau"]])
    with trend_right:
        st.markdown("**购买行为趋势**")
        st.caption("横轴：日期；纵轴：购买行为次数")
        st.line_chart(daily.set_index("day")[["buy"]])

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("购买漏斗")
        show = funnel[["behavior_type", "event_count", "user_count", "user_to_pv"]].copy()
        show["user_to_pv"] = (show["user_to_pv"] * 100).round(2).astype(str) + "%"
        st.dataframe(show, use_container_width=True)

    with col2:
        st.subheader("留存率")
        pivot = retention.pivot_table(
            index="first_day",
            columns="day_diff",
            values="retention_rate",
            aggfunc="first",
        ).round(4)
        st.dataframe(pivot, use_container_width=True)

    st.subheader("异常检测")
    st.image(os.path.join(OUTPUT_DIR, "anomaly_chart.png"), use_container_width=True)
    anomaly_show = anomaly[
        [
            "day",
            "weekday",
            "dau",
            "dau_pct_to_ma",
            "dau_pct_to_prev_week",
            "dau_zscore",
            "buy",
            "buy_pct_to_ma",
            "buy_pct_to_prev_week",
            "buy_zscore",
            "anomaly_level",
        ]
    ]
    st.dataframe(anomaly_show, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("类目购买增量归因 Top 10")
        st.dataframe(category.head(10), use_container_width=True)
    with col4:
        st.subheader("时段购买增量归因 Top 10")
        st.dataframe(hour.head(10), use_container_width=True)

    st.subheader("用户 DAU 增量拆解")
    st.dataframe(users, use_container_width=True)

    with st.expander("AI 日报（人工校准版）"):
        st.markdown(report)


if __name__ == "__main__":
    main()
