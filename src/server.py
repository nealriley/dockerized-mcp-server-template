import os
import multiprocessing
import uvicorn
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("docker-mcp")
app = mcp.sse_app()

# Define a simple function called 'add' to be used with the MCP
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

if __name__ == "__main__":
    if os.getenv("RUNNING_IN_PRODUCTION"):
        # Production mode with multiple workers for better performance
        uvicorn.run(
            "server:app",  # Pass as import string
            host="0.0.0.0",
            port=3000,
            workers=(multiprocessing.cpu_count() * 2) + 1,
            timeout_keep_alive=300  # Increased for SSE connections
        )
    else:
        # Development mode with a single worker for easier debugging
        uvicorn.run("server:app", host="0.0.0.0", port=3000, reload=True)