"""Local protocol fixture, not an LLM; responses deliberately scripted."""

import hashlib
import os
from pathlib import Path
import json
import re
from collections import Counter
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

app = FastAPI()
audit = Counter()


@app.get("/audit")
def get_audit():
    return dict(audit)


@app.get("/api/ui/config")
def disabled_registry():
    return {"agent_registry": False}


@app.post("/stream")
def unexpected_stream():
    audit["unexpected_stream_calls"] += 1
    return {"error": "This fixture must not receive a named-agent invocation"}


@app.get("/orders/{order_id}", operation_id="lookupOrder")
def lookup_order(order_id: str):
    audit["openapi_calls"] += 1
    return {
        "order_id": order_id,
        "status": "shipped",
        "confirmation": "OPENAPI_EXECUTED",
    }


@app.post("/v1/embeddings")
async def embeddings(request: Request):
    data = await request.json()
    inputs = data["input"]
    if not isinstance(inputs, list) or (inputs and isinstance(inputs[0], int)):
        inputs = [inputs]
    items = []
    for i, value in enumerate(inputs):
        vector = [0.0] * 1536
        text = value if isinstance(value, str) else str(value)
        for word in re.findall(r"\w+", text.lower()):
            idx = (
                int.from_bytes(hashlib.sha256(word.encode()).digest()[:4], "little")
                % 1536
            )
            vector[idx] += 1
        norm = sum(x * x for x in vector) ** 0.5 or 1
        items.append(
            {"object": "embedding", "index": i, "embedding": [x / norm for x in vector]}
        )
    audit["embedding_calls"] += 1
    return {
        "object": "list",
        "data": items,
        "model": data.get("model"),
        "usage": {"prompt_tokens": 1, "total_tokens": 1},
    }


def answer(data):
    messages = data["messages"]
    text = "\n".join(str(m.get("content") or "") for m in messages)
    last = str(messages[-1].get("content") or "")
    # Persist only synthetic fixture prompts, so tool naming is inspectable.
    with open(
        Path(os.environ["CUGA_FIXTURE_LOG_DIR"]) / "model-requests.jsonl", "a"
    ) as f:
        f.write(json.dumps(data) + "\n")
    if data.get("response_format", {}).get("type") == "json_schema":
        return json.dumps({"summary": "Fixture summary"})
    if last.startswith(("Execution output:", "Execution Output:")):
        if "knowledge_search_knowledge" in text and "42 million" in last:
            return "Q4 revenue was 42 million dollars [s1]."
        return "Fixture result: " + last[-500:]
    if "5 + 3" in text and "add_numbers" in text:
        if any(
            "```python" in str(m.get("content", ""))
            for m in messages[-3:]
            if m["role"] == "assistant"
        ):
            return "The result is 8."
        return "```python\nresult = await add_numbers(a=5, b=3)\nprint(result)\n```"
    if "knowledge_search_knowledge" in text and "Q4 revenue" in last:
        return '```python\nreport = await knowledge_search_knowledge(query="Q4 revenue Atlas", scope="agent")\nprint(report)\n```'
    crm_delegate = re.search(r"### `(?P<name>delegate_to_[\w]*crm[\w]*)\(", text)
    email_delegate = re.search(r"### `(?P<name>delegate_to_[\w]*email[\w]*)\(", text)
    if crm_delegate and email_delegate:
        return (
            f'```python\ncustomer_result = await {crm_delegate["name"]}(task="Get the top customer")\n'
            f'email_result = await {email_delegate["name"]}(task=f"Send a thank-you using this CRM result: {{customer_result}}")\n'
            "print(customer_result)\nprint(email_result)\n```"
        )
    crm_tool = re.search(r"\b((?:crm_tools_)?get_customers)\b", text)
    if crm_tool:
        return f"```python\ncustomers = await {crm_tool[0]}(limit=1)\nprint(customers)\n```"
    email_tool = re.search(r"\b((?:email_tools_)?send_email)\b", text)
    if email_tool:
        contact = re.search(r"[\w.+-]+@[\w.-]+", last)
        record = re.search(r"CRM_RECORD_\w+", last)
        if not contact or not record:
            return "CRM output missing; cannot send an email."
        phase = "EMAIL_DRAFT" if "EMAIL_DRAFT" in text else "EMAIL_PUBLISHED"
        return (
            f'```python\nmail_result = await {email_tool[0]}(to="{contact[0]}", '
            f'body="Thank you for {record[0]} {phase}")\nprint(mail_result)\n```'
        )
    if "delete_record" in text:
        return '```python\ndeleted = await delete_record(record_id="fixture-1")\nprint(deleted)\n```'
    match = re.search(r"using (orders_\w+)", last)
    if match and "H123" in last:
        return f'```python\norder = await {match.group(1)}(order_id="H123")\nprint(order)\n```'
    return "Hello from the fixture model."


@app.post("/v1/chat/completions")
async def chat(request: Request):
    data = await request.json()
    audit["model_calls"] += 1
    content = answer(data)
    if data.get("stream"):

        async def chunks():
            row = {
                "id": "fixture",
                "object": "chat.completion.chunk",
                "model": data.get("model", "fixture"),
                "choices": [
                    {
                        "index": 0,
                        "delta": {"role": "assistant", "content": content},
                        "finish_reason": None,
                    }
                ],
            }
            yield "data: " + json.dumps(row) + "\n\n"
            row["choices"] = [{"index": 0, "delta": {}, "finish_reason": "stop"}]
            yield "data: " + json.dumps(row) + "\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(chunks(), media_type="text/event-stream")
    return {
        "id": "fixture",
        "object": "chat.completion",
        "model": data.get("model", "fixture"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
    }


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=int(os.environ["CUGA_FIXTURE_PORT"]),
        log_level="warning",
    )
