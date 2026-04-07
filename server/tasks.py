# server/tasks.py — hardened grader + normalization
import sqlite3
import re
from typing import Tuple

TASKS = {
    "easy": {
        "description": (
            "Fix the SQL query to retrieve all employees with salary greater than 50000. "
            "Table: employees(id, name, salary, department, dept_id)"
        ),
        "broken_query": "SELCT * FORM employees WHER salary > 50000",
        "solution_keywords": ["select", "from", "employees", "where", "salary"],
        "expected_columns": ["id", "name", "salary", "department"],
        "difficulty": "easy",
        "max_steps": 10,
    },
    "medium": {
        "description": (
            "Fix this SQL query to return average salary per department, "
            "only for departments with more than 2 employees. "
            "Table: employees(id, name, salary, department, dept_id)"
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
            "Tables: employees(id, name, salary, department, dept_id), departments(id, dept_name)"
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
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("CREATE TABLE departments (id INTEGER PRIMARY KEY, dept_name TEXT)")
    cur.execute("""
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT, salary REAL,
            department TEXT,
            dept_id INTEGER
        )
    """)
    cur.executemany("INSERT INTO departments VALUES (?,?)", [
        (1, "Engineering"), (2, "Marketing"), (3, "HR")
    ])
    cur.executemany("INSERT INTO employees VALUES (?,?,?,?,?)", [
        (1, "Alice",  90000, "Engineering", 1),
        (2, "Bob",    55000, "Engineering", 1),
        (3, "Carol",  45000, "Marketing",   2),
        (4, "Dave",  120000, "Engineering", 1),
        (5, "Eve",    48000, "HR",          3),
        (6, "Frank",  80000, "Marketing",   2),
        (7, "Grace",  95000, "Marketing",   2),
    ])
    conn.commit()
    return conn


def normalize_query(query: str) -> str:
    """Clean up query for comparison — remove extra whitespace."""
    query = (query or "").strip()
    # Remove markdown backticks if model accidentally adds them
    query = re.sub(r"```sql|```", "", query, flags=re.IGNORECASE).strip()
    # Collapse multiple spaces
    query = re.sub(r"\s+", " ", query)
    # Remove trailing semicolon
    query = query.rstrip(";").strip()
    return query


def grade_query(task_id: str, submitted_query: str) -> Tuple[float, str]:
    """
    Grade submitted SQL. Returns (score 0.0-1.0, feedback string).
    Components:
      - Syntax valid (runs without error): 0.3
      - Returns rows (non-empty result):   0.2
      - Keyword coverage:                  0.3
      - Correct columns in result:         0.2
    """
    task = TASKS[task_id]
    score = 0.0
    feedback_parts = []

    query = normalize_query(submitted_query)

    if not query:
        return 0.0, "❌ Empty query submitted."

    conn = setup_test_db()

    # 1. Syntax check (0.3)
    try:
        cursor = conn.execute(query)
        result = cursor.fetchall()
        score += 0.3
        feedback_parts.append(f"✅ Query runs without errors (+0.3)")
    except Exception as e:
        feedback_parts.append(f"❌ Syntax error: {e} (+0.0)")
        conn.close()
        return round(score, 2), "\n".join(feedback_parts)

    # 2. Non-empty result (0.2)
    if len(result) > 0:
        score += 0.2
        feedback_parts.append(f"✅ Returns {len(result)} rows (+0.2)")
    else:
        feedback_parts.append("⚠️ Query returns 0 rows — check WHERE clause (+0.0)")

    # 3. Keyword coverage (0.3)
    query_lower = query.lower()
    required = task["solution_keywords"]
    matched = sum(1 for kw in required if kw in query_lower)
    keyword_score = round((matched / len(required)) * 0.3, 3)
    score += keyword_score
    feedback_parts.append(f"📝 Keywords: {matched}/{len(required)} matched (+{keyword_score:.2f})")

    # 4. Column structure (0.2)
    if result:
        try:
            desc = cursor.description
            col_names = [d[0].lower() for d in desc if d and d[0]]
            expected = [c.lower() for c in task["expected_columns"]]
            col_match = all(ec in col_names for ec in expected)
            if col_match:
                score += 0.2
                feedback_parts.append(f"✅ Expected columns found (+0.2)")
            else:
                feedback_parts.append(
                    f"⚠️ Missing columns. Got: {col_names}, Need: {expected} (+0.0)"
                )
        except Exception:
            feedback_parts.append("⚠️ Could not verify columns (+0.0)")

    conn.close()

    final_score = round(min(score, 1.0), 2)
    return final_score, "\n".join(feedback_parts)
