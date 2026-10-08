"""Isolated subprocess scenario; core knowledge code is not patched."""

import asyncio
import json
import os
from pathlib import Path

from cuga import CugaAgent


async def main():
    root = Path(os.environ["CUGA_KNOWLEDGE_WORKER_DIR"])
    root.mkdir(exist_ok=True)
    report = root / "quarterly_report.txt"
    report.write_text(
        "Quarterly report. Q4 revenue was 42 million dollars. This report covers the Atlas division. Approval code ATLAS-42."
    )
    agent = CugaAgent(
        enable_knowledge=True, auto_load_policies=False, filesystem_sync=False
    )
    try:
        ingestion = await agent.knowledge.ingest(str(report))
        results = await agent.knowledge.search("Q4 revenue Atlas")
        docs = await agent.knowledge.list_documents()
        await agent.knowledge.ingest(
            str(report), scope="session", thread_id="session-one"
        )
        first = await agent.knowledge.list_documents(
            scope="session", thread_id="session-one"
        )
        other = await agent.knowledge.list_documents(
            scope="session", thread_id="session-two"
        )
        answer = await agent.invoke(
            "What is Q4 revenue in the report?",
            thread_id="rag-citations",
            track_tool_calls=True,
        )
        data = {
            "ingestion": ingestion,
            "results": results,
            "docs": docs,
            "first": first,
            "other": other,
            "answer": answer.model_dump(mode="json"),
        }
        (root / "result.json").write_text(json.dumps(data))
    finally:
        await agent.aclose()


asyncio.run(main())
