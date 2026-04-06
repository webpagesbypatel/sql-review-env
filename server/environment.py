from __future__ import annotations

import uuid
from typing import Any, Tuple

from server.models import SQLAction, SQLObservation, SQLState
from server.tasks import TASKS, grade_query


class SQLReviewEnvironment:
    """
    SQL Query Review Environment.

    The agent receives a broken SQL query and must submit a corrected query.
    """

    def __init__(self, task_id: str = "easy"):
        if task_id not in TASKS:
            task_id = "easy"
        self.task_id = task_id
        self._state = SQLState()
        self._best_score = 0.0

    def reset(self) -> SQLObservation:
        task = TASKS[self.task_id]
        self._state = SQLState(
            episode_id=str(uuid.uuid4()),
            task_id=self.task_id,
            current_step=0,
            max_steps=int(task.get("max_steps", 10)),
            best_score=0.0,
            attempts=[],
        )
        self._best_score = 0.0
        return SQLObservation(
            task_description=task["description"],
            broken_query=task["broken_query"],
            feedback="New episode started. Fix the SQL query above.",
            score=0.0,
            hint=None,
        )

    def step(self, action: SQLAction) -> Tuple[SQLObservation, float, bool, dict[str, Any]]:
        self._state.current_step += 1
        task = TASKS[self.task_id]

        score, feedback = grade_query(self.task_id, action.query)

        improvement = max(0.0, score - self._best_score)
        self._best_score = max(self._best_score, score)
        self._state.best_score = self._best_score
        self._state.attempts.append(action.query)

        if len(self._state.attempts) >= 2 and self._state.attempts[-1] == self._state.attempts[-2]:
            score = max(0.0, score - 0.1)
            feedback += "\n⚠️ Penalty: identical submission repeated (-0.1)"

        reward = float(score + (improvement * 0.1))
        done = bool(score >= 1.0 or self._state.current_step >= self._state.max_steps)

        hint = None
        if score < 0.3 and self._state.current_step >= 3:
            keywords = task["solution_keywords"]
            hint = f"Hint: Make sure your query uses these keywords: {', '.join(keywords[:3])}"

        obs = SQLObservation(
            task_description=task["description"],
            broken_query=task["broken_query"],
            feedback=feedback,
            score=float(score),
            hint=hint,
        )
        return obs, reward, done, {"step": self._state.current_step, "episode_id": self._state.episode_id}

    @property
    def state(self) -> SQLState:
        return self._state

