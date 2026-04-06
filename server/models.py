from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class Action(BaseModel):
    """Action schema base type."""


class Observation(BaseModel):
    """Observation schema base type."""


class State(BaseModel):
    """State schema base type."""


class SQLAction(Action):
    """Agent submits a corrected SQL query."""

    query: str = Field(..., description="The corrected SQL query")
    explanation: str = Field(default="", description="Optional explanation of the fix")


class SQLObservation(Observation):
    """What the agent sees after each step."""

    task_description: str
    broken_query: str
    feedback: str
    score: float = 0.0
    hint: Optional[str] = None


class SQLState(State):
    """Internal episode state."""

    episode_id: str = ""
    task_id: str = "easy"
    current_step: int = 0
    max_steps: int = 10
    best_score: float = 0.0
    attempts: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)

