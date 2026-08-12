from google.adk.agents import LlmAgent
from google.adk.apps import App

from incident_detector.tools import create_new_incident, get_potential_incidents
from telco_local.logging_config import configure_local_logging
from telco_local.model_provider import build_model


configure_local_logging()

incident_detector_agent = LlmAgent(
    model=build_model("incident_detector"),
    name="incident_detector",
    static_instruction="""
你是电信网络事故检测助手。所有面向用户的回复必须使用简体中文，Incident ID、
KPI、eNodeB、Cell ID、ERAB、Retainability 等专业名词可以保留英文。

调用工具获取并分析潜在 Incident，说明发现数量、异常 KPI、位置和时间范围，
再按严重程度给出优先级。创建新 Incident 前必须用中文询问用户并获得明确确认。
不得编造 KPI 数值，只能使用工具返回的数据。时间使用 `YYYY-MM-DD HH:MM:SS`
格式，不要输出英文星期或月份。
""",
    description=(
        "检查本地 LTE KPI 数据、识别潜在网络事故，并在保存前征求用户确认。"
    ),
    tools=[get_potential_incidents, create_new_incident],
)

root_agent = incident_detector_agent

app = App(
    name="incident_detector",
    root_agent=root_agent,
)
