import asyncio
import json
from collections import defaultdict


class SSEManager:
    """Holds per-run async queues for SSE streaming."""

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue]] = defaultdict(list)

    def subscribe(self, run_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._queues[run_id].append(q)
        return q

    def unsubscribe(self, run_id: str, q: asyncio.Queue) -> None:
        try:
            self._queues[run_id].remove(q)
        except (ValueError, KeyError):
            pass

    async def emit(self, run_id: str, stage: str, message: str) -> None:
        data = json.dumps({"stage": stage, "message": message})
        for q in list(self._queues.get(run_id, [])):
            await q.put(data)

    async def emit_done(self, run_id: str, final_status: str) -> None:
        data = json.dumps({"stage": "done", "message": final_status, "done": True,
                           "final_status": final_status})
        for q in list(self._queues.get(run_id, [])):
            await q.put(data)
            await q.put(None)  # sentinel to close stream


sse_manager = SSEManager()
