# Generated by https://smithery.ai. See: https://smithery.ai/docs/config#dockerfile
FROM ghcr.io/astral-sh/uv:alpine

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies (excluding dev dependencies)
RUN uv sync --no-dev

# Default command to start the MCP server via stdio transport
CMD ["uv", "--directory", "/app", "run", "kmb_mcp.py"]
