FROM python:3.11-slim
# LibreOffice renders DOCX → PDF exactly (keeps Word auto-numbering) for the reference viewer.
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer-nogui fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app/backend
COPY requirements.txt .
# --trusted-host: needed behind TLS-intercepting proxies; harmless elsewhere.
RUN pip install --no-cache-dir --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
# warm the embedding model into the image
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')" || true
COPY odin ./odin
ENV ODIN_CONFIG=/app/config/odin.yaml PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "odin.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
