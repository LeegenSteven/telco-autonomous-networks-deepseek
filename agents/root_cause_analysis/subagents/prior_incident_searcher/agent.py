import json
import logging

from google.adk import Agent
from google.adk.tools import ToolContext

from root_cause_analysis.constants import KEY_INCIDENT_DATA, KEY_PRIOR_INCIDENTS
from root_cause_analysis.tools.database import execute_query
from telco_local.model_provider import build_model
from telco_local.settings import settings
from telco_local.similarity import cosine_similarity


logger = logging.getLogger(__name__)


def build_prior_incidents_searcher() -> Agent:
    return Agent(
        model=build_model("prior_incidents_searcher"),
        name="prior_incidents_search_agent",
        description="在本地 DuckDB 中搜索相似的历史 Incident",
        instruction=(
            "调用 prior_incident_search，只能报告工具返回的 Incident。"
            "所有说明使用简体中文；Incident ID、KPI 等专业标识可以保留英文。"
        ),
        output_key=KEY_PRIOR_INCIDENTS,
        tools=[prior_incident_search],
    )


async def prior_incident_search(tool_context: ToolContext) -> dict:
    query_events = tool_context.state.get(KEY_INCIDENT_DATA, "")
    rows = execute_query(
        """
        SELECT incident_id, start_ts, end_ts, status, description, events,
               kpi_missed, enodeb_id, cell_id, cause, severity,
               final_analysis, preliminary_analysis, resolution
        FROM incidents
        WHERE events IS NOT NULL AND events <> ''
        """
    )

    ranked = sorted(
        (
            (cosine_similarity(query_events, row.events), row)
            for row in rows
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    matches = [
        (score, row)
        for score, row in ranked
        if score >= settings.similarity_search_min_score
    ][: settings.similarity_search_max_number_of_incidents]

    result = [
        {
            "incident_id": row.incident_id,
            "similarity": round(score, 4),
            "description": row.description,
            "events": row.events,
            "severity": row.severity,
            "cause": row.cause,
            "analysis": row.final_analysis or row.preliminary_analysis,
            "resolution": row.resolution,
            "kpi_missed": json.loads(row.kpi_missed),
        }
        for score, row in matches
    ]
    return (
        {"status": "success", "prior_incidents": result}
        if result
        else {"status": "no similar incidents found", "message": "未找到相似的历史 Incident", "prior_incidents": []}
    )
