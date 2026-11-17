# syntax=docker/dockerfile:1
#
# Multi-stage build for the Natives FastAPI backend.
#   1) "builder": installs Python deps into an isolated venv.
#   2) "runtime": copies just the venv + app code into a slim image,
#      runs as a non-root user. No compilers/build tools end up in the
#      final image.
#
# Build:  docker build -t natives-backend .
# Run:    docker run --rm -p 8000:8000 --env-file .env natives-backend
# (In real deployments, pass config via real env vars / your platform's
#  secret manager, not --env-file — see README.md "Deployment".)

# ---------------------------------------------------------------- builder
FROM python:3.12-slim AS builder

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"

# Copy only the requirements file first so dependency installs are cached
# across builds as long as requirements.txt doesn't change.
COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install -r requirements.txt

# ---------------------------------------------------------------- runtime
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}"

# Unprivileged user to run the app as.
RUN addgroup --system app && adduser --system --ingroup app app

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv

# App code. alembic/scripts are included so migrations/seeding can still be
# run manually inside the container (`docker exec ... alembic upgrade head`),
# but nothing here runs them automatically on boot.
COPY app/ ./app
COPY alembic/ ./alembic
COPY alembic.ini .
COPY scripts/ ./scripts

USER app

EXPOSE 8000

# Reads the PORT env var itself so it matches whatever the server binds to.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "\
import os, sys, urllib.request; \
port = os.environ.get('PORT', '8000'); \
sys.exit(0 if urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3).status == 200 else 1)"

# Shell form so $PORT / $WEB_CONCURRENCY are expanded at container start;
# most PaaS hosts inject PORT automatically.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers ${WEB_CONCURRENCY:-1}
