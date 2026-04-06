from __future__ import annotations

import sqlite3
from typing import Tuple

TASKS = {
    "easy": {
        "description": (
            "Fix the SQL query to retrieve all employees with salary > 50000. "
            "The table is called 'employees' with columns: id, name, salary, department."
        ),
        "broken_query": "SELCT * FORM employees WHER salary > 50000",
        "solution_keywords": ["select", "from", "employees", "where", "salary", ">", "50000"],
        "expected_columns": ["id", "name", "salary", "department"],
        "difficulty": "easy",
        "max_steps": 10,
    },
    "medium": {
        "description": (
            "Fix this SQL query that should return the average salary per department, "
            "but only for departments with more than 2 employees. "
            "Table: employees(id, name, salary, department)"
        ),
        "broken_query": (
            "SELECT department, AVG(salary) "
            "FROM employees "
            "GROUP department "
            "HAVING COUNT(*) > 2"
        ),
        "solution_keywords": ["select", "avg", "from", "employees", "group by", "having", "count"],
        "expected_columns": ["department"],
        "difficulty": "medium",
        "max_steps": 10,
    },
    "hard": {
        "description": (
            "Fix this SQL query to find employees who earn more than the average salary "
            "of their own department, sorted by salary descending. "
            "Tables: employees(id, name, salary, dept_id), departments(id, dept_name)"
        ),
        "broken_query": (
            "SELECT e.name, e.salary, d.dept_name "
            "FROM employees e "
            "JOIN departments d ON e.dept_id = d.id "
            "WHERE e.salary > (SELECT AVG(salary) FROM employees WHERE dept_id = e.dept_id) "
            "ORDER salary DESC"
        ),
        "solution_keywords": ["select", "from", "join", "where", "avg", "order by", "desc"],
        "expected_columns": ["name", "salary"],
        "difficulty": "hard",
        "max_steps": 15,
    },
}


def setup_test_db() -> sqlite3.Connection:
    """Create an in-memory SQLite DB with deterministic test data."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY, dept_name TEXT)")
    cur.execute(
        """
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT,
            salary REAL,
            department TEXT,
            dept_id INTEGER
        )
        """
    )

    cur.executemany(
        "INSERT INTO departments VALUES (?, ?)",
        [(1, "Engineering"), (2, "Marketing"), (3, "HR")],
    )
    cur.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?, ?)",
        [
            (1, "Alice", 90000, "Engineering", 1),
            (2, "Bob", 55000, "Engineering", 1),
            (3, "Carol", 45000, "Marketing", 2),
            (4, "Dave", 120000, "Engineering", 1),
            (5, "Eve", 48000, "HR", 3),
            (6, "Frank", 80000, "Marketing", 2),
            (7, "Grace", 95000, "Marketing", 2),
        ],
    )
    conn.commit()
    return conn


def grade_query(task_id: str, submitted_query: str) -> Tuple[float, str]:
    """
    Grade a submitted SQL query. Returns (score 0.0–1.0, feedback string).

    Scoring breakdown:
      - Syntax valid (runs without error): +0.3
      - Returns rows / non-empty result: +0.2
      - Contains required keywords: +0.3
      - Returns expected column structure: +0.2
    """
    task = TASKS[task_id]
    score = 0.0
    feedback_parts: list[str] = []
    query = (submitted_query or "").strip().rstrip(";")

    if not query:
        return 0.0, "❌ Empty query submitted (+0.0)"

    conn = setup_test_db()
    try:
        cursor = conn.execute(query)
        rows = cursor.fetchall()
        description = cursor.description
        score += 0.3
        feedback_parts.append("✅ Query runs without syntax errors (+0.3)")
    except Exception as e:
        conn.close()
        feedback_parts.append(f"❌ Syntax/runtime error: {e} (+0.0)")
        return round(score, 2), "\n".join(feedback_parts)

    if len(rows) > 0:
        score += 0.2
        feedback_parts.append(f"✅ Query returns {len(rows)} rows (+0.2)")
    else:
        feedback_parts.append("⚠️ Query returns 0 rows (+0.0)")

    query_lower = query.lower()
    required = task["solution_keywords"]
    matched = sum(1 for kw in required if kw in query_lower)
    keyword_score = round((matched / len(required)) * 0.3, 3)
    score += keyword_score
    feedback_parts.append(f"📝 Keywords matched: {matched}/{len(required)} (+{keyword_score:.2f})")

    if description is not None:
        col_names = [d[0].lower() for d in description if d and d[0]]
        expected = [c.lower() for c in task["expected_columns"]]
        if all(ec in col_names for ec in expected):
            score += 0.2
            feedback_parts.append("✅ Result contains expected columns (+0.2)")
        else:
            feedback_parts.append(
                f"⚠️ Missing expected columns. Got: {col_names}, Expected: {expected} (+0.0)"
            )

    conn.close()
    return round(min(score, 1.0), 2), "\n".join(feedback_parts)

