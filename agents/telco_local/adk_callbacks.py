"""ADK callbacks that make stateful DeepSeek workflows deterministic."""

from __future__ import annotations

from google.adk.agents.context import Context
from google.adk.models.llm_response import LlmResponse


def serialize_function_calls(
    callback_context: Context,
    llm_response: LlmResponse,
) -> LlmResponse | None:
    """Keep one function call per model turn to avoid state dependency races."""

    del callback_context
    if not llm_response.content or not llm_response.content.parts:
        return None

    function_call_count = sum(
        bool(getattr(part, "function_call", None))
        for part in llm_response.content.parts
    )
    if function_call_count <= 1:
        return None

    serialized = llm_response.model_copy(deep=True)
    kept_parts = []
    function_call_kept = False
    for part in serialized.content.parts:
        if getattr(part, "function_call", None):
            if function_call_kept:
                continue
            function_call_kept = True
        kept_parts.append(part)
    serialized.content.parts = kept_parts
    return serialized
