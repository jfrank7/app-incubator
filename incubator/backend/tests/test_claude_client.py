import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.claude_client import ClaudeClient


def _make_mock_response(text: str) -> MagicMock:
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    mock_response.usage.input_tokens = 100
    mock_response.usage.output_tokens = 50
    return mock_response


@pytest.fixture
def client():
    return ClaudeClient()


@pytest.mark.asyncio
async def test_generate_spec_calls_opus(client):
    mock_response = _make_mock_response('{"app_name": "Test"}')

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        await client.generate_spec("build a tracker", "{}")

    mock_msgs.create.assert_called_once()
    assert mock_msgs.create.call_args.kwargs["model"] == "claude-opus-4-7"


@pytest.mark.asyncio
async def test_generate_json_parses_response(client):
    payload = {"app_name": "Tracker", "app_slug": "tracker"}
    mock_response = _make_mock_response(json.dumps(payload))

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["app_name"] == "Tracker"


@pytest.mark.asyncio
async def test_generate_json_strips_markdown_fences(client):
    payload = {"key": "value"}
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_response = _make_mock_response(fenced)

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_json("prompt")

    assert result["key"] == "value"


@pytest.mark.asyncio
async def test_generate_file_strips_markdown_fences(client):
    mock_response = _make_mock_response("```python\nprint('hello')\n```")

    with patch.object(client._client, "messages") as mock_msgs:
        mock_msgs.create = AsyncMock(return_value=mock_response)
        result = await client.generate_file("generate a python file")

    assert result == "print('hello')"
