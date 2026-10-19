from __future__ import annotations

from dataclasses import dataclass
from io import StringIO

import pandas as pd
import plotly.express as px
import streamlit as st


try:
    import scrapling  # noqa: F401

    SCRAPLING_AVAILABLE = True
except Exception:
    SCRAPLING_AVAILABLE = False


@dataclass(frozen=True)
class Challenge:
    name: str
    signal: str
    required: set[str]
    safe_action: str


CHALLENGES = [
    Challenge("请求身份缺失", "403 或服务端拒绝非标准客户端", {"headers"}, "核对授权范围并补充可识别的客户端标识"),
    Challenge("访问频率超限", "429 Too Many Requests", {"delay"}, "降低频率并遵守约定的速率上限"),
    Challenge("会话状态缺失", "401 或业务状态不完整", {"session"}, "使用企业提供的测试账号和会话流程"),
    Challenge("页面动态渲染", "首屏 HTML 不包含授权字段", {"browser"}, "在资源预算内使用浏览器渲染"),
    Challenge("分页状态依赖", "翻页后重复或遗漏", {"token", "session"}, "维护合法分页状态并校验去重"),
    Challenge("出口频率受限", "出口地址被临时限制", {"delay"}, "暂停任务并与数据提供方确认访问窗口"),
]

STRATEGIES = {
    "基础 HTTP 请求": {"features": set(), "cost": 1, "latency": 0.4},
    "可识别请求头": {"features": {"headers"}, "cost": 1, "latency": 0.5},
    "会话保持请求": {"features": {"headers", "session"}, "cost": 2, "latency": 0.7},
    "限速会话采集": {"features": {"headers", "session", "delay", "token"}, "cost": 3, "latency": 1.4},
    "授权浏览器采集": {"features": {"headers", "session", "delay", "browser", "token"}, "cost": 5, "latency": 3.8},
    "工程化采集任务": {"features": {"headers", "session", "delay", "browser", "token"}, "cost": 6, "latency": 3.2},
}

SCENARIOS = {
    "企业自有网站数据同步": "企业书面授权，目标是稳定同步自有公开业务字段。",
    "合作平台授权数据核验": "合作方提供测试账号、字段清单和访问频率上限。",
    "公开信息低频采集评估": "只评估合法公开字段，并先核对条款、robots和个人信息边界。",
}


def evaluate(challenge: Challenge, strategy: str, round_no: int) -> dict[str, object]:
    spec = STRATEGIES[strategy]
    missing = challenge.required - spec["features"]
    success = not missing
    latency = float(spec["latency"]) + (round_no - 1) * 0.05
    return {
        "轮次": round_no,
        "运行信号": challenge.name,
        "诊断依据": challenge.signal,
        "策略": strategy,
        "结果": "通过" if success else "未通过",
        "缺失能力": "、".join(sorted(missing)) if missing else "无",
        "估计耗时秒": round(latency, 2),
        "资源成本级": spec["cost"],
        "合规处置建议": "按任务单继续" if success else challenge.safe_action,
    }


def build_report(task_id: str, scenario: str, strategy: str, compliant: bool, df: pd.DataFrame) -> str:
    output = StringIO()
    output.write(f"# 网络采集策略评审报告 {task_id}\n\n")
    output.write(f"- 业务场景：{scenario}\n- 候选策略：{strategy}\n")
    output.write(f"- 合规前置检查：{'通过' if compliant else '未通过，禁止执行'}\n")
    output.write(f"- 技术关卡通过率：{df['结果'].eq('通过').mean():.0%}\n\n")
    output.write("## 仿真记录\n\n")
    output.write(df.to_markdown(index=False))
    output.write("\n\n## 决策边界\n\n本报告来自本地仿真，不构成对任何外部网站的访问许可。生产实施必须以书面授权和平台规则为前提。\n")
    return output.getvalue()


st.set_page_config(page_title="网络采集合规与策略选择仿真", layout="wide")
st.title("网络采集合规与策略选择虚拟仿真")
st.caption("生产任务映射：数据采集工程师根据授权范围、运行信号、服务等级和资源成本选择实施策略。")

