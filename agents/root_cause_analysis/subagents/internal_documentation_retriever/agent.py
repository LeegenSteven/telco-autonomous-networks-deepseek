from google.adk import Agent

from root_cause_analysis.constants import KEY_INCIDENT_INFO
from root_cause_analysis.tools.local_search import search_internal_documentation
from telco_local.model_provider import build_model


def build_internal_documentation_retriever_agent() -> Agent:
    return Agent(
        model=build_model("internal_doc_retriever"),
        name="internal_documentation_retriever_agent",
        description="检索与当前 Incident 相关的本地资料",
        instruction=f"""
在本地资料中检索与下方 Incident 有关的可能原因和建议措施：
{{{KEY_INCIDENT_INFO}}}

查询内容和面向用户的结果使用简体中文。只能使用
search_internal_documentation 返回的结果，不得虚构参考资料。
""",
        tools=[search_internal_documentation],
    )
