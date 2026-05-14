FROM python:3.12-slim AS base
WORKDIR /app
RUN addgroup --system worker && adduser --system --group worker

FROM base AS builder
COPY pyproject.toml .
RUN pip install uv && uv pip install --system .

FROM base AS runtime
COPY --from=builder /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY --from=builder /usr/local/bin /usr/local/bin
COPY worker/ ./worker/
USER worker
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "worker.main:app", "--host", "0.0.0.0", "--port", "8000"]
