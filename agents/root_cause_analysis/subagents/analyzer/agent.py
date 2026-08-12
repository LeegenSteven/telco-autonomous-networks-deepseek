from google.adk import Agent
from google.adk.tools import ToolContext

from root_cause_analysis.constants import (
    KEY_ACTIONS,
    KEY_ANALYSIS,
    KEY_INSTRUCTIONS,
    KEY_PROCESSING_RULES_TOOLS,
)
from root_cause_analysis.models import Action
from root_cause_analysis.settings import settings
from root_cause_analysis.tools.analysis_tools import AnalysisToolset
from telco_local.model_provider import build_model


processing_rules_toolset = AnalysisToolset(state_key=KEY_PROCESSING_RULES_TOOLS)


async def save_analysis(
    tool_context: ToolContext,
    analysis: str,
    action_tool_name: str = "",
    action_parameters: dict | None = None,
    action_reason: str = "",
) -> dict:
    """保存分析、按需登记一个建议动作，然后返回根 Agent。"""

    tool_context.state[KEY_ANALYSIS] = analysis
    if action_tool_name:
        actions = [
            Action.model_validate_json(item)
            for item in tool_context.state.get(KEY_ACTIONS, [])
        ]
        actions.append(
            Action(
                tool_name=action_tool_name,
                reason_to_perform=action_reason,
                parameters=action_parameters or {},
            )
        )
        tool_context.state[KEY_ACTIONS] = [
            item.model_dump_json() for item in actions
        ]
    tool_context.actions.transfer_to_agent = settings.root_agent_name
    return {
        "status": "success",
        "action_registered": bool(action_tool_name),
        "next_agent": settings.root_agent_name,
    }


def build_analyzer_agent() -> Agent:
    return Agent(
        model=build_model("analyzer"),
        name="analyzer_agent",
        description="依据本地证据和生成的指令执行 RCA",
        instruction=f"""
{{{KEY_INSTRUCTIONS}}}

分析和工具参数可以保留 KPI、eNodeB、Cell ID 等专业名词，但分析结论和动作理由必须
使用简体中文。只能使用可用工具及其返回的证据。如果适合建议自动化动作，在
save_analysis 中提供工具名称、参数和中文理由；否则省略这些可选字段。最后必须且
只能调用一次 save_analysis，并提交完整、基于证据的中文分析。该原子操作会保存
结果、按需登记动作，并把控制权交回根 Agent。不得只在聊天文字中描述分析。
""",
        tools=[processing_rules_toolset, save_analysis],
        output_key=KEY_ANALYSIS,
    )
