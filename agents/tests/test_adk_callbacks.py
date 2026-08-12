from google.adk.models.llm_response import LlmResponse
from google.genai import types

from telco_local.adk_callbacks import serialize_function_calls


def test_serialize_function_calls_keeps_only_first_call():
    response = LlmResponse(
        content=types.Content(
            role="model",
            parts=[
                types.Part.from_function_call(name="first", args={}),
                types.Part.from_function_call(name="second", args={}),
            ],
        )
    )

    serialized = serialize_function_calls(
        callback_context=None,
        llm_response=response,
    )

    assert serialized is not None
    names = [
        part.function_call.name
        for part in serialized.content.parts
        if part.function_call
    ]
    assert names == ["first"]
    assert len(response.content.parts) == 2
