# Conversational Memory

LLM applications are often designed to support multi-turn conversations. For this to work, the application must maintain relevant information from earlier interactions and provide it to the model when processing a new message. This is known as **conversational memory**.

## Stateful Conversations

A **stateful conversation** maintains information across multiple interactions within a session.

Without memory, each request is independent:

```text
Message 1 → LLM
Message 2 → LLM
Message 3 → LLM
```

With conversational memory, previous messages become part of the context:

```text
Message 1
   ↓
Message 2 + History
   ↓
Message 3 + History
```

This allows the model to maintain conversational context and refer to information provided earlier.

## Message History

A message history stores the sequence of messages exchanged during a conversation. It typically contains both user messages and model responses.

In LangChain, `InMemoryChatMessageHistory` provides an in-memory mechanism for maintaining this conversation state.

A session can therefore maintain its own sequence of messages independently from other sessions.

## MessagesPlaceholder

`MessagesPlaceholder` provides a location in a chat prompt where a collection of previous messages can be inserted dynamically.

A prompt can therefore be structured as:

```text
System Message
      ↓
Conversation History
      ↓
Current User Message
```

This separates the persistent conversation history from the current input while allowing both to be supplied to the model.

## RunnableWithMessageHistory

`RunnableWithMessageHistory` adds message-history management to an existing LangChain runnable.

It connects a chain with a mechanism that:

1. Identifies the current session.
2. Retrieves the corresponding message history.
3. Provides that history to the chain.
4. Processes the new input.
5. Updates the conversation history.

This allows an otherwise stateless chain to participate in a stateful conversation.

## Session Isolation

A conversational application may serve many users simultaneously. Each conversation therefore needs a unique **session identifier**.

Conceptually:

```text
Session A → History A
Session B → History B
Session C → History C
```

When a request arrives, its `session_id` determines which conversation history is used. This prevents messages from one session from being mixed with another session.

Session isolation is particularly important when conversations contain confidential or user-specific information.

## In-Memory vs Persistent Memory

`InMemoryChatMessageHistory` stores conversation state in application memory. This is useful for simple applications and demonstrations, but the state is generally tied to the lifetime of the running application.

Production systems may instead use persistent storage so that conversation history can survive application restarts and be shared across application instances.

Conversational memory therefore consists of two closely related concerns: **maintaining context across turns** and **maintaining strict separation between different sessions**.
