from google.adk import Agent

from root_cause_analysis.subagents.incident_retriever.tools import get_incident_info
from telco_local.model_provider import build_model


def build_incident_retriever_agent() -> Agent:
    return Agent(
        model=build_model("incident_retriever"),
        name="incident_retriever_agent",
        description="从本地 DuckDB 读取 Incident 信息",
        instruction="""
使用用户提供的准确 Incident ID 读取事故。如果找不到，用简体中文说明并请用户
提供其他 ID。不得虚构 Incident。面向用户的文字必须使用简体中文。
""",
        tools=[get_incident_info],
    )
