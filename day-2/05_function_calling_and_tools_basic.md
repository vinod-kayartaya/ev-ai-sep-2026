# Function Calling and Custom Tools

## Step 1: Write a Simple Tool with `@tool`

```python
@tool
def get_pto_balance(employee_id: str) -> str:
    """Look up the remaining Paid Time Off (PTO) balance for an employee."""
    mock_db = {"EMP-101": 14.5, "EMP-102": 8.0}
    return f"Employee {employee_id.upper()} has {mock_db.get(employee_id.upper(), 0.0)} days of PTO."
```

---

## Step 2: Enforce Boundaries with Pydantic v2

```python
class BonusProposalSchema(BaseModel):
    employee_id: str = Field(description="Employee ID in format 'EMP-XXX'")
    bonus_pct: float = Field(description="Bonus %", ge=1.0, le=25.0)

@tool(args_schema=BonusProposalSchema)
def propose_bonus(employee_id: str, bonus_pct: float) -> str:
    """Submit an annual bonus proposal within policy limits (1% to 25%)."""
    return f"SUCCESS: Submitted {bonus_pct}% bonus for {employee_id}."
```

---

## Step 3: Build a Tool with `StructuredTool.from_function`

```python
def book_leave_function(employee_id: str, days: int, leave_type: str = "VACATION") -> str:
    return f"CONFIRMED: Booked {days} days of {leave_type} leave for {employee_id}."

book_leave_tool = StructuredTool.from_function(
    func=book_leave_function,
    name="book_leave",
    description="Book employee leave in the HR system with duration and type.",
)
```

---

## Step 4: Bind Tools and Execute the Handshake

```python
tools = [get_pto_balance, propose_bonus, book_leave_tool]
llm_with_tools = llm.bind_tools(tools)

# 1. User sends query
ai_msg = llm_with_tools.invoke("How much PTO does EMP-101 have left?")

# 2. Host runs tool using model's arguments
call = ai_msg.tool_calls[0]
output = get_pto_balance.invoke(call["args"])

# 3. Host passes result back with matching tool_call_id
tool_msg = ToolMessage(content=output, tool_call_id=call["id"])
final_answer = llm_with_tools.invoke([HumanMessage(content=query), ai_msg, tool_msg])
```

---
