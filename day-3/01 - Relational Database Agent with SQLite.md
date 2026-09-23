# Relational Database Agent with SQLite

Enterprise HR and People Operations departments store core workforce records in relational databases—covering employee profiles, historical leave requests, salary bands, and open job requisitions.

Writing custom reporting queries for business questions (e.g., *"Which department has the highest average tenure?"* or *"List employees whose salary is below the midpoint of their band"*) usually requires SQL expertise.

A **Text-to-SQL Database Agent** translates natural language questions into executable SQL queries, inspects the schema dynamically, executes read-only queries, and synthesizes answers for business leaders.

## Architecture of a SQL Agent

A SQL agent uses dynamic schema introspection to discover database structure at runtime:

```text
Natural Language Question:
"Which department has the most approved leave requests this quarter?"
                        ↓
             SQL Agent (create_sql_agent)
                        ↓
     1. Inspect Schema: sql_db_list_tables
        Returns: employees, leave_requests, compensation_bands
                        ↓
     2. Inspect Columns: sql_db_schema
        Reads table DDL & foreign keys
                        ↓
     3. Generate SQL:
        SELECT e.department, COUNT(l.id) as total_leaves
        FROM employees e
        JOIN leave_requests l ON e.employee_id = l.employee_id
        WHERE l.status = 'Approved'
        GROUP BY e.department
        ORDER BY total_leaves DESC LIMIT 5;
                        ↓
     4. Execute SQL: sql_db_query
        Runs query against SQLite
                        ↓
     5. Synthesize Answer:
        "Engineering has the highest count with 24 approved leaves."
```

The agent discovers the table schemas automatically—no hardcoded SQL templates are required.

## Connecting to SQLite with `SQLDatabase`

LangChain's `SQLDatabase` wrapper encapsulates connection pooling, dialect handling, and metadata introspection:

```python
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent

# Connect to the HR relational database
db = SQLDatabase.from_uri(
    "sqlite:///hr_and_people_ops/day2/demo/data/people_operations.db",
    include_tables=["employees", "leave_requests", "compensation_bands", "job_requisitions"]
)

print("Available Tables:", db.get_usable_table_names())
```

## Initializing the SQL Agent

The agent is created using `create_sql_agent`:

```python
agent_executor = create_sql_agent(
    llm=llm,
    db=db,
    agent_type="openai-tools",
    verbose=True,
    top_k=10
)
```

The `top_k` parameter limits query result rows, preventing out-of-memory errors when querying large tables.

## Multi-Table Foreign Key JOINs

Real-world workforce analytics questions often span multiple tables:

```text
employees (id, department, title, salary)
     ├── Foreign Key (employee_id) ──→ leave_requests (id, category, days, status)
     └── Foreign Key (tier, dept)  ──→ compensation_bands (tier, min_salary, max_salary)
```

When asked: *"Find all employees whose base salary is below their band minimum,"* the agent automatically:
1. Discovers the join relationship between `employees.tier` and `compensation_bands.tier`.
2. Constructs an `INNER JOIN` query.
3. Filters rows where `employees.salary < compensation_bands.min_salary`.
4. Returns a formatted executive summary.

## Database Safety and Guardrails

Connecting LLMs to enterprise databases requires safety constraints:

1. **Read-Only Connections**: Ensure the database connection user has only `SELECT` permissions. DDL (`DROP`, `ALTER`) or DML (`INSERT`, `UPDATE`, `DELETE`) operations should be prohibited.
2. **Execution Timeout**: Limit query runtimes to prevent runaway table scans or accidental cartesian joins.
3. **Query Row Limits (`top_k`)**: Automatically append `LIMIT` clauses to avoid exhausting context windows.

## Summary: Key Takeaways for the Demo

```text
┌─────────────────────────────────────────────────────────────┐
│                 SQL Database Agent Features                 │
│                                                             │
│ • Introspection: Discovers tables & columns dynamically     │
│ • Multi-Table:   Generates complex SQL JOINs automatically  │
│ • Translation:   Converts plain business questions to SQL   │
│ • Safety:        Uses read-only queries with row limits     │
└─────────────────────────────────────────────────────────────┘
```

When observing the demo:
1. Watch how the agent first inspects table schemas before writing any SQL.
2. Notice how it generates multi-table JOINs across `employees` and `compensation_bands` to answer compensation equity questions.
