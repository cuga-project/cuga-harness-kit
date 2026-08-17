"""
{{PLACEHOLDER: replace "my_server" with the MCP server name from the spec}}
{{PLACEHOLDER: describe what data source or service this server wraps, e.g.
  "MCP Server: incident_db — wraps the Trino/Presto incident database.
   Replaces 6 direct @tool functions from the source system.
   Credentials read from environment variables."}}

FastMCP server. Each @app.tool() exposes one callable to the CUGA agent.
Credentials are read from environment variables — no SDK coupling to the source system.

Run:
    python mcp_server_template.py   # starts SSE server on the configured port
"""

import logging
import os
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

logger = logging.getLogger(__name__)
app = FastMCP("my_server")  # {{PLACEHOLDER: replace with server name from spec}}


# ---------------------------------------------------------------------------
# Connection / client helpers
#
# {{PLACEHOLDER: Replace this section with the actual client for your data source.
#   Read ALL credentials from os.environ — never hard-code them.
#   Common patterns:
#     - Database  → prestodb.dbapi.connect(...) / psycopg2.connect(...)
#     - REST API  → httpx.Client(base_url=..., headers={"Authorization": ...})
#     - SDK       → boto3.client(...) / ibm_watson.SomeService(...)
#   Keep connection creation in a helper so each tool can get a fresh connection.}}
# ---------------------------------------------------------------------------

def _get_client():  # {{PLACEHOLDER: rename to _get_connection / _get_session as appropriate}}
    host = os.environ["MY_SERVICE_HOST"]        # {{PLACEHOLDER: replace with real env var}}
    api_key = os.environ["MY_SERVICE_API_KEY"]  # {{PLACEHOLDER: replace with real env var}}
    # return YourClient(host=host, api_key=api_key)
    raise NotImplementedError("{{PLACEHOLDER: implement client setup}}")


# ---------------------------------------------------------------------------
# Tools
#
# {{PLACEHOLDER: Add one @app.tool() per logical operation the agent needs.
#   Rules:
#   - Function name  → tool name visible to the agent; use snake_case verbs
#   - Docstring      → tool description; be precise about inputs and output shape
#   - Parameters     → map to JSON Schema the agent sees; use Optional for optional args
#   - Return value   → always a JSON-serializable dict; include "success" and/or "error" keys
#   - Error handling → catch exceptions, return {"error": str(e), "success": False}
#                      never let an exception propagate — the agent cannot recover from that}}
# ---------------------------------------------------------------------------

@app.tool()
def fetch_record(record_id: str) -> Dict[str, Any]:
    """
    {{PLACEHOLDER: Precise description of what this tool fetches and what it returns.
    Example: "Fetches core metadata for a given record ID. Returns a dict with
    fields: id, title, status, created_at, updated_at. Returns found=False if
    the record does not exist."}}
    """
    if not record_id or not record_id.strip():
        return {"error": "record_id must be provided", "success": False}

    try:
        # client = _get_client()
        # result = client.get(record_id.strip())
        # return {"success": True, "found": True, "record": result}
        raise NotImplementedError("{{PLACEHOLDER: implement tool body}}")
    except Exception as e:
        logger.exception("fetch_record failed")
        return {"error": str(e), "success": False, "found": False}


@app.tool()
def search_records(
    query: str,
    limit: int = 10,
    filter_field: Optional[str] = None,
) -> Dict[str, Any]:
    """
    {{PLACEHOLDER: Describe the search capability and return shape.
    Example: "Searches records by keyword across title and description fields.
    Returns a list of matching records with id, title, and relevance_score.
    limit caps results (default 10). filter_field restricts the search field."}}
    """
    if not query or not query.strip():
        return {"error": "query must be provided", "success": False}

    try:
        # client = _get_client()
        # results = client.search(query.strip(), limit=limit, filter_field=filter_field)
        # return {"success": True, "results": results, "count": len(results)}
        raise NotImplementedError("{{PLACEHOLDER: implement tool body}}")
    except Exception as e:
        logger.exception("search_records failed")
        return {"error": str(e), "success": False, "results": []}


# {{PLACEHOLDER: Add more @app.tool() functions as needed — one per operation in the spec}}


if __name__ == "__main__":
    port = int(os.getenv("MCP_PORT", "8114"))  # {{PLACEHOLDER: set default port from spec}}
    app.run(transport="sse", port=port)
