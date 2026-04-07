import asyncio
import os
import sys
from typing import List
import httpx
from openai import OpenAI

from server.tasks import TASKS

# ── Config ────────────────────────────────────────────────────────
API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
HF_TOKEN     = os.environ.get("HF_TOKEN", "")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")
ENV_URL      = os.environ.get("ENV_URL", "http://localhost:7860")

BENCHMARK         = "sql-review-env"
MAX_STEPS         = 10
MAX_TOTAL_REWARD  = 10.0
SUCCESS_THRESHOLD = 0.7

# ── Logging (exact bracket format required) ───────────────────────
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)
    sys.stdout.flush()

def log_step(step, action, reward, done, error=None):
    err_part = f" error={error}" if error else ""
    print(f"[STEP] step={step} action={repr(str(action))[:120]} reward={reward} done={done}{err_part}", flush=True)
    sys.stdout.flush()

def log_end(success, steps, score, rewards):
    print(f"[END] success={success} steps={steps} score={round(score,4)} rewards={rewards}", flush=True)
    sys.stdout.flush()

# ── Smart prompt — gives model everything it needs ────────────────
def build_prompt(obs: dict, step: int, last_reward: float, history: List[str], max_steps: int) -> str:
    hint_text = f"\n💡 Hint: {obs.get('hint')}" if obs.get("hint") else ""
    history_text = "\n".join(history[-4:]) if history else "None yet"

    return f"""You are an expert SQL developer fixing broken SQL queries.

TASK: {obs.get('task_description', '')}

BROKEN QUERY TO FIX:
{obs.get('broken_query', '')}

FEEDBACK FROM LAST ATTEMPT:
{obs.get('feedback', 'No feedback yet — this is your first attempt.')}

CURRENT SCORE: {obs.get('score', 0.0)} / 1.0
LAST REWARD: {last_reward}
STEP: {step} of {max_steps}{hint_text}

PREVIOUS ATTEMPTS:
{history_text}

INSTRUCTIONS:
- Return ONLY the corrected SQL query
- No markdown, no backticks, no explanations
- Fix ALL syntax errors (typos in keywords, missing clauses, wrong ORDER)
- Common fixes: SELCT→SELECT, FORM→FROM, WHER→WHERE, GROUP BY not GROUP, ORDER BY not ORDER
- If score < 0.3: focus on fixing keyword typos first
- If score >= 0.3: focus on fixing logic and columns

CORRECTED SQL:"""


def get_model_action(client, obs: dict, step: int, last_reward: float, history: List[str], max_steps: int) -> str:
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert SQL developer. "
                        "You ONLY output raw SQL queries. "
                        "Never use markdown, never explain, never add backticks. "
                        "Just the SQL."
                    )
                },
                {
                    "role": "user",
                    "content": build_prompt(obs, step, last_reward, history, max_steps)
                }
            ],
            max_tokens=400,
            temperature=0.0,  # deterministic = reproducible scores
        )
        raw = (resp.choices[0].message.content or "").strip()
        # Strip accidental markdown backticks
        raw = raw.replace("```sql", "").replace("```", "").strip()
        return raw
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}", flush=True)
        # Fallback: return the broken query as-is so episode doesn't crash
        return obs.get("broken_query", "SELECT 1")


# ── Run one task ──────────────────────────────────────────────────
async def run_task(task_id: str) -> float:
    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)
    http   = httpx.Client(base_url=ENV_URL, timeout=60)

    task_max = int(TASKS.get(task_id, TASKS["easy"]).get("max_steps", MAX_STEPS))

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score   = 0.0
    success = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        reset_resp = http.post("/reset", json={"task_id": task_id})
        reset_resp.raise_for_status()
        result      = reset_resp.json()
        obs         = result["observation"]
        last_reward = 0.0

        for step in range(1, task_max + 1):
            if result.get("done"):
                break

            # Get action from LLM
            action = get_model_action(client, obs, step, last_reward, history, task_max)

            # Step the environment
            step_resp = http.post("/step", json={
                "task_id":     task_id,
                "query":       action,
                "explanation": ""
            })
            step_resp.raise_for_status()

            result      = step_resp.json()
            obs         = result["observation"]
            reward      = float(result.get("reward", 0.0))
            done        = bool(result.get("done", False))

            rewards.append(reward)
            steps_taken = step
            last_reward = reward

            log_step(step=step, action=action, reward=reward, done=done)
            history.append(
                f"Step {step}: submitted '{str(action)[:60]}' → reward={reward:.2f}, score={obs.get('score',0)}"
            )

            if done:
                break

        # Final score clamped to [0, 1]
        score   = sum(rewards) / MAX_TOTAL_REWARD
        # Strictly between 0 and 1
        score   = round(min(max(score, 0.05), 0.95), 4)
        success = score >= SUCCESS_THRESHOLD

    except Exception as e:
        print(f"[ERROR] task={task_id} exception={str(e)}", flush=True)
        log_step(step=steps_taken, action="", reward=0.0, done=True, error=str(e))

    finally:
        try:
            http.close()
        except Exception:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ── Main ──────────────────────────────────────────────────────────
async def main():
    print(f"[INFO] Starting SQL Review Env baseline", flush=True)
    print(f"[INFO] ENV_URL={ENV_URL} MODEL={MODEL_NAME}", flush=True)

    total = 0.0
    for task_id in ["easy", "medium", "hard"]:
        s = await run_task(task_id)
        total += s
        print(f"[INFO] {task_id} final score: {s:.3f}", flush=True)

    print(f"[INFO] Overall average: {total/3:.3f}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
