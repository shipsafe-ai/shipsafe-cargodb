FROM python:3.11-slim

WORKDIR /app

# Node.js required for mongodb-mcp-server (spawned via npx per MCP call)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm curl \
    && rm -rf /var/lib/apt/lists/*

# Pre-warm npx cache for mongodb-mcp-server so first call doesn't cold-start download
RUN npx -y mongodb-mcp-server --version 2>/dev/null || true

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

CMD ["uvicorn", "agent.server:app", "--host", "0.0.0.0", "--port", "8080"]
