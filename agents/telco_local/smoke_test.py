"""Opt-in live DeepSeek + ADK tool-calling smoke test."""

import asyncio

from google.adk import Agent
from google.adk.runners import InMemoryRunner

from telco_local.model_provider import assert_deepseek_configured, build_model


async def local_health_check() -> dict:
    """Return local runtime health for the model to verify tool calling."""

    return {"status": "healthy", "runtime": "local-duckdb"}


async def run_smoke_test() -> None:
    assert_deepseek_configured()
    agent = Agent(
        name="deepseek_tool_smoke_test",
        model=build_model("incident_detector"),
        instruction=(
            "You must call local_health_check exactly once, then report its "
            "status without adding facts."
        ),
        tools=[local_health_check],
    )
    runner = InMemoryRunner(agent=agent)
    events = await runner.run_debug(
        "Run the local health check now.",
        quiet=False,
        verbose=False,
    )
    if not events:
        raise RuntimeError("DeepSeek smoke test returned no ADK events")
    print("DeepSeek + ADK smoke test completed.")


def main() -> None:
    asyncio.run(run_smoke_test())


if __name__ == "__main__":
    main()
