---
name: cuga-knowledge-rag
description: Use when the user wants a cuga agent to ingest, search, or answer questions from documents (PDF/DOCX/XLSX/PPTX/HTML/Markdown/images) - RAG / knowledge base features.
---

# Knowledge base (RAG)

cuga has a built-in knowledge base: configurable vector/metadata storage (local by default) + **Docling** for parsing/normalizing documents before chunking and embedding, for the default parsing path. Hosted embedding/LLM providers need credentials, and local providers may download models on first use.

The SDK follows installed settings when `enable_knowledge=None`; use `enable_knowledge=True` explicitly for this workflow. When enabled, the SDK auto-injects knowledge tools/awareness so the agent knows what's available and how to search it.

This example uses the embedded SDK. For a managed server, configure knowledge and upload documents through Manage/server APIs on the selected agent; use `cuga-managed-server`. Publishing config does not import SDK-process documents into that server.

## Try it

```bash
uv run cuga start demo_knowledge
```

Full walkthrough with sample docs: `docs/examples/knowledge_demo/` in a cuga-agent checkout.

## Programmatic use

```python
from cuga import CugaAgent
import asyncio

async def main():
    agent = CugaAgent(enable_knowledge=True)
    try:
        await agent.knowledge.ingest("/path/to/quarterly_report.pdf")  # replace with an existing file

        result = await agent.invoke("What does the report say about Q4 revenue?")
        if result.error:
            raise RuntimeError(result.error)
        print(result.answer)  # agent searches the knowledge base automatically

        results = await agent.knowledge.search("Q4 revenue figures")
        for r in results:
            print(f"{r['filename']} (page {r.get('page', '?')}): {r['text'][:100]}")

        docs = await agent.knowledge.list_documents()
    finally:
        await agent.aclose()

asyncio.run(main())
```

## Scoping

```python
# Session-scoped: temporary, tied to one conversation thread
await agent.knowledge.ingest("/path/to/file.pdf", scope="session", thread_id="user-session-123")
results = await agent.knowledge.search("query", scope="session", thread_id="user-session-123")

# Agent-scoped (default): permanent, shared across conversations
await agent.knowledge.ingest("/path/to/file.pdf", scope="agent")
```

Use `session` scope for per-conversation uploads that shouldn't leak between users; use `agent` scope for a shared reference corpus.

## Disabling

```python
agent = CugaAgent(enable_knowledge=False)
```

## Supported types & tuning

PDF, DOCX, XLSX, PPTX, HTML, Markdown, images, and more (via Docling). Embedding provider (`fastembed` default/local, `huggingface`, `openai`, `ollama`, `openrouter`) plus model/batch/concurrency are set under `[knowledge.embeddings]` in `settings.toml` or via `--embeddings-*` CLI flags. Switching provider/model invalidates existing vectors (different dimensionality) — the manage UI (`cuga start manager`) surfaces a "re-index recommended" banner when that happens.

Full provider matrix: https://docs.cuga.dev/docs/sdk/knowledge/
