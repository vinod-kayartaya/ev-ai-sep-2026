# AI Customer Complaint Resolution CLI (LangGraph + Langfuse @observe)

An educational, AI-powered interactive command-line application that accepts customer complaints, classifies them into **Payment**, **Quality**, **Delivery**, or **Uncategorized** issues using [LangGraph](https://langchain-ai.github.io/langgraph/), routes them to specialized resolution nodes, and tracks the execution using Langfuse's **`@observe` decorator**.

---

## Architecture

```
                       ┌──────────────────────────────┐
                       │      Customer Complaint      │
                       └──────────────┬───────────────┘
                                      │
                                      ▼
                       ┌──────────────────────────────┐
                       │ @observe categorize_complaint│
                       └──────────────┬───────────────┘
                                      │ (Conditional Router)
         ┌───────────────────────┬────┴──────────────────┬───────────────────────┐
         │ (Payment)             │ (Quality)             │ (Delivery)            │ (Uncategorized)
         ▼                       ▼                       ▼                       ▼
┌──────────────────────┐┌──────────────────────┐┌──────────────────────┐┌───────────────────────────┐
│ @observe             ││ @observe             ││ @observe             ││ @observe                  │
│ handle_payment_issue ││ handle_quality_issue ││ handle_delivery_issue││ handle_uncategorized_issue│
└──────────┬───────────┘└──────────┬───────────┘└──────────┬───────────┘└─────────────┬─────────────┘
           │                       │                       │                          │
           └───────────────────────┴───────────────────────┴──────────────────────────┘
                                                       │
                                                       ▼
                                                   ┌───────┐
                                                   │  END  │
                                                   └───────┘
```

A visual diagram is generated and saved as [**`complaint_graph.png`**](file:///Users/vinod/Desktop/langfuse-sandbox/langchain-app/complaint_graph.png) in this directory.

---

## Node Responsibilities

1. **`categorize_complaint`**: Classifies inputs into `Payment`, `Quality`, `Delivery`, or `Uncategorized` using structured output (`ComplaintCategorySchema`).
2. **`handle_payment_issue`**: Crafts empathetic responses for double charges, billing discrepancies, and refund procedures.
3. **`handle_quality_issue`**: Crafts responses for broken/damaged items, wrong sizes/colors, and replacement/return workflows.
4. **`handle_delivery_issue`**: Crafts responses for tracking delays, lost parcels, and courier escalations.
5. **`handle_uncategorized_issue`**: Triggered when a message is unclear, ambiguous, or not related to an order. Politely guides the customer to re-enter their complaint with specific order details (e.g., Order ID, item received, or payment reference).

---

## Why Use `@observe` (Teaching Points for Students)

1. **Explicit & Readable**: By placing `@observe(name="...")` directly above any function or LangGraph node:
   ```python
   @observe(name="categorize_complaint")
   def categorize_complaint(state: ComplaintState) -> dict:
       ...
   ```
   Students can immediately see which parts of the application are being monitored without hunting through configuration dictionaries.

2. **Automatic Context Nesting**:
   - The root function `process_complaint` is decorated with `@observe(name="process_customer_complaint")`.
   - Any child nodes decorated with `@observe` that execute inside it are automatically nested under that root trace.
   - Langfuse captures:
     - Function name
     - Inputs (the incoming graph state)
     - Outputs (the updated graph state / generated response)
     - Execution start time, end time, and latency
     - Any errors or exceptions

3. **No Complex Callbacks**:
   - Students don't need to pass `config={"callbacks": [...]}` into `graph.invoke()`.
   - The graph invocation remains standard, vanilla LangGraph:
     ```python
     final_state = graph.invoke({"complaint": user_complaint})
     ```

4. **Modular Architecture (`init()` function)**:
   - All environment variables, clients, models, and graph compilation are encapsulated within `init()`.
   - Prevents module-level side-effects when importing `main.py`.
   - Explicitly invoked at the start of `main()`.

---

## Quick Start

### 1. Activate Environment & Run

From inside the `langchain-app` directory:

```bash
cd langchain-app
source .venv/bin/activate
python main.py
```

### 2. Interactive Session

Once launched, enter customer complaints directly into the prompt:

```text
======================================================================
Customer Complaint AI Resolution CLI
Langfuse Observability: Enabled via @observe (http://localhost:3000)
LLM Engine: gpt-4o-mini
======================================================================
Enter a customer complaint below (or type 'exit' / 'quit' to quit):

Customer Complaint > Hello, can you tell me what the weather is today in Paris?
```

Type `exit`, `quit`, or `q` (or press `Ctrl+C`) to exit the CLI.

---

## Monitoring in Langfuse Dashboard

1. Open [http://localhost:3000](http://localhost:3000) in your browser.
2. Navigate to **Tracing -> Traces**.
3. Inspect the live trace hierarchy:
   ```text
   SPAN: process_customer_complaint
   ├── SPAN: categorize_complaint
   └── SPAN: handle_uncategorized_issue (or handle_payment_issue / handle_quality_issue / handle_delivery_issue)
   ```
4. Click on each span to inspect the exact input arguments, output dictionary, and execution time.
