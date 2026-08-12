from google.adk import Agent

from root_cause_analysis.constants import (
    KEY_ANALYSIS,
    KEY_EXTERNAL_SEARCH_RESULTS,
    KEY_INCIDENT_INFO,
    KEY_INTERNAL_SEARCH_RESULTS,
    KEY_PRIOR_INCIDENTS,
    KEY_SEVERITY_EXPLANATION,
    KEY_SEVERITY_LEVEL,
)
from telco_local.model_provider import build_model


def build_report_generator() -> Agent:
    return Agent(
        model=build_model("report_generator"),
        name="report_generator_agent",
        description="根据已收集的本地证据生成中文 RCA 报告",
        instruction=f"""
只能依据下方证据生成简体中文 RCA 报告，不得补充未经证据支持的事实。

当前 Incident：{{{KEY_INCIDENT_INFO}}}
Root Cause Analysis：{{{KEY_ANALYSIS}}}
严重程度：{{{KEY_SEVERITY_LEVEL}}}
严重程度说明：{{{KEY_SEVERITY_EXPLANATION}}}
外部资料：{{{KEY_EXTERNAL_SEARCH_RESULTS}?}} 
内部资料：{{{KEY_INTERNAL_SEARCH_RESULTS}?}} 
历史相似 Incident：{{{KEY_PRIOR_INCIDENTS}?}} 

报告必须使用简体中文，并按以下固定章节组织：
1. Incident 概述
2. Root Cause Analysis
3. 严重程度
4. 相似历史 Incident
5. 内部资料
6. 外部资料
7. 建议措施
8. 参考资料

保留 Incident ID、KPI、eNodeB、Cell ID、ERAB 等专业名词。某章节没有信息时，
明确写“暂无相关信息”，不要删除该章节。不得暴露 IMSI、MSISDN 或 IMEISV。
""",
    )
