from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx


@dataclass
class HTTPEnvClient:
    base_url: str = "http://localhost:7860"
    timeout_s: float = 30.0

    def _client(self) -> httpx.Client:
        return httpx.Client(base_url=self.base_url, timeout=self.timeout_s)

    def reset(self, task_id: str = "easy") -> Dict[str, Any]:
        with self._client() as c:
            r = c.post("/reset", json={"task_id": task_id})
            r.raise_for_status()
            return r.json()

    def step(self, query: str, task_id: str = "easy", explanation: str = "") -> Dict[str, Any]:
        with self._client() as c:
            r = c.post("/step", json={"query": query, "task_id": task_id, "explanation": explanation})
            r.raise_for_status()
            return r.json()

    def state(self, task_id: str = "easy") -> Dict[str, Any]:
        with self._client() as c:
            r = c.get("/state", params={"task_id": task_id})
            r.raise_for_status()
            return r.json()

    def health(self) -> Dict[str, Any]:
        with self._client() as c:
            r = c.get("/health")
            r.raise_for_status()
            return r.json()

