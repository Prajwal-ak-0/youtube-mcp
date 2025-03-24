FROM python:3.11-slim as builder

WORKDIR /app

# Copy only requirements files first for better caching
COPY setup.py pyproject.toml ./

# Install build dependencies and create optimized wheel
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
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
    pip install --no-cache-dir python-dotenv && \
    rm -rf /app/wheels && \
    # Create non-root user
    useradd -m appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Set environment variables (these will be overridden at runtime)
ENV GEMINI_API_KEY=""
ENV YOUTUBE_API_KEY=""
ENV PYTHONUNBUFFERED=1

# Expose port for websocket (if needed)
EXPOSE 8000

# Run the MCP server with stdio transport
CMD ["python", "main.py"] 