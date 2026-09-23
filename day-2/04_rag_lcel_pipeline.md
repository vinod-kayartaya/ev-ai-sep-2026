# Building a RAG Pipeline with LCEL

Retrieval-Augmented Generation (RAG) combines document retrieval with LLM-based generation. Instead of relying only on the model's internal knowledge, the application retrieves relevant information and provides it as context for generating the response.

## RAG Pipeline

A basic RAG workflow consists of four major stages:

```text id="x1s6xm"
User Question
      ↓
Retriever
      ↓
Relevant Documents
      ↓
Prompt + Context
      ↓
LLM
      ↓
Answer
```

The retriever identifies relevant document chunks, and those chunks are supplied to the LLM as context.

## Document Formatting

Retrieved documents need to be converted into a suitable textual representation before being included in a prompt.

A formatting step can:

- Combine multiple document chunks.
- Clearly separate individual chunks.
- Preserve source information.
- Produce a consistent context structure for the prompt.

This creates a clean boundary between retrieved knowledge and the user's question.

## RAG with LCEL

LCEL allows the retrieval and generation stages to be expressed as a declarative pipeline.

Conceptually:

```text id="b5r8x1"
                    ┌──→ Retriever → Format Documents ──→ Context
Question ───────────┤
                    └──→ Pass Through ─────────────────→ Question
                                      ↓
                                   Prompt
                                      ↓
                                     LLM
                                      ↓
                                Output Parser
```

The retrieved context and the original question are assembled into the prompt before being passed to the LLM.

## Grounded Answer Generation

**Grounded generation** means that the LLM is instructed to base its response on the retrieved context.

The retrieved documents become the application's source of information for that particular request. This reduces the need for the model to rely on information outside the supplied knowledge.

A grounded RAG system therefore establishes a clear relationship:

```text id="z2q3a8"
Retrieved Context
       ↓
     LLM
       ↓
Context-Based Answer
```

## Anti-Hallucination Boundaries

RAG does not automatically guarantee that an LLM will use only retrieved information. The prompt should explicitly establish boundaries around what the model is allowed to use.

A strict grounded prompt can instruct the model to:

- Use only the supplied context.
- Avoid speculation.
- Avoid extrapolating beyond the available information.
- State when the available documentation is insufficient.

This creates an explicit refusal boundary for questions that cannot be answered from the retrieved material.

## Complete RAG Architecture

The complete flow combines the concepts covered in the previous stages:

```text id="s7frqj"
Documents
    ↓
Chunking
    ↓
Embeddings
    ↓
Vector Store
    ↓
Retriever
    ↓
Relevant Chunks
    ↓
Document Formatting
    ↓
Grounded Prompt
    ↓
LLM
    ↓
Answer
```

LCEL provides a declarative way to connect these components into a single RAG workflow. This makes the flow explicit while keeping retrieval, formatting, prompting, generation, and output parsing as separate composable stages.
