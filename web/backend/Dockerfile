# ── Backend image ─────────────────────────────────────────────────────────────
# Serves both the FastAPI app (uvicorn) and the RQ worker (same image,
# different CMD). The constellation_simulator source is mounted at runtime
# via a volume — only the Python dependencies are baked in here.
FROM python:3.11-slim

# System libraries required by numpy/matplotlib/skyfield/Pillow
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        libsm6 \
        libxrender1 \
        libxext6 \
        libgl1 \
        curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ── Python dependencies ────────────────────────────────────────────────────────
# Copy both requirement files so a single image can run both the simulator
# and the web backend without a second venv.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ── App source ─────────────────────────────────────────────────────────────────
# Copy web-backend code (simulator source is volume-mounted at /app/simulator)
COPY app/    /app/app/
COPY worker/ /app/worker/

# ── Runtime defaults ──────────────────────────────────────────────────────────
ENV PYTHONPATH=/app/simulator
ENV OUTPUTS_DIR=/app/outputs
ENV SIMULATOR_ROOT=/app/simulator

EXPOSE 8000

# Default: run the API server. Override CMD to start the worker instead.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
