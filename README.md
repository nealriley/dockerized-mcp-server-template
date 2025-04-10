# Dockerized MCP Server Template

This repository provides a reusable template for a Python server implementing the **Model Context Protocol (MCP)**, running in a Docker container and utilizing Server-Sent Events (SSE) for real-time communication. Built using the FastMCP library, this template enables easy integration with Large Language Models (LLMs).

## What is MCP?

The **Model Context Protocol (MCP)** is a standardized protocol designed specifically for interactions with Large Language Models (LLMs). MCP allows applications to clearly separate the concerns of providing context (data and functionality) from the actual LLM interactions. MCP servers expose:

- **Resources**: Provide data to LLMs (similar to GET endpoints).
- **Tools**: Allow LLMs to execute actions or computations (similar to POST endpoints).
- **Prompts**: Reusable templates for structured interactions with LLMs.

This template demonstrates a production-ready MCP server running in a Docker container, utilizing Server-Sent Events (SSE) for real-time communication.

## Project Structure

```
dockerized-mcp-server-template/
├── src/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py
├── docker-compose.yml
└── README.md
```

## Getting Started

### Build and Run with Docker Compose

```bash
docker-compose up --build
```

The server will be accessible at:

```
http://localhost:3000/sse
```

### Running Directly (without Docker)

Alternatively, you can run the server directly using Python. First, install dependencies:

```bash
pip install -r src/requirements.txt
```

Then run the server:

```bash
python src/server.py
```

The server will be accessible at:

```
http://localhost:3000/sse
```

## Example Usage

The example includes a simple MCP tool function `add`:

```python
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
```

You can invoke this tool via MCP client requests.

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)