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

FILE_GEN_SYSTEM = (
    "You are an expert full-stack developer specialising in Expo (React Native) and FastAPI. "
    "Generate complete, production-quality source files. "
    "Respond with the raw file content only — no markdown fences, no explanation, no commentary. "
    "Use the exact library versions provided. Follow the patterns provided exactly."
)

BLUEPRINT_SYSTEM = (
    "You are an expert mobile app architect. Generate architecture blueprints as JSON. "
    "Always respond with valid JSON only. No markdown fences, no explanation."
)


class ClaudeClient:
    def __init__(self) -> None:
        self._client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def generate_spec(self, prompt: str, context: str = "", model: str = "opus") -> str:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=4096,
            system=SPEC_SYSTEM,
            messages=[{"role": "user", "content": f"{context}\n\n{prompt}".strip()}],
        )
        return response.content[0].text

    async def generate_json(self, prompt: str, model: str = "opus", system: str | None = None) -> dict:
        model_id = OPUS_MODEL if model == "opus" else SONNET_MODEL
        sys = system or SPEC_SYSTEM
        response = await self._client.messages.create(
            model=model_id,
            max_tokens=8192,
            system=sys,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
        return json.loads(text.strip())

    async def generate_file(self, prompt: str) -> str:
        """Generate a source file. Returns raw file content."""
        response = await self._client.messages.create(
            model=SONNET_MODEL,
            max_tokens=8192,
            system=FILE_GEN_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        # Strip any accidental markdown fences
        text = re.sub(r"^```\w*\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)
        return text
