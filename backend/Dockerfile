# Build context: raiz del repo (necesita el paquete backend/ completo para
# que los imports "backend.app.xxx" resuelvan). Ver docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY backend/__init__.py backend/__init__.py
COPY backend/app backend/app

# Los modelos NO se copian a la imagen (pesan varios GB); se montan como
# volumen en runtime y se apuntan con MODELS_DIR (ver docker-compose.yml).
ENV MODELS_DIR=/models
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
