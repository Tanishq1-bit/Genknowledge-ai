
FROM python:3.11-slim

WORKDIR /app

# Step 1: torch alone, so this big download is cached once it succeeds
RUN pip install --no-cache-dir --default-timeout=100 --retries 10 \
    torch --index-url https://download.pytorch.org/whl/cpu

# Step 2: everything else
COPY requirements.txt .
RUN pip install --no-cache-dir --default-timeout=100 --retries 10 -r requirements.txt

# Download the embedding model at build time
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"

COPY . .

EXPOSE 8000 8501
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]