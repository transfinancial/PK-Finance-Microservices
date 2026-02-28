# ── MUFAP Mutual Funds Microservice (multi-stage) ──
# Stage 1: Build wheels (gcc + headers only needed here)
FROM python:3.12-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libxml2-dev libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# Stage 2: Minimal runtime (no compiler, ~50 MB smaller)
FROM python:3.12-slim
WORKDIR /app

# Only runtime libs for lxml (no gcc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

# Install pre-built wheels
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-deps /wheels/*.whl && rm -rf /wheels

# App code only
COPY config.py excel_export.py main.py scraper.py ./

RUN mkdir -p /app/output
ENV EXCEL_OUTPUT_DIR=/app/output \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8001

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "1"]
