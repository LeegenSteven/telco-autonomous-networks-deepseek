import logging

from google.adk.tools import ToolContext

from root_cause_analysis.constants import (
    KEY_INCIDENT_DATA,
    KEY_INCIDENT_INFO,
    KEY_SEVERITY_LEVEL,
)
from root_cause_analysis.models import Incident
from root_cause_analysis.tools.database import execute_statement


logger = logging.getLogger(__name__)


async def add_new_incident_data_section(
    tool_context: ToolContext,
    section_name: str,
    details: str,
) -> None:
    incident_data = tool_context.state.get(KEY_INCIDENT_DATA, "")
    tool_context.state[KEY_INCIDENT_DATA] = (
        incident_data
        + ("\n\n" if incident_data else "")
        + f"**{section_name}**\n{details}"
    )


async def update_incident(tool_context: ToolContext, report: str) -> dict:
    """把用户已批准的 RCA 报告保存到本地 DuckDB。"""

    incident = Incident.model_validate_json(tool_context.state[KEY_INCIDENT_INFO])
    severity = tool_context.state.get(KEY_SEVERITY_LEVEL, "UNKNOWN")
    events = tool_context.state.get(KEY_INCIDENT_DATA, "")

    try:
        execute_statement(
            """
            UPDATE incidents
            SET status = 'ANALYZED',
                preliminary_analysis = ?,
                severity = ?,
                events = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE incident_id = ?
            """,
            [report, severity, events, incident.id],
        )
    except Exception as exc:
        logger.exception("Failed to update incident %s", incident.id)
        return {"status": "error", "description": f"更新 Incident 失败：{exc}"}

    logger.info("Incident %s successfully updated", incident.id)
    return {"status": "success", "incident_id": incident.id}
