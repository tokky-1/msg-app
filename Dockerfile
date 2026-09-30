FROM python:3.12-slim AS builder

WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN pip install uv && \
    uv export --no-dev --format requirements-txt -o requirements.txt && \
    pip install -r requirements.txt --target /install


FROM python:3.12-slim

# Keep JSON log lines flowing to stdout instead of sitting in a buffer.
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY --from=builder /install /usr/local/lib/python3.12/site-packages
RUN groupadd -r appgroup && useradd -r -g appgroup appuser
RUN mkdir -p /app/storage && chown -R appuser:appgroup /app/storage
COPY --chown=appuser:appgroup backend/ .

USER appuser
EXPOSE 8000
CMD ["python","-m","uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
