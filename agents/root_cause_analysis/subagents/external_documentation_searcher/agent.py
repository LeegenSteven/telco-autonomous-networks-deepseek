from google.adk import Agent

from root_cause_analysis.constants import KEY_INCIDENT_INFO
from root_cause_analysis.tools.local_search import retrieve_external_documentation
from telco_local.model_provider import build_model


def build_external_documentation_retriever() -> Agent:
    return Agent(
        model=build_model("external_doc_retriever"),
        name="external_documentation_retriever_agent",
        description="检索可选且位于允许列表中的外部资料",
        instruction=f"""
工具启用时，为下方 Incident 检索外部资料：
{{{KEY_INCIDENT_INFO}}}

所有可见结果使用简体中文，只能依据工具返回内容。若外部检索已关闭，直接说明
“外部资料检索当前已关闭”，不得虚构资料或引用。
""",
        tools=[retrieve_external_documentation],
    )
