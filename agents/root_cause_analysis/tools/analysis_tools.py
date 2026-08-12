import logging
from typing import Optional, override

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import BaseTool, FunctionTool, ToolContext
from google.adk.tools.base_toolset import BaseToolset

from root_cause_analysis.constants import KEY_ACTIONS, KEY_INCIDENT_INFO
from root_cause_analysis.models import Action, CellTracesStats, Incident
from root_cause_analysis.tools.database import execute_query
from root_cause_analysis.tools.incident_data import add_new_incident_data_section


logger = logging.getLogger(__name__)


async def get_cell_trace_statistics(tool_context: ToolContext) -> dict:
    """返回当前 Incident 时间窗口内的 S1 连接结果统计。"""

    incident = Incident.model_validate_json(tool_context.state[KEY_INCIDENT_INFO])
    try:
        rows = execute_query(
            """
            SELECT
                COALESCE(s1_sig_conn_setup_sig_conn_result, 'OTHER') AS connection_outcome,
                COUNT(*) AS number_of_outcomes
            FROM cell_traces
            WHERE CAST(start_enodeb_id AS VARCHAR) = ?
              AND CAST(start_cell_id AS VARCHAR) = ?
              AND starttime >= ?
              AND endtime <= ?
            GROUP BY connection_outcome
            ORDER BY connection_outcome
            """,
            [
                incident.enodeb_id,
                incident.cell_id,
                incident.start_time,
                incident.end_time,
            ],
        )
    except Exception as exc:
        logger.exception("Failed to retrieve cell trace statistics")
        return {"status": "error", "description": f"读取 Cell Trace 统计失败：{exc}"}

    result = [
        CellTracesStats(
            connection_outcome=row.connection_outcome,
            count=row.number_of_outcomes,
        )
        for row in rows
    ]
    await add_new_incident_data_section(
        tool_context,
        "Cell Trace 统计",
        ", ".join(f"{item.connection_outcome}: {item.count}" for item in result)
        or "没有匹配的 Cell Trace",
    )
    return {
        "status": "success" if result else "no cell traces found",
        "message": "已获得 Cell Trace 聚合统计" if result else "未找到匹配的 Cell Trace",
        "cell_trace_statistics": result,
    }


async def get_uplink_rssi_level(
    tool_context: ToolContext,
    enodeb_id: str,
    cell_id: str,
) -> dict:
    """返回本地演示数据中的模拟上行 RSSI。"""

    return {"status": "success", "uplink_signal_strength": "-100"}


async def get_uplink_configuration(
    tool_context: ToolContext,
    enodeb_id: str,
    cell_id: str,
) -> dict:
    """返回本地演示数据中的模拟上行链路配置。"""

    return {
        "status": "success",
        "pZeroNominalPucch": "-110",
        "pZeroNominalPusch": "-94",
    }


async def initiate_uplink_configuration_adjustment(
    tool_context: ToolContext,
    enodeb_id: str,
    cell_id: str,
) -> dict:
    """模拟执行用户已批准的上行链路配置调整。"""

    return {
        "status": "success",
        "details": (
            "已接受模拟上行链路调整；没有修改任何真实网络设备。"
        ),
    }


available_tools: list[FunctionTool] = [
    FunctionTool(func=get_cell_trace_statistics),
    FunctionTool(func=get_uplink_configuration),
    FunctionTool(func=get_uplink_rssi_level),
    FunctionTool(func=initiate_uplink_configuration_adjustment),
]


class AnalysisToolset(BaseToolset):
    def __init__(self, state_key: str):
        super().__init__()
        self.state_key = state_key

    @override
    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> list[BaseTool]:
        if not readonly_context:
            return available_tools
        required_tools = readonly_context.state.get(self.state_key, [])
        return [
            tool for tool in available_tools if tool.func.__name__ in required_tools
        ]


class AutomaticActionToolset(BaseToolset):
    @override
    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> list[BaseTool]:
        if not readonly_context:
            return available_tools
        required_tools = [
            Action.model_validate_json(action_json).tool_name
            for action_json in readonly_context.state.get(KEY_ACTIONS, [])
        ]
        return [
            tool for tool in available_tools if tool.func.__name__ in required_tools
        ]


automatic_action_toolset = AutomaticActionToolset()
