# Prompt Templates & Few-Shot Prompting

Prompt engineering involves designing the instructions and input provided to an LLM so that it produces useful and consistent results.

When applications repeatedly use similar prompts, **prompt templates** provide a structured way to create prompts dynamically.

## ChatPromptTemplate

LangChain provides `ChatPromptTemplate` for defining reusable chat prompts.

A template can contain both fixed instructions and variables:

```python
ChatPromptTemplate.from_messages([
    ("system", "You are an assistant for {company_name}."),
    ("human", "Employee: {employee_name}\n"
              "Department: {department}\n"
              "Inquiry: {inquiry_text}")
])
```

The template defines the structure of the prompt while leaving certain values as variables.

## Variable Substitution

Variables inside a prompt are represented using curly braces:

```text
{company_name}
{employee_name}
{department}
{inquiry_text}
```

Values can be supplied when the template is formatted:

```python
template.format_messages(
    company_name="Acme Technologies",
    employee_name="Jordan",
    department="Engineering",
    inquiry_text="I need information about parental leave."
)
```

The template is converted into actual messages with the supplied values.

Conceptually:

```text
Prompt Template
      +
Variable Values
      ↓
Formatted Messages
      ↓
LLM
```

This makes the same prompt structure reusable with different inputs.

## Role-Based Prompting

Chat prompts can assign different roles to messages, such as:

```text
system
human
ai
```

A **system** message provides instructions and context.

A **human** message provides the user's input.

An **AI** message represents an assistant response and can also be used when providing previous examples to the model.

Using explicit roles makes the structure of a conversation clear to the model.

## Few-Shot Prompting

**Few-shot prompting** provides a model with a small number of examples showing how an input should be handled.

The basic pattern is:

```text
Instruction

Input 1
Output 1

Input 2
Output 2

New Input
Output ?
```

The model uses the examples as context to infer the expected behavior and output pattern.

For example:

```text
Input:
My paycheck has not arrived.

Output:
CATEGORY: PAYROLL
URGENCY: HIGH

Input:
My laptop is not working.

Output:
CATEGORY: IT
URGENCY: MEDIUM

Input:
I need help with my benefits.

Output:
?
```

The previous input/output pairs provide context for processing the new input.

## In-Context Learning

Few-shot prompting is a form of **in-context learning**.

The model is not being retrained or fine-tuned. Instead, examples are included directly in the prompt for the current request.

```text
Examples
   ↓
Prompt Context
   ↓
LLM
   ↓
New Response
```

This makes it possible to guide classification, formatting, terminology, and response patterns without changing the underlying model.

## Structured Output Instructions

Prompt templates can also specify the expected format of the response.

For example:

```text
Classify the request into one category.

Provide:
CATEGORY
URGENCY
ASSIGNED_DESK
```

Combining clear instructions with examples can help produce more consistent outputs.

## Key Concepts

```text
Prompt Template
      ↓
Reusable prompt structure

Variable Substitution
      ↓
Dynamic values inserted into the template

Role-Based Prompting
      ↓
System / Human / AI message roles

Few-Shot Prompting
      ↓
Examples provided within the prompt

In-Context Learning
      ↓
Model follows patterns demonstrated in the context
```

These concepts provide the foundation for creating reusable, parameterized prompts and guiding LLM behavior through examples rather than model fine-tuning.
