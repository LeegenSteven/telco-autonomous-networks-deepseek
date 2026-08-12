from google.adk import Agent
from google.adk.tools import ToolContext

from root_cause_analysis.constants import KEY_INSTRUCTIONS, KEY_PROCESSING_RULES
from telco_local.model_provider import build_model


async def receive_instructions(
    tool_context: ToolContext,
    instructions: str,
) -> dict:
    tool_context.state[KEY_INSTRUCTIONS] = instructions
    return {"status": "success"}


def build_instruction_generator_agent() -> Agent:
    return Agent(
        model=build_model("instruction_generator"),
        name="instruction_generator_agent",
        description="把本地 RCA 规则转换为 Analyzer 指令",
        instruction=f"""
只能依据以下规则，为 RCA Agent 生成准确、可执行的简体中文分析指令：
{{{KEY_PROCESSING_RULES}}}

保留工具名称和 KPI 等专业标识。完成后调用 receive_instructions，并提交完整指令。
""",
        tools=[receive_instructions],
    )
