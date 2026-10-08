---
name: cuga-knowledge-rag
description: Use when the user wants a cuga agent to ingest, search, or answer questions from documents (PDF/DOCX/XLSX/PPTX/HTML/Markdown/images) - RAG / knowledge base features.
---

# Knowledge base (RAG)

cuga has a built-in knowledge base: configurable vector/metadata storage (local by default) + **Docling** for parsing/normalizing documents before chunking and embedding, for the default parsing path. Hosted embedding/LLM providers need credentials, and local providers may download models on first use.

The SDK follows installed settings when `enable_knowledge=None`; use `enable_knowledge=True` explicitly for this workflow. Also enable `[knowledge].enabled`, `agent_level_enabled`, and `session_level_enabled` in the installed settings for the scopes you need. In the reviewed version, `enable_knowledge=True` injects tools but `agent.knowledge` still enforces those global settings; it does not override a globally disabled knowledge engine. When enabled, the SDK auto-injects knowledge tools/awareness. Validate those tools through an actual invocation before relying on automatic retrieval. In the reviewed source version, the auto-injected search failed with `Unexpected argument(s) for knowledge_search_knowledge: thread_id`; direct `agent.knowledge.search(...)` succeeded. Do not report automatic RAG or citations as working on that version.

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
        ingestion = await agent.knowledge.ingest("/path/to/quarterly_report.pdf")  # replace with an existing file
        if ingestion.get("status") != "completed" or ingestion.get("failed_files"):
            raise RuntimeError(ingestion)

        results = await agent.knowledge.search("Q4 revenue figures")
        assert results, "No report passages retrieved"
        for r in results:
            print(f"{r['filename']} (page {r.get('page', '?')}): {r['text'][:100]}")

        docs = await agent.knowledge.list_documents()
    finally:
        await agent.aclose()

asyncio.run(main())
```

Direct ingestion/search is a separate check from agent-generated answers. When testing automatic retrieval, use `track_tool_calls=True`, require a successful `knowledge_search_knowledge` call without tool errors, and verify the returned `sources` against the retrieved documents. `result.error is None` alone does not prove tool execution succeeded. If automatic retrieval is broken, use explicit retrieval and pass the checked passages to a separate answering agent with `enable_knowledge=False`; label source references you construct as application-provided references.

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
