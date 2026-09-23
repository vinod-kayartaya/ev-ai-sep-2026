# Document Loading & Chunking

Retrieval-Augmented Generation (RAG) systems work with information stored in documents. Before this information can be searched and provided to an LLM, documents need to be loaded and divided into smaller pieces called **chunks**.

## Document Loading

**Document loading** is the process of reading external data and converting it into a format that LangChain can process.

LangChain provides different document loaders for different sources, including text files, PDFs, web pages, and other document formats.

A loaded document generally contains two important parts:

- **Page content** — the actual text.
- **Metadata** — information about the source and other document properties.

## Text Splitting

Large documents are usually too big to process or retrieve as a single unit. **Text splitting** divides them into smaller chunks.

For example:

```text
Document
   ↓
┌─────────┐
│ Chunk 1 │
├─────────┤
│ Chunk 2 │
├─────────┤
│ Chunk 3 │
└─────────┘
```

Good chunking should preserve enough context for each chunk to remain meaningful while keeping chunks small enough for efficient retrieval.

## CharacterTextSplitter

`CharacterTextSplitter` divides text based on a specified separator and chunk size.

It provides a simple splitting strategy, but fixed character boundaries may not always preserve the logical structure of the content. Important sentences, paragraphs, or clauses can potentially be separated between chunks.

## RecursiveCharacterTextSplitter

`RecursiveCharacterTextSplitter` uses a hierarchy of separators to find suitable boundaries.

It can progressively attempt larger structural boundaries before falling back to smaller ones:

```text
Paragraph
   ↓
Line
   ↓
Word
   ↓
Character
```

This makes recursive splitting more suitable for documents where maintaining meaningful text boundaries is important.

## Chunk Size

**chunk_size** determines the approximate maximum size of each chunk.

A smaller chunk provides more focused content but may contain less context. A larger chunk preserves more context but may introduce unrelated information during retrieval.

Choosing an appropriate chunk size is therefore a balance between **context**, **retrieval precision**, and **processing cost**.

## Chunk Overlap

**chunk_overlap** specifies how much content is shared between consecutive chunks.

```text
Chunk 1: [A B C D E]
Chunk 2:       [D E F G H]
```

The overlapping content helps preserve context when an important piece of information occurs near a chunk boundary.

Too little overlap can lose contextual continuity, while excessive overlap increases the amount of duplicated content.

## Document Metadata

Metadata provides information about where a chunk originated and can be preserved during splitting.

Common metadata can include:

- Source document
- Document identifier
- Position or start index
- Other application-specific attributes

Metadata becomes particularly useful during retrieval because it allows the application to associate retrieved content with its original source.

## Chunking for RAG

Chunking is an important preprocessing step in a RAG pipeline:

```text
Documents
    ↓
Document Loader
    ↓
Text Splitter
    ↓
Chunks + Metadata
    ↓
Embeddings / Vector Store
    ↓
Retrieval
```

The quality of the chunks directly affects how effectively relevant information can be retrieved later. Good chunking preserves meaningful context while producing manageable and searchable units.
