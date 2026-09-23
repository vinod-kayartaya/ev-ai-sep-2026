# Output Parsers & Structured Data

LLMs normally generate **unstructured text**. While this is useful for conversations, applications often need information in a predictable structure that can be processed programmatically.

For example, an application may need to extract:

```text
Employee Name
Employee ID
Leave Type
Number of Days
Start Date
End Date
```

Output parsers and structured outputs provide ways to convert LLM responses into usable application data.

## Output Parsers

An **output parser** converts the model's response into a particular format that an application can work with.

Conceptually:

```text
LLM Response
     ↓
Output Parser
     ↓
Application Data
```

LangChain provides different output parsers for different requirements.

### StrOutputParser

`StrOutputParser` extracts the model's response as a plain string.

```text
LLM
 ↓
Text Response
 ↓
String
```

This is useful when the application simply needs generated text and does not require a specific data structure.

### JsonOutputParser

`JsonOutputParser` converts the model's response into JSON-compatible data.

For example:

```json
{
  "employee": "Marcus Chen",
  "days": 10,
  "start_date": "2026-10-05"
}
```

This provides a more structured representation that can be processed by application code.

However, generic JSON parsing does not by itself define all the rules that the data must satisfy.

## Structured Output

**Structured output** goes a step further by defining the expected structure of the model's response.

Instead of simply asking the model to produce JSON, an application can define a data model containing:

* Field names
* Data types
* Allowed values
* Validation rules
* Field descriptions

The model's output can then be mapped into that defined structure.

```text
Unstructured Text
       ↓
      LLM
       ↓
Structured Data
       ↓
Validation
       ↓
Application
```

## Pydantic Data Models

**Pydantic** provides a way to define structured, type-safe data models in Python.

A model can define fields and their types:

```python
class LeaveRequest(BaseModel):
    employee_name: str
    days_requested: float
    coverage_provided: bool
```

This establishes a clear data contract:

```text
employee_name       → string
days_requested      → number
coverage_provided   → boolean
```

The application can therefore work with the result as a Python object rather than manually processing raw text.

## Field Validation

Pydantic models can also define validation rules.

For example:

```python
days_requested: float = Field(
    ge=0.5,
    le=90.0
)
```

This specifies that the value must be between `0.5` and `90.0`.

Fields can also restrict values to a predefined set:

```python
leave_type: Literal[
    "VACATION_PTO",
    "SICK_LEAVE",
    "PARENTAL_LEAVE"
]
```

This prevents arbitrary values from being accepted for that field.

## Type-Safe LLM Output

With structured output, the application can work with a defined Python type:

```text
LLM
 ↓
Structured Output
 ↓
Pydantic Model
 ↓
Validated Python Object
```

This is particularly useful when LLM-generated information is going to be passed to other application components, stored in a database, or used in an automated workflow.

## Structured Data vs. Unstructured Text

The difference can be summarized as:

```text
Unstructured Output

"Marcus Chen wants to take two weeks
of vacation starting October 5."

                ↓

Difficult to process reliably
```

versus:

```text
Structured Output

{
    employee_name: "Marcus Chen",
    leave_type: "VACATION_PTO",
    days_requested: 10,
    start_date: "2026-10-05"
}

                ↓

Easy for application code to process
```

## Key Concepts

```text
Output Parser
     ↓
Converts LLM output into a usable format

StrOutputParser
     ↓
Plain string

JsonOutputParser
     ↓
Generic JSON data

Pydantic Model
     ↓
Defined fields + types + validation

Structured Output
     ↓
LLM response mapped to the defined data model
```

The combination of **LLMs, structured outputs, and Pydantic validation** allows unstructured natural-language input to be transformed into predictable, type-safe application data.
