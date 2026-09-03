FROM ghcr.io/astral-sh/uv:python3.14-bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./

RUN uv sync \
    --frozen \
    --no-dev \
    --no-install-project \
    --no-binary-package numpy \
    --config-settings-package numpy:setup-args=-Dcpu-baseline=none

COPY alembic.ini ./
COPY alembic ./alembic
COPY src ./src

RUN uv sync \
    --frozen \
    --no-dev \
    --config-settings-package numpy:setup-args=-Dcpu-baseline=none

FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    libegl1 \
    libgl1 \
    libglib2.0-0 \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=builder --chown=appuser:appuser /app /app
ENV PATH="/app/.venv/bin:$PATH"
USER appuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["python", "-m", "mood_tracker.presentation.main"]
