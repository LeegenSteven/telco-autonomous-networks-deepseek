from google.adk import Agent
from google.adk.tools import ToolContext

from root_cause_analysis.constants import (
    KEY_INCIDENT_INFO,
    KEY_SEVERITY_DETERMINATION_RULES,
    KEY_SEVERITY_DETERMINATION_RULES_TOOLS,
    KEY_SEVERITY_EXPLANATION,
    KEY_SEVERITY_LEVEL,
)
from root_cause_analysis.settings import settings
from root_cause_analysis.tools.analysis_tools import AnalysisToolset
from telco_local.model_provider import build_model


async def update_severity_level(
    tool_context: ToolContext,
    severity: str,
    explanation: str,
) -> dict:
    tool_context.state[KEY_SEVERITY_LEVEL] = severity
    tool_context.state[KEY_SEVERITY_EXPLANATION] = explanation
    tool_context.actions.transfer_to_agent = settings.root_agent_name
    return {"status": "success"}


severity_rule_toolset = AnalysisToolset(
    state_key=KEY_SEVERITY_DETERMINATION_RULES_TOOLS
)


def build_severity_classifier_agent() -> Agent:
    return Agent(
        model=build_model("severity_classifier"),
        name="severity_classifier_agent",
        description="依据本地规则判断 Incident 严重程度",
        instruction=f"""
判断下方 Incident 的严重程度：
{{{KEY_INCIDENT_INFO}}}

只能使用以下规则：
{{{KEY_SEVERITY_DETERMINATION_RULES}}}

severity 字段必须为 HIGH、MEDIUM 或 LOW。调用 update_severity_level，并提供
severity 和简明、基于证据的中文说明。不得输出未经规则支持的判断。
""",
        tools=[severity_rule_toolset, update_severity_level],
    )
