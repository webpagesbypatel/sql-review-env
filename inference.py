import asyncio
import os
import json
from typing import List
from openai import OpenAI
import httpx

# ── MUST use these exact variable names ──────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:7860")

BENCHMARK         = "sql-review-env"
MAX_STEPS         = 10
MAX_TOTAL_REWARD  = 10.0
SUCCESS_THRESHOLD = 0.7

# ── EXACT log format — do not change field names ─────────────────
def log_start(task, env, model):
    print(json.dumps({"type": "START", "task": task, "env": env, "model": model}), flush=True)

def log_step(step, action, reward, done, error):
    print(json.dumps({"type": "STEP", "step": step, "action": action,
                      "reward": reward, "done": done, "error": error}), flush=True)

def log_end(success, steps, score, rewards):
    print(json.dumps({"type": "END", "success": success, "steps": steps,
                      "score": score, "rewards": rewards}), flush=True)

def get_model_action(client, obs, last_reward, history):
    system = (
        "You are an expert SQL developer. Fix the broken SQL query. "
        "Return ONLY the corrected SQL — no markdown, no backticks, no explanation."
    )
    user = (
        f"Task: {obs.get('task_description','')}\n\n"
        f"Broken query:\n{obs.get('broken_query','')}\n\n"
        f"Last feedback:\n{obs.get('feedback','')}\n"
        f"Last reward: {last_reward}\n\n"
        f"Previous attempts:\n{chr(10).join(history[-3:])}\n\n"
        "Return the fixed SQL only:"
    )
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "system", "content": system},
                  {"role": "user",   "content": user}],
        max_tokens=300,
        temperature=0.1,
    )
    return resp.choices[0].message.content.strip()

async def run_task(task_id: str):
    # ── Use HF_TOKEN as the API key (mandatory per instructions) ──
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    http   = httpx.Client(base_url=ENV_URL, timeout=30)

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score   = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        resp   = http.post("/reset", json={"task_id": task_id})
        result = resp.json()
        obs    = result["observation"]
        last_reward = 0.0

        for step in range(1, MAX_STEPS + 1):
            if result.get("done"):
                break

            action = get_model_action(client, obs, last_reward, history)

            resp   = http.post("/step", json={
                "task_id": task_id, "query": action, "explanation": ""
            })
            result     = resp.json()
            obs        = result["observation"]
            reward     = result.get("reward", 0.0)
            done       = result.get("done", False)

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action, reward=reward, done=done, error=None)
            history.append(f"Step {step}: reward={reward:.2f}")

            if done:
                break

        score   = sum(rewards) / MAX_TOTAL_REWARD
        score   = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        log_step(step=steps_taken, action="", reward=0.0, done=True, error=str(e))
    finally:
        http.close()
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score

async def main():
    for task_id in ["easy", "medium", "hard"]:
        await run_task(task_id)

if __name__ == "__main__":
    asyncio.run(main())
