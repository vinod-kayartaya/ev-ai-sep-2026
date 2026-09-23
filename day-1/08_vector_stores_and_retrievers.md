# Embeddings, Vector Stores & Retrievers

RAG systems need a way to find information that is semantically related to a user's query. **Embeddings**, **vector stores**, and **retrievers** provide the core mechanism for this process.

## Vector Embeddings

A **vector embedding** is a numerical representation of text in a high-dimensional vector space.

Text with similar meaning tends to produce vectors that are closer together:

```text
Text A ──→ [0.12, 0.81, 0.34, ...]
Text B ──→ [0.15, 0.79, 0.31, ...]
Text C ──→ [0.91, 0.12, 0.67, ...]
```

The embedding model converts text into these numerical representations while capturing semantic characteristics of the content.

## Vector Stores

A **vector store** stores embeddings together with their associated documents or chunks and provides efficient similarity search.

The general process is:

```text
Documents
    ↓
Text Chunks
    ↓
Embedding Model
    ↓
Vectors
    ↓
Vector Store
```

A vector store can then compare a query embedding against stored vectors to identify relevant content.

## FAISS

**FAISS** is a library for efficient similarity search over vectors. LangChain can use FAISS as a vector store for indexing document embeddings and retrieving relevant documents.

The index maintains vector representations and supports searching for vectors that are close to a query vector.

## Similarity Search

When a query is submitted, the query is converted into an embedding and compared with the vectors stored in the vector store.

Conceptually:

```text
User Query
    ↓
Query Embedding
    ↓
Compare with Stored Vectors
    ↓
Similarity / Distance Score
    ↓
Most Relevant Chunks
```

A distance or similarity score indicates how closely a stored vector matches the query. The exact interpretation of the score depends on the distance or similarity metric being used.

## k-NN Retrieval

**k-Nearest Neighbors (k-NN)** retrieval selects the `k` documents whose vectors are closest to the query vector.

For example, with `k = 3`, the three closest matching chunks are returned.

```text
Query
  ↓
Vector Space
  ↓
Nearest ──→ Result 1
Nearest ──→ Result 2
Nearest ──→ Result 3
```

k-NN is straightforward and effective when the most similar pieces of information are the primary retrieval objective.

## Maximal Marginal Relevance

**Maximal Marginal Relevance (MMR)** considers both relevance and diversity when selecting documents.

A standard similarity search may return several chunks that are highly similar to one another. MMR attempts to reduce this redundancy while still maintaining relevance to the query.

Conceptually:

```text
                 Relevance
                    ↑
                    │
             ●  ●   │
          ●         │
                    │
────────────────────┼────→ Diversity
                    │
```

MMR balances two objectives:

- **Relevance** — how closely a document matches the query.
- **Diversity** — how different the selected documents are from one another.

This can provide broader coverage when multiple retrieved chunks contain overlapping information.

## Retrievers

A **retriever** is the component responsible for selecting relevant documents from a collection.

The vector store provides the underlying indexed data, while the retriever defines how relevant documents are selected.

Common retrieval strategies include:

- Similarity-based retrieval
- k-NN retrieval
- MMR retrieval

Retrievers form an important bridge between the knowledge stored in a vector database and the context ultimately provided to an LLM.

## Embeddings in a RAG Pipeline

These components fit together as follows:

```text
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
Relevant Context
    ↓
LLM
```

The quality of embeddings and retrieval directly influences the quality of the context available to the LLM. Efficient retrieval therefore forms one of the fundamental building blocks of a RAG system.
