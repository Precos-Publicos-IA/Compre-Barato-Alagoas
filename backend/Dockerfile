# Backend image for Compre Barato Alagoas — multi-stage so the runtime image
# ships only the app + its production dependencies (no build tools, no tests,
# no pip/build caches).

# ---- builder: compile deps into an isolated venv ----
FROM python:3.12-slim AS builder
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

# Build toolchain for any wheels that need compiling (psycopg, cryptography…).
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
# Install dependencies first for better layer caching.
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --upgrade pip && pip install ".[prod]"

# ---- runtime: slim, only the venv + app code ----
FROM python:3.12-slim AS runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app
# The prebuilt venv carries all runtime deps (and the installed app package);
# no compilers or pip caches come along.
COPY --from=builder /opt/venv /opt/venv
COPY app ./app
COPY pyproject.toml README.md ./

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

EXPOSE 8000

# gunicorn with uvicorn workers; tune workers via $WEB_CONCURRENCY.
# Timeout aligned with nginx proxy_read_timeout (~120s) and slow SEFAZ/LLM paths (#196).
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "2", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
