# LCEL Chains & Runnables

LangChain Expression Language (LCEL) provides a declarative way to build LLM workflows by composing individual operations into a pipeline. Instead of manually controlling each step, LCEL allows components to be connected using the pipe (`|`) operator.

## LCEL Pipe Composition

The pipe operator connects the output of one runnable to the input of the next:

```text
Input → Prompt → LLM → Output Parser
```

Each component performs one responsibility, and the result flows automatically to the next component. This makes LLM workflows easier to read, compose, and maintain.

## Runnables

A **Runnable** is a component that can receive an input and produce an output. Prompts, LLMs, output parsers, and custom processing functions can all participate in an LCEL pipeline.

Common runnable types include:

- **RunnablePassthrough** — passes the input through without changing it.
- **RunnableLambda** — wraps a Python function so it can be used as part of an LCEL pipeline.
- **RunnableParallel** — executes multiple runnable branches using the same input.

## RunnableLambda

`RunnableLambda` allows ordinary Python functions to become part of an LCEL pipeline.

This is useful for deterministic processing such as:

- Cleaning or transforming input data
- Normalizing values
- Adding metadata
- Applying business rules
- Preparing data before it reaches an LLM

It provides a bridge between conventional Python logic and declarative LCEL pipelines.

## RunnableParallel

`RunnableParallel` allows multiple independent operations to execute concurrently using the same input.

Conceptually:

```text
                 ┌──→ Chain A ──→ Result A
Input ───────────┤
                 └──→ Chain B ──→ Result B
```

The results are collected into a structured output, with each branch identified by its corresponding key.

Parallel execution is useful when several independent LLM operations need to be performed on the same input.

## RunnablePassthrough

`RunnablePassthrough` forwards the original input unchanged. It is useful when the original data needs to be preserved while other processing happens alongside it.

This makes it possible to combine original input with results produced by other branches.

## Declarative Pipeline Composition

LCEL becomes particularly powerful when these runnables are combined into a single pipeline:

```text
Input
  ↓
Pre-processing
  ↓
Parallel Processing
  ├──→ Chain A
  └──→ Chain B
  ↓
Combined Results
```

This approach separates individual responsibilities while allowing them to form a complete workflow. LCEL therefore provides a consistent abstraction for building sequential, parallel, and custom processing pipelines around LLM applications.
