from __future__ import annotations

import asyncio
import json
import os
from typing import List

import httpx
from openai import OpenAI


API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
API_KEY = os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", ""))
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o-mini")
ENV_URL = os.environ.get("ENV_URL", "http://localhost:7860")

BENCHMARK = "sql-review-env"
MAX_STEPS = int(os.environ.get("MAX_STEPS", "10"))
MAX_TOTAL_REWARD = float(os.environ.get("MAX_TOTAL_REWARD", "10.0"))
SUCCESS_THRESHOLD = float(os.environ.get("SUCCESS_THRESHOLD", "0.7"))


def log_start(task, env, model):
    print(json.dumps({"type": "START", "task": task, "env": env, "model": model}), flush=True)


def log_step(step, action, reward, done, error):
    print(
        json.dumps(
            {
                "type": "STEP",
                "step": step,
                "action": action,
                "reward": reward,
                "done": done,
                "error": error,
            }
        ),
        flush=True,
    )


def log_end(success, steps, score, rewards):
    print(
        json.dumps({"type": "END", "success": success, "steps": steps, "score": score, "rewards": rewards}),
        flush=True,
    )


def get_model_action(client: OpenAI, obs: dict, last_reward: float, history: List[str]) -> str:
    system = (
        "You are an expert SQL developer. You will be given a broken SQL query. "
        "Your job is to fix it and return ONLY the corrected SQL query with no explanation, "
        "no markdown, no backticks. Just raw SQL."
    )
    history_text = "\n".join(history[-4:])
    user = (
        f"Task: {obs.get('task_description', '')}\n\n"
        f"Broken query:\n{obs.get('broken_query', '')}\n\n"
        f"Last feedback:\n{obs.get('feedback', '')}\n"
        f"Last reward: {last_reward}\n\n"
        f"Previous attempts:\n{history_text}\n\n"
        "Return the fixed SQL query only:"
    )

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        max_tokens=300,
        temperature=0.1,
    )
    return (resp.choices[0].message.content or "").strip()


async def run_task(task_id: str) -> float:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    http = httpx.Client(base_url=ENV_URL, timeout=30)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        resp = http.post("/reset", json={"task_id": task_id})
        resp.raise_for_status()
        result = resp.json()
        obs = result["observation"]
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.get("done"):
                break

            action = get_model_action(client, obs, last_reward, history)

            resp = http.post("/step", json={"query": action, "explanation": "", "task_id": task_id})
            resp.raise_for_status()
            result = resp.json()
            obs = result["observation"]
            reward = float(result.get("reward", 0.0))
            done = bool(result.get("done", False))

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action, reward=reward, done=done, error=None)
            history.append(f"Step {step}: reward={reward:.2f}")

            if done:
                break

        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD else 0.0
        score = float(min(max(score, 0.0), 1.0))
        success = score >= SUCCESS_THRESHOLD
        return score

    except Exception as e:
        log_step(step=steps_taken, action="", reward=0.0, done=True, error=str(e))
        return 0.0
    finally:
        http.close()
        # Note: END log must always print
        # If we returned early, compute score from rewards
        score = sum(rewards) / MAX_TOTAL_REWARD if MAX_TOTAL_REWARD else 0.0
        score = float(min(max(score, 0.0), 1.0))
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main():
    print("\n=== SQL Review Env Baseline ===", flush=True)
    for task_id in ["easy", "medium", "hard"]:
        s = await run_task(task_id)
        print(f"Task {task_id}: final score = {s:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())

