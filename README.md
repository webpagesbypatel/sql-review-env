
---
**SQL Review Env**

  - openenv
  - reinforcement-learning
  - sql
  - code-review
  - agent-evaluation
---

# 🛢️ SQL Review Environment

> An OpenEnv-compatible reinforcement learning environment where AI agents learn to identify and fix broken SQL queries — a real-world skill used daily by data engineers, analysts, and backend developers.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker)](https://docker.com)
[![HF Space](https://img.shields.io/badge/HuggingFace-Space-FFD21E?logo=huggingface)](https://huggingface.co)

---

## 🌍 What Is This?

The **SQL Review Environment** simulates a task that real humans do every day: reviewing and fixing broken SQL queries. A data engineer receives a malformed query, diagnoses what's wrong, and submits a corrected version.

This environment wraps that workflow into a fully standards-compliant **OpenEnv** interface — making it usable for:

- **RL training** — teach LLMs to fix SQL through trial and reward
- **Agent benchmarking** — evaluate how well a model understands SQL semantics
- **LLM evaluation** — measure code understanding and correction ability
- **Research** — study how agents learn structured formal languages

---

## 🎯 Why This Environment Matters

| Problem | How This Helps |
|---|---|
| LLMs hallucinate SQL | Deterministic grader catches wrong syntax immediately |
| Hard to evaluate SQL quality | 4-component reward gives fine-grained signal |
| No real-world SQL RL benchmarks | Fills a genuine gap in the OpenEnv ecosystem |
| Binary pass/fail rewards don't teach | Partial rewards guide the agent step by step |

SQL is one of the most widely used languages in the world — used by over 10 million developers. An agent that can reliably fix SQL has **immediate practical value** in data pipelines, code review tools, IDE assistants, and database management systems.

---

## 🧠 Environment Design

### How It Works

1. The agent receives a **broken SQL query** and a description of what it should do
2. The agent submits a **fixed query**
3. The environment **executes the query** against a real in-memory SQLite database
4. A **deterministic grader** scores the result across 4 dimensions
5. The agent gets **feedback + partial reward** and tries again
6. Episode ends when score reaches `1.0` or max steps are exhausted

### Reward Function (4-component, partial progress)

```
Score = syntax_valid (0.3)
      + returns_rows  (0.2)
      + keyword_match (0.3)
      + correct_cols  (0.2)
```

- **Not binary** — agent gets rewarded for partial fixes
- **Penalizes repetition** — submitting the same wrong query twice costs `-0.1`
- **Hints unlock** — after 3 failed steps, a keyword hint is provided
- **Improvement bonus** — agent gets extra reward for beating its own best score

This reward shape encourages the agent to iteratively improve rather than guess randomly.

---

## 📋 Tasks

### Task 1 — Easy 🟢
**Fix basic syntax errors in a simple SELECT query**

The broken query has typos in SQL keywords (`SELCT`, `FORM`, `WHER`). The agent must identify and correct all keyword misspellings.

- Expected difficulty for frontier models: **~0.95 score**
- Skills tested: SQL keyword recognition, basic syntax

### Task 2 — Medium 🟡
**Fix a GROUP BY query with aggregate filtering**

The broken query is missing `BY` in `GROUP BY` and has incorrect clause structure. The agent must fix the aggregation logic.

- Expected difficulty for frontier models: **~0.80 score**
- Skills tested: Aggregation, HAVING clause, GROUP BY syntax

### Task 3 — Hard 🔴
**Fix a correlated subquery with JOIN and ORDER BY**

The broken query has a missing `BY` in `ORDER BY` inside a complex multi-table JOIN with a correlated subquery. The agent must understand query context to fix it correctly.

- Expected difficulty for frontier models: **~0.65 score**
- Skills tested: JOINs, correlated subqueries, ORDER BY, multi-table reasoning

---

## 📐 Action & Observation Spaces

### Action Space
```json
{
  "query": "string — the corrected SQL query",
  "explanation": "string — optional reasoning (not graded)"
}
```

### Observation Space
```json
{
  "task_description": "string — what the query should do",
  "broken_query":     "string — the buggy SQL to fix",
  "feedback":         "string — detailed grader output from last step",
  "score":            "float  — current step score (0.0–1.0)",
  "hint":             "string — keyword hint (appears after 3 failed steps)"
}
```

### State
```json
{
  "task_id":      "string — easy | medium | hard",
  "current_step": "int    — steps taken this episode",
  "max_steps":    "int    — step limit (10 easy/medium, 15 hard)",
  "best_score":   "float  — highest score achieved this episode",
  "attempts":     "list   — history of submitted queries"
}
```

---

## 🔌 API Reference

| Method | Endpoint | Body | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| POST | `/reset` | `{"task_id": "easy"}` | Start new episode |
| POST | `/step` | `{"task_id": "easy", "query": "...", "explanation": ""}` | Submit a fix |
| GET | `/state` | `?task_id=easy` | Inspect current state |
| GET | `/docs` | — | Interactive Swagger UI |

---

## 🚀 Quick Start

### Option 1 — Run Locally (Python)
```bash
python -m venv .venv

# Windows
.\.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```
Open **http://localhost:7860/docs** for the interactive API explorer.

### Option 2 — Run with Docker
```bash
docker build -t sql-review-env .
docker run -p 7860:7860 sql-review-env
```

### Option 3 — Use the Live HF Space
```python
import httpx

BASE = "https://YOUR_USERNAME-sql-review-env.hf.space"

# Start episode
obs = httpx.post(f"{BASE}/reset", json={"task_id": "easy"}).json()
print(obs["observation"]["broken_query"])

# Submit a fix
result = httpx.post(f"{BASE}/step", json={
    "task_id": "easy",
    "query": "SELECT * FROM employees WHERE salary > 50000",
    "explanation": "Fixed typos in SELECT, FROM, WHERE"
}).json()
print(result["reward"])  # e.g. 1.0
```

---

## 📊 Baseline Results

Run the baseline inference script (requires API key):

```bash
# Set your API credentials
set OPENAI_API_KEY=sk-...        # Windows
export OPENAI_API_KEY=sk-...     # Mac/Linux

set ENV_URL=http://localhost:7860
python inference.py
```

| Task | Model | Avg Score | Steps to Solve |
|---|---|---|---|
| Easy | gpt-4o-mini | ~0.95 | 1–2 |
| Medium | gpt-4o-mini | ~0.80 | 2–4 |
| Hard | gpt-4o-mini | ~0.65 | 4–8 |

---

## 🏗️ Project Structure

```
sql-review-env/
├── server/
│   ├── __init__.py       # Package marker
│   ├── app.py            # FastAPI server + all endpoints
│   ├── environment.py    # Core RL environment logic
│   ├── models.py         # Pydantic Action/Observation/State models
│   └── tasks.py          # Task definitions + deterministic graders
├── inference.py          # Baseline agent script (OpenAI client)
├── openenv.yaml          # OpenEnv spec metadata
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## ✅ OpenEnv Compliance

| Requirement | Status |
|---|---|
| `reset()` returns clean initial observation | ✅ |
| `step()` returns observation, reward, done, info | ✅ |
| `state()` returns current episode metadata | ✅ |
| Typed Pydantic models for Action/Observation/State | ✅ |
| `openenv.yaml` metadata file | ✅ |
| 3+ tasks with difficulty progression | ✅ |
| Graders return scores in `0.0–1.0` range | ✅ |
| Deterministic and reproducible graders | ✅ |
| Partial reward signal (not just binary) | ✅ |
| Baseline `inference.py` with structured logs | ✅ |
| Dockerfile builds and runs | ✅ |
| Deploys to HF Space | ✅ |

---

## 🔬 Real-World Use Cases

- **IDE plugins** — auto-fix SQL as developers type
- **Data pipeline validation** — catch broken queries before production
- **LLM fine-tuning** — generate training data for SQL-repair models
- **Agent evaluation** — benchmark how well a model understands relational data
- **Education tools** — give students feedback on SQL assignments

---

## 📄 License

MIT License — free to use, modify, and build upon.
