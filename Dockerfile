# Stage 1: build the React app.
FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

# Stage 2: the Python API on CPU, serving the built app too (port 7860).
# The fine-tuned model is mounted at /model (docker compose) or baked in with --build-arg MODEL_REPO=<hub repo>.
FROM python:3.12-slim

ARG MODEL_REPO=""
ENV PIP_NO_CACHE_DIR=1 TORCH_THREADS=4 MODEL_DIR=/model HF_HOME=/tmp/hf WEB_DIST=/home/user/app/web/dist

RUN pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 \
 && pip install "transformers>=4.45,<5" "sentencepiece>=0.2" "protobuf>=5" "pillow>=10" "matplotlib>=3.9" \
    "fastapi>=0.115" "uvicorn>=0.30" "python-multipart>=0.0.9" "huggingface_hub>=0.25"

RUN useradd -m -u 1000 user && mkdir -p /model && chown user /model
USER user
WORKDIR /home/user/app
RUN if [ -n "$MODEL_REPO" ]; then python -c "from huggingface_hub import snapshot_download; snapshot_download('$MODEL_REPO', local_dir='/model')"; fi
COPY --chown=user invoicedesk ./invoicedesk
COPY --chown=user app ./app
COPY --from=web --chown=user /web/dist ./web/dist

EXPOSE 7860
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:7860/health')"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
