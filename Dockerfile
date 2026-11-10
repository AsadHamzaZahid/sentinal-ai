FROM python:3.12.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    RAGTRUTH_MODE=precomputed

WORKDIR /app

COPY requirements.docker.txt .
RUN python -m pip install --upgrade pip && \
    python -m pip install -r requirements.docker.txt

COPY main.py .
COPY static/ ./static/
COPY models/smd/ ./models/smd/
COPY NAB_outputs/prepared/ ./NAB_outputs/prepared/
COPY data/demo/ragtruth_samples.json ./data/demo/ragtruth_samples.json
COPY artifacts/ ./artifacts/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
