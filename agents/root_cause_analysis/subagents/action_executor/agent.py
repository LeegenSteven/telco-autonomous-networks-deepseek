from typing import Optional

from google.adk import Agent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types
from google.genai.types import FunctionCall

from root_cause_analysis.constants import KEY_ACTIONS
from root_cause_analysis.settings import settings
from root_cause_analysis.tools.analysis_tools import automatic_action_toolset
from telco_local.model_provider import build_model


async def check_if_there_are_actions(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    if not callback_context.state.get(KEY_ACTIONS):
        return types.Content(
            role="model",
            parts=[
                types.Part(text="当前没有建议执行的自动化动作。"),
                types.Part(
                    function_call=FunctionCall(
                        name="transfer_to_agent",
                        args={"agent_name": settings.root_agent_name},
                    )
                ),
            ],
        )
    return None


def build_action_executor() -> Agent:
    return Agent(
        model=build_model("agent_executor"),
        name="action_executor",
        description="列出建议动作、请求确认并执行本地模拟操作",
        instruction=f"""
建议动作：{{{KEY_ACTIONS}}}

所有面向用户的文字使用简体中文。列出建议动作、参数、理由和可能影响，并询问用户
希望执行哪一个；未得到明确确认前不得执行。调用时必须使用已注册的准确工具名称
和参数。这些演示工具不会修改真实网络设备。如果用户已经在当前请求中拒绝全部
动作，不要重复询问，立即返回 {settings.root_agent_name} 生成报告。任何已批准的
动作执行完成后也要返回该 Agent。
""",
        tools=[automatic_action_toolset],
        before_agent_callback=check_if_there_are_actions,
    )
