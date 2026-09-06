# ── Base image ────────────────────────────────────────────────────────────────
FROM python:3.10-slim

# ── System dependencies ───────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# ── Non-root user (Render / HF Spaces compatible) ─────────────────────────────
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HOME=/home/user \
    PYTHONUNBUFFERED=1 \
    # Cache models inside the image (no runtime download needed)
    HF_HOME=/home/user/.cache/huggingface \
    TRANSFORMERS_CACHE=/home/user/.cache/huggingface/transformers

WORKDIR /home/user/app

# ── Python dependencies (layer-cached separately from app code) ───────────────
COPY --chown=user:user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Pre-download model weights at build time ──────────────────────────────────
# This bakes the ~800 MB of model weights into the image so the container
# starts instantly on Render (no timeout waiting for downloads at runtime).
COPY --chown=user:user download_models.py .
RUN python download_models.py

# ── Copy application code ─────────────────────────────────────────────────────
COPY --chown=user:user . .

# ── Expose & run ──────────────────────────────────────────────────────────────
EXPOSE 8080
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}"]
