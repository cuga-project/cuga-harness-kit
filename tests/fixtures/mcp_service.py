import argparse
import json
import os
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


if __name__ == "__main__":
    mcp.run(transport="stdio" if args.stdio else "streamable-http")
