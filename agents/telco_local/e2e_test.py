"""Opt-in live Incident Detector -> RCA acceptance test."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Iterable

from google.adk.runners import InMemoryRunner

from incident_detector.agent import root_agent as incident_detector_agent
from root_cause_analysis.agent import root_agent as rca_agent
from telco_local.database import execute_query
from telco_local.model_provider import assert_deepseek_configured


def _function_calls(events: Iterable[object]) -> list[str]:
    names: list[str] = []
    for event in events:
        content = getattr(event, "content", None)
        for part in getattr(content, "parts", None) or []:
            function_call = getattr(part, "function_call", None)
            if function_call and function_call.name:
                names.append(function_call.name)
    return names


def _agent_text(events: Iterable[object], author: str | None = None) -> str:
    pieces: list[str] = []
    for event in events:
        if author is not None and getattr(event, "author", None) != author:
            continue
        content = getattr(event, "content", None)
        for part in getattr(content, "parts", None) or []:
            if getattr(part, "text", None) and not getattr(part, "thought", False):
                pieces.append(part.text)
    return "\n".join(pieces)


def _latest_incident_id() -> str:
    rows = execute_query(
        """
        SELECT incident_id
        FROM incidents
        ORDER BY created_at DESC, incident_id DESC
        LIMIT 1
        """
    )
    if not rows:
        raise RuntimeError("Incident Detector did not persist an incident")
    return str(rows[0].incident_id)


async def run_e2e_test() -> None:
    assert_deepseek_configured()

    detector_runner = InMemoryRunner(agent=incident_detector_agent)
    detector_events = await detector_runner.run_debug(
        [
            (
                "Find potential incidents using the tool. Show the number found "
                "and identify the first incident, then ask me to confirm creation."
            ),
            "I confirm. Create exactly the first incident you proposed.",
        ],
        quiet=True,
    )
    detector_calls = _function_calls(detector_events)
    required_detector_calls = {"get_potential_incidents", "create_new_incident"}
    if not required_detector_calls.issubset(detector_calls):
        raise RuntimeError(
            "Incident Detector did not complete its required tool calls: "
            f"{detector_calls}"
        )

    incident_id = _latest_incident_id()
    print(
        "Incident Detector completed: "
        f"incident_id={incident_id}, calls={detector_calls}"
    )

    rca_runner = InMemoryRunner(agent=rca_agent)
    rca_events = await rca_runner.run_debug(
        (
            f"Run the complete evidence-based RCA for incident {incident_id}. "
            "I authorize all read-only analysis steps. I explicitly decline every "
            "suggested simulated action, so do not ask about actions and do not "
            "execute any. I also explicitly decline saving or updating the report. "
            "These decisions must not stop the analysis: call every required "
            "specialist, call report_generator_agent, display the final report, "
            "and then finish without calling update_incident."
        ),
        quiet=True,
    )
    rca_calls = _function_calls(rca_events)
    required_rca_calls = {
        "get_incident_info",
        "processing_rules_retriever",
        "instruction_generator_agent",
        "update_severity_level",
        "external_documentation_retriever_agent",
        "internal_documentation_retriever_agent",
        "prior_incidents_search_agent",
        "report_generator_agent",
    }
    missing_rca_calls = required_rca_calls.difference(rca_calls)
    if missing_rca_calls:
        raise RuntimeError(
            "RCA did not complete all required stages; missing "
            f"{sorted(missing_rca_calls)}; calls={rca_calls}"
        )
    if "update_incident" in rca_calls:
        raise RuntimeError("RCA updated the incident without approval")

    report_text = _agent_text(rca_events)
    expected_sections = ["Incident 概述", "Root Cause Analysis", "严重程度", "建议措施"]
    if (
        not re.search(r"[\u4e00-\u9fff]", report_text)
        or sum(section in report_text for section in expected_sections) < 3
    ):
        raise RuntimeError("RCA report generator did not produce Chinese output")

    persisted = execute_query(
        """
        SELECT status, preliminary_analysis
        FROM incidents
        WHERE incident_id = ?
        """,
        [incident_id],
    )
    if not persisted or persisted[0].status != "NEW":
        raise RuntimeError("RCA changed the incident despite the no-save instruction")

    print(f"RCA completed without persistence: calls={rca_calls}")
    print("Chinese RCA report output verified.")
    print("DeepSeek Incident Detector -> RCA acceptance test completed.")


def main() -> None:
    asyncio.run(run_e2e_test())


if __name__ == "__main__":
    main()
