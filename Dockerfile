# Use a Python image
FROM python:3.11-slim as builder

WORKDIR /app

# Copy only requirements files first for better caching
COPY pyproject.toml setup.py ./

# Install build dependencies and create optimized wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip wheel --no-cache-dir --wheel-dir /app/wheels -e .

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Set labels for Smithery
LABEL org.opencontainers.image.title="YouTube MCP"
LABEL org.opencontainers.image.description="MCP server for YouTube video analysis"
LABEL org.opencontainers.image.source="https://github.com/Prajwal-ak-0/youtube-mcp"

# Copy wheels from builder
COPY --from=builder /app/wheels /app/wheels

# Copy project files
COPY . .

# Install dependencies from wheels
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir /app/wheels/*.whl && \
    python -m pip install --no-cache-dir python-dotenv && \
    # Clean up after installation
    rm -rf /app/wheels && \
    # Create non-root user
    groupadd -r mcp && \
    useradd -r -g mcp -d /app -s /bin/bash mcp && \
    chown -R mcp:mcp /app

# Switch to non-root user
USER mcp

# Enable unbuffered Python output
ENV PYTHONUNBUFFERED=1

# The actual command is provided by smithery.yaml at runtime
CMD ["python", "main.py"]
