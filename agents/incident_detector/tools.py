import json
import logging
import uuid
from datetime import datetime
from typing import Optional

from google.adk.tools import ToolContext

from incident_detector.models import Incident, MissedKPI
from telco_local.database import execute_query, execute_statement


logger = logging.getLogger(__name__)
INCIDENTS_ATTR = "incidents"


async def get_potential_incidents(tool_context: ToolContext) -> dict:
    """从本地 DuckDB 性能视图中查找超过阈值的 KPI。"""

    query = """
    WITH missed_kpis AS (
        SELECT
            CAST(enodeb_id AS VARCHAR) AS enodeb_id,
            CAST(cell_id AS VARCHAR) AS cell_id,
            measurement_end,
            'erab_success_rate' AS kpi,
            erab_success_rate AS kpi_value,
            'ERAB 成功率低于 97%' AS description
        FROM performance_kpi
        WHERE erab_success_rate < 97

        UNION ALL

        SELECT
            CAST(enodeb_id AS VARCHAR) AS enodeb_id,
            CAST(cell_id AS VARCHAR) AS cell_id,
            measurement_end,
            'retainability' AS kpi,
            retainability AS kpi_value,
            'Retainability 高于 3' AS description
        FROM performance_kpi
        WHERE retainability > 3
    )
    SELECT
        enodeb_id,
        cell_id,
        description,
        kpi,
        AVG(kpi_value) AS kpi_value,
        MIN(measurement_end) AS started,
        MAX(measurement_end) AS ended
    FROM missed_kpis
    GROUP BY enodeb_id, cell_id, description, kpi
    ORDER BY started, enodeb_id, cell_id, kpi
    """

    try:
        rows = execute_query(query)
    except Exception as exc:
        logger.exception("Failed to retrieve potential incidents")
        return {"status": "error", "description": f"读取潜在 Incident 失败：{exc}"}

    incidents = [
        Incident(
            id=str(uuid.uuid4()),
            status="NEW",
            description=row.description,
            kpi_missed=[MissedKPI(kpi=row.kpi, value=row.kpi_value)],
            enodeb_id=row.enodeb_id,
            cell_id=row.cell_id,
            start_time=row.started.isoformat(sep=" "),
            end_time=row.ended.isoformat(sep=" "),
        )
        for row in rows
    ]

    tool_context.state[INCIDENTS_ATTR] = [
        incident.model_dump_json() for incident in incidents
    ]
    logger.info("Found %d potential incidents", len(incidents))
    return {"status": "success", "incidents": incidents}


async def create_new_incident(
    tool_context: ToolContext,
    incident_id: str,
) -> dict:
    """把用户已确认的潜在 Incident 保存到本地 DuckDB。"""

    serialized = tool_context.state.get(INCIDENTS_ATTR, [])
    incidents = [Incident.model_validate_json(item) for item in serialized]
    incident: Optional[Incident] = next(
        (item for item in incidents if item.id == incident_id),
        None,
    )
    if not incident:
        return {
            "status": "failed",
            "reason": "无法根据给定的 Incident ID 找到候选事故",
        }

    try:
        execute_statement(
            """
            INSERT INTO incidents (
                incident_id, enodeb_id, cell_id, start_ts, end_ts,
                status, description, kpi_missed
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (incident_id) DO NOTHING
            """,
            [
                incident.id,
                incident.enodeb_id,
                incident.cell_id,
                datetime.fromisoformat(incident.start_time),
                datetime.fromisoformat(incident.end_time)
                if incident.end_time
                else None,
                incident.status,
                incident.description,
                json.dumps(
                    [item.model_dump() for item in incident.kpi_missed],
                    ensure_ascii=False,
                ),
            ],
        )
    except Exception as exc:
        logger.exception("Failed to save incident %s", incident_id)
        return {"status": "error", "description": f"保存 Incident 失败：{exc}"}

    logger.info("Incident %s successfully created", incident_id)
    return {"status": "success", "incident_id": incident_id}
