# Build context: raiz del repo (necesita el paquete backend/ completo para
# que los imports "backend.app.xxx" resuelvan). Ver docker-compose.yml.
FROM python:3.12-slim

WORKDIR /app

# perl-base ships in the base image marked "essential" by Debian but nothing
# in this app or its deps calls perl; it's purged to drop unfixed Debian CVEs
# (docker scout) that a Python-only image has no other way to resolve.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 \
    libxslt1.1 \
    && apt-get purge -y --allow-remove-essential perl-base \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    --no-build-isolation

# Los pesos (~821MB: random_forest_v2.pkl, roberta_phishing_new/, roberta_content/)
# no viven en el repo (models/ esta en .gitignore) ni en un volumen persistente
# (Render free tier no ofrece disco persistente), asi que se descargan desde el
# repo publico de Hugging Face Hub durante el build y quedan horneados en la
# imagen. Repo: https://huggingface.co/mel3601/phishing-ia-models
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='mel3601/phishing-ia-models', local_dir='/models')"

COPY backend/__init__.py backend/__init__.py
COPY backend/app backend/app

ENV MODELS_DIR=/models
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# $PORT is set by Render (default 10000) and must be respected; falls back to
# 8000 for local docker-compose, which doesn't set PORT.
#
# --proxy-headers makes uvicorn read X-Forwarded-For from the connecting
# peer and use it as request.client.host (needed for RateLimitMiddleware in
# main.py to see real visitor IPs instead of Render's load balancer IP —
# without this every user shares one rate-limit bucket in production).
# --forwarded-allow-ips defaults to the safe/inert 127.0.0.1 (same as
# uvicorn's own default) so a directly-exposed local docker-compose
# instance doesn't trust a client-supplied X-Forwarded-For by default; set
# FORWARDED_ALLOW_IPS=* in Render's dashboard env vars, where the container
# is never reachable except through Render's own proxy.
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=${FORWARDED_ALLOW_IPS:-127.0.0.1}"]
