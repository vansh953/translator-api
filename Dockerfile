# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (Render / Cloud Run compatible) ─────────────────────────────
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HOME=/home/user \
    PYTHONUNBUFFERED=1

WORKDIR /home/user/app

# ── Python dependencies ───────────────────────────────────────────────────────
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Copy application code ─────────────────────────────────────────────────────
COPY --chown=user:user . .

# ── Expose & run ──────────────────────────────────────────────────────────────
# PORT env var is injected by Cloud Run / Railway / Render at runtime
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
