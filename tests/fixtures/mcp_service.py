import argparse
import json
import os
import uuid
from pathlib import Path
from mcp.server.fastmcp import FastMCP

parser = argparse.ArgumentParser()
parser.add_argument("--stdio", action="store_true")
parser.add_argument("--http", action="store_true")
parser.add_argument("--log-dir", default=os.getenv("CUGA_FIXTURE_LOG_DIR"))
args = parser.parse_args()
mcp = FastMCP(
    "orders",
    host="127.0.0.1",
    port=int(os.getenv("CUGA_MCP_FIXTURE_PORT", "19091")),
    stateless_http=True,
)


@mcp.tool()
def lookup_order(order_id: str) -> str:
    """Look up an order by ID."""
    p = Path(args.log_dir) / "mcp-calls.jsonl"
    with p.open("a") as f:
        f.write(
            json.dumps(
                {
                    "order_id": order_id,
                    "transport": "--stdio" if args.stdio else "--http",
                }
            )
            + "\n"
        )
    return f"MCP_EXECUTED: order {order_id} shipped"


def record_team_call(data):
    with (Path(args.log_dir) / "supervisor-calls.jsonl").open("a") as f:
        f.write(json.dumps(data) + "\n")


@mcp.tool()
def get_customers(limit: int = 1) -> str:
    """Get the top customer's contact and customer record."""
    customer = {
        "contact": "alice@example.test",
        "record": "CRM_RECORD_" + uuid.uuid4().hex,
    }
    record_team_call({"tool": "get_customers", "limit": limit, **customer})
    return json.dumps(customer)


@mcp.tool()
def send_email(to: str, body: str) -> str:
    """Send a fixture email to the supplied contact."""
    record_team_call({"tool": "send_email", "to": to, "body": body})
    return "EMAIL_EXECUTED: " + to + "; " + body


if __name__ == "__main__":
    mcp.run(transport="stdio" if args.stdio else "streamable-http")
