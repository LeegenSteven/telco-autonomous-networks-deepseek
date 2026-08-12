import asyncio
from types import SimpleNamespace

import pytest

from incident_detector.tools import create_new_incident, get_potential_incidents
from root_cause_analysis.constants import (
    KEY_INCIDENT_DATA,
    KEY_INCIDENT_INFO,
    KEY_SEVERITY_LEVEL,
)
from root_cause_analysis.models import Incident, MissedKPI
from root_cause_analysis.subagents.incident_retriever.tools import get_incident_info
from root_cause_analysis.tools.analysis_tools import get_cell_trace_statistics
from root_cause_analysis.tools.local_search import find_rca_rules
from root_cause_analysis.tools.incident_data import update_incident
from telco_local.database import execute_query
from telco_local.init_db import initialize_database
from telco_local.settings import settings
from telco_local.similarity import cosine_similarity


@pytest.fixture()
def local_database(tmp_path, monkeypatch):
    database_path = tmp_path / "telco.duckdb"
    monkeypatch.setattr(settings, "local_db_path", str(database_path))
    initialize_database(reset=True)
    return database_path


def test_kpi_view_matches_known_first_row(local_database):
    row = execute_query(
        """
        SELECT erab_success_rate, retainability
        FROM performance_kpi
        ORDER BY measurement_end
        LIMIT 1
        """
    )[0]
    assert row.erab_success_rate == pytest.approx(430 * 100 / 431)
    assert row.retainability == pytest.approx(9 * 3600 / 20907)


def test_detector_creates_and_retrieves_local_incident(local_database):
    context = SimpleNamespace(state={}, actions=SimpleNamespace())
    potential = asyncio.run(get_potential_incidents(context))
    assert potential["status"] == "success"
    assert potential["incidents"]

    incident = potential["incidents"][0]
    created = asyncio.run(create_new_incident(context, incident.id))
    assert created == {"status": "success", "incident_id": incident.id}

    rca_context = SimpleNamespace(state={}, actions=SimpleNamespace())
    retrieved = asyncio.run(get_incident_info(rca_context, incident.id))
    assert retrieved["status"] == "success"
    stored = Incident.model_validate_json(rca_context.state[KEY_INCIDENT_INFO])
    assert stored.id == incident.id
    assert stored.kpi_missed[0].kpi == incident.kpi_missed[0].kpi


def test_approved_rca_report_updates_local_incident(local_database):
    detector_context = SimpleNamespace(state={}, actions=SimpleNamespace())
    potential = asyncio.run(get_potential_incidents(detector_context))
    incident = potential["incidents"][0]
    asyncio.run(create_new_incident(detector_context, incident.id))

    rca_context = SimpleNamespace(
        state={
            KEY_INCIDENT_INFO: Incident(
                id=incident.id,
                description=incident.description,
                kpi_missed=[item.model_dump() for item in incident.kpi_missed],
                enodeb_id=incident.enodeb_id,
                cell_id=incident.cell_id,
                status="NEW",
                start_time=incident.start_time,
                end_time=incident.end_time,
            ).model_dump_json(),
            KEY_SEVERITY_LEVEL: "HIGH",
            KEY_INCIDENT_DATA: "Aggregated test evidence",
        },
        actions=SimpleNamespace(),
    )
    result = asyncio.run(update_incident(rca_context, "Approved test report"))

    assert result == {"status": "success", "incident_id": incident.id}
    stored = execute_query(
        """
        SELECT status, preliminary_analysis, severity, events
        FROM incidents
        WHERE incident_id = ?
        """,
        [incident.id],
    )[0]
    assert stored.status == "ANALYZED"
    assert stored.preliminary_analysis == "Approved test report"
    assert stored.severity == "HIGH"
    assert stored.events == "Aggregated test evidence"


def test_local_rule_lookup_dynamically_selects_tools():
    rules = asyncio.run(
        find_rca_rules([MissedKPI(kpi="erab_success_rate", value=94.5)])
    )
    assert len(rules) == 1
    assert "get_cell_trace_statistics" in rules[0].processing_rule_tools


def test_cell_trace_tool_returns_only_aggregated_outcomes(local_database):
    incident = Incident(
        id="trace-test",
        description="Trace aggregation test",
        kpi_missed=[MissedKPI(kpi="erab_success_rate", value=94.5)],
        enodeb_id="1",
        cell_id="12314",
        status="NEW",
        start_time="2025-11-24 15:00:00",
        end_time="2025-11-24 18:18:40",
    )
    context = SimpleNamespace(
        state={KEY_INCIDENT_INFO: incident.model_dump_json()},
        actions=SimpleNamespace(),
    )
    result = asyncio.run(get_cell_trace_statistics(context))
    outcomes = {
        item.connection_outcome: item.count
        for item in result["cell_trace_statistics"]
    }

    assert result["status"] == "success"
    assert outcomes["FAILED_SECURITY_SETUP"] == 21
    assert outcomes["SUCCESS"] == 144
    assert "imsi" not in str(result).lower()


def test_local_similarity_prefers_related_incidents():
    related = cosine_similarity(
        "ERAB setup failed due to S1 security failure",
        "S1 security setup failure caused ERAB setup errors",
    )
    unrelated = cosine_similarity(
        "ERAB setup failed due to S1 security failure",
        "uplink RSSI configuration adjustment",
    )
    assert related > unrelated
