from google.adk import Agent
from google.adk.apps import App
from google.adk.tools import AgentTool

from root_cause_analysis.settings import settings
from root_cause_analysis.subagents.action_executor.agent import build_action_executor
from root_cause_analysis.subagents.analyzer.agent import build_analyzer_agent
from root_cause_analysis.subagents.external_documentation_searcher.agent import (
    build_external_documentation_retriever,
)
from root_cause_analysis.subagents.incident_retriever.tools import get_incident_info
from root_cause_analysis.subagents.instructions_generator.agent import (
    build_instruction_generator_agent,
)
from root_cause_analysis.subagents.internal_documentation_retriever.agent import (
    build_internal_documentation_retriever_agent,
)
from root_cause_analysis.subagents.prior_incident_searcher.agent import (
    build_prior_incidents_searcher,
)
from root_cause_analysis.subagents.report_generator.agent import build_report_generator
from root_cause_analysis.subagents.rules_retriever.agent import (
    build_rules_retriever_agent,
)
from root_cause_analysis.subagents.severity_classifier.agent import (
    build_severity_classifier_agent,
)
from root_cause_analysis.tools.incident_data import update_incident
from telco_local.adk_callbacks import serialize_function_calls
from telco_local.logging_config import configure_local_logging
from telco_local.model_provider import build_model


configure_local_logging()

external_documentation_retriever_agent = build_external_documentation_retriever()
internal_documentation_retriever_agent = (
    build_internal_documentation_retriever_agent()
)
prior_incidents_search_agent = build_prior_incidents_searcher()
report_generator_agent = build_report_generator()
instruction_generator = build_instruction_generator_agent()
analyzer = build_analyzer_agent()
rules_retriever = build_rules_retriever_agent()
severity_classifier = build_severity_classifier_agent()
action_performer = build_action_executor()

progress_instruction = (
    "每一步开始前，用简体中文说明下一步并等待用户确认。"
    if settings.confirm_each_step
    else "每一步开始前，用简体中文简要说明当前进度。"
)

root_agent = Agent(
    model=build_model("root_agent"),
    name=settings.root_agent_name,
    description="针对 LTE Incident 的本地化根因分析（RCA）助手",
    static_instruction=f"""
你负责对 LTE 网络 Incident 执行基于证据的 Root Cause Analysis（RCA）。
所有面向用户的进度、问题、结论和报告必须使用简体中文；Incident ID、KPI、
eNodeB、Cell ID、ERAB、Retainability、RCA、IMSI、MSISDN、IMEISV 等专业名词
可以保留英文。所有数据来自本地 DuckDB 和本地文档，不得编造测量结果。

首先获取 Incident ID 并调用 get_incident_info。找不到 Incident 时必须停止，
用中文说明原因并请用户提供其他 ID。找到后严格按顺序执行：
1. 检索与当前 Incident 相关的本地规则。
2. 根据规则生成 Analyzer 指令。
3. 把 RCA 分析交给 analyzer_agent。
4. 把严重程度判断交给 severity_classifier_agent。
5. 检索可选的外部资料和本地内部资料。
6. 搜索相似的历史 Incident。
7. 仅当用户尚未决定是否执行建议动作时，才交给 action_executor 审阅模拟动作。
   如果用户在初始请求中已经拒绝全部动作，必须完全跳过 action_executor 并直接
   进入第 8 步；如果用户在 action_executor 中拒绝动作，返回后继续第 8 步。
8. 必须调用 report_generator_agent 生成最终中文报告。不得由根 Agent 自行撰写
   最终报告，也不得跳过该工具。用户拒绝保存报告只会阻止 update_incident，
   不能取消报告生成。

展示中文报告后，询问用户是否保存到本地 Incident 记录。只有得到明确确认后
才能调用 update_incident。任何模型可见文字都不得包含完整的 IMSI、MSISDN 或
IMEISV。不得向用户展示英文思考过程或内部编排说明。

{progress_instruction}
""",
    sub_agents=[analyzer, severity_classifier, action_performer],
    tools=[
        get_incident_info,
        AgentTool(agent=rules_retriever),
        AgentTool(agent=instruction_generator),
        AgentTool(agent=external_documentation_retriever_agent),
        AgentTool(agent=internal_documentation_retriever_agent),
        AgentTool(agent=prior_incidents_search_agent),
        AgentTool(agent=report_generator_agent),
        update_incident,
    ],
    after_model_callback=serialize_function_calls,
)

app = App(
    name="root_cause_analysis",
    root_agent=root_agent,
)
