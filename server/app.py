from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from server.environment import SQLReviewEnvironment
from server.models import SQLAction
from server.tasks import TASKS

app = FastAPI(title="SQL Review Env", version="1.0.0")

envs = {task_id: SQLReviewEnvironment(task_id) for task_id in TASKS.keys()}


class ActionRequest(BaseModel):
    query: str = Field(..., description="Corrected SQL query")
    explanation: str = Field(default="", description="Optional explanation")
    task_id: str = Field(default="easy", description="Task id: easy|medium|hard")


@app.get("/")
def root():
    return {
        "name": "sql-review-env",
        "status": "ok",
        "endpoints": ["/health", "/docs", "/reset", "/step", "/state"],
    }


@app.post("/reset")
def reset(req: dict[str, Any] | None = None):
    task_id = (req or {}).get("task_id", "easy")
    env = envs.get(task_id, envs["easy"])
    obs = env.reset()
    return {"observation": obs.model_dump(), "reward": 0.0, "done": False, "info": {}}


@app.post("/step")
def step(req: ActionRequest):
    env = envs.get(req.task_id, envs["easy"])
    action = SQLAction(query=req.query, explanation=req.explanation)
    obs, reward, done, info = env.step(action)
    return {"observation": obs.model_dump(), "reward": reward, "done": done, "info": info}


@app.get("/state")
def state(task_id: str = "easy"):
    env = envs.get(task_id, envs["easy"])
    return env.state.model_dump()


@app.get("/health")
def health():
    return {"status": "ok"}