with st.expander("生产任务单与验收标准", expanded=True):
    st.markdown(
        """
        **任务目标：** 为经过授权的数据同步任务制定可执行、可审计、成本适当的采集策略。  
        **工作流程：** 确认授权 → 识别运行信号 → 比较技术策略 → 评估成本 → 制定处置方案 → 提交评审报告。  
        **交付物：** 合规检查表、策略对比表、异常处置记录、策略评审报告。  
        **一票否决：** 未取得授权、未确认平台规则、超出数据范围或涉及不必要个人信息时，不得执行采集。
        """
    )

with st.sidebar:
    task_id = st.text_input("任务编号", value="SIM-COM-001")
    scenario = st.selectbox("业务场景", list(SCENARIOS))
    st.caption(SCENARIOS[scenario])
    selected = st.multiselect("选择运行信号", [c.name for c in CHALLENGES], default=[c.name for c in CHALLENGES])
    strategy = st.selectbox("候选采集策略", list(STRATEGIES))
    rounds = st.slider("重复验证轮次", 1, 5, 3)
    max_cost = st.slider("允许的资源成本级", 1, 6, 5)
    st.caption(f"Scrapling 环境状态：{'已安装' if SCRAPLING_AVAILABLE else '未安装'}；本项目不连接外部网站。")

st.subheader("合规前置检查")
c1, c2, c3, c4 = st.columns(4)
authorization = c1.checkbox("已取得数据源授权")
rules_checked = c2.checkbox("已核对条款和robots")
scope_limited = c3.checkbox("字段范围最小必要")
privacy_checked = c4.checkbox("不采集无关个人信息")
compliant = all([authorization, rules_checked, scope_limited, privacy_checked])
if compliant:
    st.success("合规前置检查通过，可以进入技术策略评审。")
else:
    st.warning("合规前置检查未完成：仿真可以继续，但生产任务不得执行。")

active_challenges = [c for c in CHALLENGES if c.name in selected]
records = [evaluate(challenge, strategy, round_no) for round_no in range(1, rounds + 1) for challenge in active_challenges]
df = pd.DataFrame(records)

if df.empty:
    st.info("请至少选择一个运行信号。")
    st.stop()

pass_rate = df["结果"].eq("通过").mean()
cost_ok = int(STRATEGIES[strategy]["cost"]) <= max_cost
technical_ok = pass_rate == 1.0 and cost_ok
release_ok = compliant and technical_ok

m1, m2, m3, m4 = st.columns(4)
m1.metric("技术通过率", f"{pass_rate:.0%}")
m2.metric("平均耗时", f"{df['估计耗时秒'].mean():.2f}s")
m3.metric("资源成本级", STRATEGIES[strategy]["cost"])
m4.metric("生产放行", "允许" if release_ok else "不允许")

left, right = st.columns([1.35, 1])
with left:
    st.subheader("仿真记录")
    st.dataframe(df, width="stretch")
with right:
    st.subheader("运行信号通过率")
    summary = df.assign(通过=df["结果"].eq("通过")).groupby("运行信号", as_index=False)["通过"].mean()
    st.plotly_chart(px.bar(summary, x="运行信号", y="通过", range_y=[0, 1], color="通过"), width="stretch")

st.subheader("评审结论")
if release_ok:
    st.success("该策略同时通过授权、技术和资源约束，可进入受控测试环境。")
elif not compliant:
    st.error("合规条件未满足，禁止进入生产执行。")
elif not cost_ok:
    st.error("策略超过资源预算，应降低技术复杂度或重新协商服务等级。")
else:
    st.error("技术能力未覆盖全部运行信号，应补充能力或缩小任务范围。")

report = build_report(task_id, scenario, strategy, compliant, df)
d1, d2 = st.columns(2)
d1.download_button("下载仿真记录 CSV", df.to_csv(index=False).encode("utf-8-sig"), f"{task_id}_仿真记录.csv", "text/csv")
d2.download_button("下载策略评审报告", report, f"{task_id}_策略评审报告.md", "text/markdown")

st.info("本平台训练的是授权判断、策略选型和异常处置，不训练绕过访问控制。所有结果仅来自本地规则仿真。")
