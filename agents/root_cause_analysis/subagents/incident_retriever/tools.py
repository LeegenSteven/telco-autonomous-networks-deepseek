import json
import logging
from typing import Optional

from google.adk.tools import ToolContext

from root_cause_analysis.constants import KEY_INCIDENT_INFO
from root_cause_analysis.models import Incident, MissedKPI
from root_cause_analysis.tools.database import execute_query
from root_cause_analysis.tools.incident_data import add_new_incident_data_section


logger = logging.getLogger(__name__)


async def get_incident_info(
    tool_context: ToolContext,
    incident_id: str,
) -> dict:
    """根据 Incident ID 从本地 DuckDB 读取事故。"""

    try:
        rows = execute_query(
            """
            SELECT incident_id, enodeb_id, cell_id, start_ts, end_ts,
                   status, description, kpi_missed, severity
            FROM incidents
            WHERE incident_id = ?
            """,
            [incident_id],
        )
    except Exception as exc:
        logger.exception("Failed to retrieve incident %s", incident_id)
        return {"status": "error", "description": f"读取 Incident 失败：{exc}"}

    if not rows:
        return {
            "status": "not found",
            "description": f"未找到 Incident ID 为 {incident_id} 的记录",
        }
    if len(rows) > 1:
        return {"status": "error", "description": "Incident ID 不唯一"}

    row = rows[0]
    raw_kpis = json.loads(row.kpi_missed)
    incident: Optional[Incident] = Incident(
        id=row.incident_id,
        enodeb_id=row.enodeb_id,
        cell_id=row.cell_id,
        start_time=row.start_ts.isoformat(sep=" "),
        end_time=row.end_ts.isoformat(sep=" ") if row.end_ts else None,
        status=row.status,
        description=row.description,
        severity=row.severity,
        kpi_missed=[MissedKPI.model_validate(item) for item in raw_kpis],
    )

    tool_context.state[KEY_INCIDENT_INFO] = incident.model_dump_json()
    duration_seconds = (
        (row.end_ts - row.start_ts).total_seconds() if row.end_ts else 0
    )
    await add_new_incident_data_section(
        tool_context,
        "基本信息",
        "异常 KPI："
        + ", ".join(item.to_descriptive_string() for item in incident.kpi_missed)
        + f"。持续时间：{duration_seconds} 秒。",
    )
    return {"status": "success", "incident": incident}
