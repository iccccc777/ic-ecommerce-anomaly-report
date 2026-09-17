import json
import os
import urllib.request
from datetime import datetime

import pandas as pd


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "daily_report.md")
LOG_FILE = os.path.join(OUTPUT_DIR, "ai_call_log.json")


def load_env():
    """从项目根目录 .env 读取 API Key，不要求用户把 Key 写进代码。"""
    env_path = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def read_csv(filename):
    return pd.read_csv(os.path.join(OUTPUT_DIR, filename))


def get_api_key():
    load_env()
    return os.getenv("DEEPSEEK_API_KEY") or os.getenv("DASHSCOPE_API_KEY")


def build_prompt():
    daily = read_csv("daily_metrics.csv").tail(3)
    anomaly = read_csv("anomaly_detection.csv")
    anomaly = anomaly[anomaly["is_anomaly"] == True][
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
    ].to_string(index=False)
    category = read_csv("attribution_category.csv").head(5).to_string(index=False)
    hour = read_csv("attribution_hour.csv").head(5).to_string(index=False)
    users = read_csv("attribution_user_segment.csv").to_string(index=False)

    return f"""你是一名电商业务数据分析师。请根据下面的数据写一份中文经营日报初稿。

数据口径：用户级抽样 19,476 个用户 / 196.7 万行行为记录；DAU 是当天活跃用户数；购买是 buy 事件数。
时间说明：12 月 2 日是周六，已与 11 月 25 日周六对比；12 月 3 日是周日，已与 11 月 26 日周日对比。
用户归因是 DAU 净增量拆解（新增活跃用户 - 流失活跃用户），不是简单占比，不要写成“新用户贡献”。

要求：
1. 先写核心指标概览。
2. 再写异动定位，说明同星期基线、类目、时段、用户类型各说明了什么。
3. 最后给 3 条可执行的业务建议。
4. 不要编造数据中没有的信息；没有证据时写成假设或局限。

近期核心指标：
{daily.to_string(index=False)}

异常检测结果：
{anomaly}

类目购买增量归因 Top 5：
{category}

时段购买增量归因 Top 5：
{hour}

用户 DAU 增量拆解：
{users}
"""


def build_template_report():
    daily = read_csv("daily_metrics.csv")
    anomaly = read_csv("anomaly_detection.csv")
    anomaly_days = anomaly[anomaly["is_anomaly"] == True]
    category = read_csv("attribution_category.csv").head(5)
    hour = read_csv("attribution_hour.csv").head(5)
    users = read_csv("attribution_user_segment.csv")

    last_day = daily.iloc[-1]
    top_cat = category.iloc[0]
    top_hour = hour.iloc[0]
    segment_names = {
        "both_days": "12月1日和2日都活跃",
        "gained_1202_only": "仅12月2日新增活跃",
        "lost_1201_only": "仅12月1日活跃（12月2日流失）",
    }
    user_text = "；".join(
        f"{segment_names.get(row['segment'], row['segment'])} "
        f"{int(row['users_1202'])}人/净增量{int(row['delta_contribution']):+d}"
        for _, row in users.iterrows()
    )
    anomaly_text = "、".join(
        f"{row['day']}（{row['weekday']}，{row['anomaly_level']}）"
        for _, row in anomaly_days.iterrows()
    )

    return f"""# 电商经营日报初稿

## 一、核心指标

截至 {last_day['day']}，DAU 为 {int(last_day['dau'])}，PV 为 {int(last_day['pv'])}，购买行为为 {int(last_day['buy'])}，购买/浏览转化率为 {last_day['buy_to_pv']:.4f}。

## 二、异动定位

异常检测标记 {anomaly_text} 为异动日。

12 月 2 日 DAU 相对前 3 日移动平均上升约 {anomaly_days.iloc[0]['dau_pct_to_ma']:.2f}%，相对 11 月 25 日周六上升约 {anomaly_days.iloc[0]['dau_pct_to_prev_week']:.2f}%，说明不是单纯的周末效应。

归因结果显示：

- 类目：购买增量贡献最大的是类目 {int(top_cat['category_id'])}，贡献度约 {top_cat['contribution']:.2%}。
- 时段：购买增量主要集中在 {int(top_hour['hour'])} 点前后。
- 用户：{user_text}。

## 三、业务建议

1. 对购买增量贡献最大的类目复盘商品供给、价格和活动节奏。
2. 在购买增量集中的时段优化推荐位、Push 时间和活动排期。
3. 新增活跃用户多于流失用户，可以进一步分析新增用户的行为路径，而不是直接归因于拉新渠道。

## 四、局限

- 用户级抽样约 2% 用户，指标不能直接外推全量。
- 数据集只有 9 天，留存和新老用户口径受窗口左截断影响。
- 当前异常和归因是相关性分析，不能证明因果关系。
- 本报告为初稿，需人工校准数据和结论后再使用。
"""


def call_llm(prompt):
    api_key = get_api_key()
    if os.getenv("DEEPSEEK_API_KEY"):
        url = "https://api.deepseek.com/chat/completions"
        model = "deepseek-chat"
    else:
        url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        model = "qwen-plus"

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"], model


def save_call_log(prompt, content, model, source):
    log = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "model": model,
        "source": source,
        "prompt": prompt,
        "content": content,
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def main():
    load_env()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    prompt = build_prompt()
    api_key = get_api_key()

    if api_key:
        try:
            content, model = call_llm(prompt)
            source = "LLM API"
        except Exception as e:
            print("LLM 调用失败，已使用本地模板:", e)
            content = build_template_report()
            model = "local-template"
            source = "local template"
    else:
        print("未检测到 API Key，已使用本地模板日报。")
        content = build_template_report()
        model = "local-template"
        source = "local template"

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    save_call_log(prompt, content, model, source)

    print("日报已保存:", OUTPUT_FILE)
    print("来源:", source)
    print()
    print(content)


if __name__ == "__main__":
    main()
