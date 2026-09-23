## Introduction to LangChain

**LangChain** is an open-source framework for building applications powered by **Large Language Models (LLMs)** such as GPT, Claude, Gemini, and others.

The key idea is that an LLM by itself mainly **generates text**. LangChain provides the building blocks needed to turn an LLM into an application that can **retrieve information, call tools, maintain context, produce structured output, and perform multi-step tasks**.

### Why LangChain?

Consider a simple LLM application:

```text
User → LLM → Response
```

A real-world AI application often looks more like:

```text
                  ┌── Vector Database
                  │
User → Application → LLM → Tools/APIs
                  │
                  ├── Conversation History
                  │
                  └── Structured Output
```

LangChain provides abstractions for connecting these components.

### Important LangChain concepts

| Concept                      | Purpose                                      |
| ---------------------------- | -------------------------------------------- |
| **LLM / Chat Model**         | Interact with an AI model                    |
| **Prompt Templates**         | Dynamically construct prompts                |
| **Output Parsers**           | Convert model output into usable formats     |
| **Runnables / LCEL**         | Compose components into pipelines            |
| **Chains**                   | Combine multiple operations into workflows   |
| **Embeddings**               | Convert text into numerical vectors          |
| **Vector Stores**            | Store and search embeddings                  |
| **Retrievers**               | Retrieve relevant documents                  |
| **RAG**                      | Give the LLM relevant external knowledge     |
| **Tools**                    | Allow an LLM to perform actions              |
| **Tool Calling**             | Allow the model to request specific tools    |
| **Agents**                   | Let an LLM decide which tools/actions to use |
| **Memory / Message History** | Maintain conversational context              |
| **Structured Output**        | Get predictable JSON/Pydantic-style results  |

### A simple LangChain pipeline

For example, you can create:

```text
User Question
      ↓
Prompt Template
      ↓
Chat Model
      ↓
Output Parser
      ↓
Final Answer
```

In LangChain's **LCEL (LangChain Expression Language)**, this can be expressed very concisely:

```python
chain = prompt | llm | parser

result = chain.invoke({
    "question": "What is LangChain?"
})
```

The `|` operator connects the components into a **Runnable pipeline**.

### LangChain and RAG

One of LangChain's most common applications is **Retrieval-Augmented Generation (RAG)**:

```text
                Documents
                    ↓
              Text Splitting
                    ↓
                Embeddings
                    ↓
              Vector Store
                    ↓
User Question → Retriever
                    ↓
              Relevant Docs
                    ↓
                  LLM
                    ↓
                 Answer
```

This allows an application to answer questions using **your own documents or data**, rather than relying only on the knowledge contained in the LLM.

### LangChain vs LangGraph

A useful distinction is:

**LangChain** → building blocks and abstractions for LLM applications.

**LangGraph** → orchestration framework for building **stateful, multi-step, agentic workflows** where execution can branch, loop, pause, resume, and involve multiple agents.

So you can think of the ecosystem roughly as:

```text
                    AI Application
                         │
              ┌──────────┴──────────┐
              │                     │
          LangChain              LangGraph
              │                     │
     LLM application          Stateful workflows
     building blocks          Agents / multi-agent
     RAG / tools              Human-in-the-loop
     prompts / parsers        loops / branching
```

In short, **LangChain provides the components for connecting LLMs to application logic, data, and tools**, while LangGraph provides a more powerful execution model for complex agentic workflows.

