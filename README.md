# SQL Review Env

An environment where an agent fixes broken SQL queries. The environment grades submissions deterministically by executing the submitted SQL against a fixed in-memory SQLite dataset.

## API

- `GET /health` → `{"status":"ok"}`
- `POST /reset` body: `{"task_id":"easy"|"medium"|"hard"}`
- `POST /step` body: `{"task_id":"easy"|"medium"|"hard","query":"...","explanation":""}`
- `GET /state?task_id=easy`

## Local run

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn server.app:app --host 0.0.0.0 --port 7860
```

Open `http://localhost:7860/docs`.

## Docker

```bash
docker build -t sql-review-env .
docker run -p 7860:7860 sql-review-env
```

## Baseline

Run (requires `OPENAI_API_KEY` or `HF_TOKEN`):

```bash
set ENV_URL=http://localhost:7860
python inference.py
```

