import json
import re

from anthropic import AsyncAnthropic

from app.config import settings

OPUS_MODEL = "claude-opus-4-7"
SONNET_MODEL = "claude-sonnet-4-6"

SPEC_SYSTEM = (
    "You are an expert mobile app architect. Generate structured JSON specs from app ideas. "
    "Always respond with valid JSON only. No markdown fences, no explanation."
)


class ClaudeClient:
    def __init__(self) -> None:
        self._client_instance = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_spec(self, prompt: str, context: str, model: str = "opus") -> str:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        response = await self._client_instance.messages.create(
            model=model_id,
            max_tokens=4096,
            system=SPEC_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}"}],
        )
        return response.content[0].text

    async def generate_json(self, prompt: str, model: str = "opus") -> dict:
        text = await self.generate_spec(prompt, "", model=model)
        text = text.strip()
        # strip markdown fences if present
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text.strip())
