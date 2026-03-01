FROM python:3.12-slim

# Metadata labels
LABEL org.opencontainers.image.title="AAIF MCP Server"
LABEL org.opencontainers.image.description="MCP server for AI & Agentic Infrastructure Foundation member onboarding"
LABEL org.opencontainers.image.vendor="Linux Foundation"
LABEL org.opencontainers.image.version="0.1.0"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/

# Install Python dependencies and the package in editable mode
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e .

# Create non-root user for security
RUN useradd -m -u 1000 mcp && chown -R mcp:mcp /app
USER mcp

# Expose HTTP transport port
EXPOSE 8080

# Health check using curl to verify HTTP transport
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Set default environment variables
ENV AAIF_MCP_TRANSPORT=streamable-http
ENV AAIF_MCP_LOG_LEVEL=INFO
# FastMCP settings: bind to 0.0.0.0 so Cloud Run / Docker can reach it
# Cloud Run injects PORT=8080; FastMCP reads FASTMCP_PORT
ENV FASTMCP_HOST=0.0.0.0
ENV FASTMCP_PORT=8080

# Default command: run with streamable-http transport
CMD ["python", "-m", "aaif_mcp_server"]
