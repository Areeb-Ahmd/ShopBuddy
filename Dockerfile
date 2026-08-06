# ============================================
# Stage 1: Builder — install dependencies
# ============================================
FROM python:3.11-slim AS builder

WORKDIR /app

COPY requirements.txt setup.py ./
COPY config/ ./config/
COPY data_ingestion/ ./data_ingestion/
COPY data_scrapper/ ./data_scrapper/
COPY prompt_library/ ./prompt_library/
COPY retriever/ ./retriever/
COPY utils/ ./utils/

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ============================================
# Stage 2: Production — lean runtime image
# ============================================
FROM python:3.11-slim AS production

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY main.py setup.py requirements.txt ./
COPY config/ ./config/
COPY data_ingestion/ ./data_ingestion/
COPY data_scrapper/ ./data_scrapper/
COPY prompt_library/ ./prompt_library/
COPY retriever/ ./retriever/
COPY utils/ ./utils/
COPY static/ ./static/
COPY templates/ ./templates/

# Install the local package (editable install from setup.py)
RUN pip install --no-cache-dir -e .

# Create data directory for runtime CSV storage
RUN mkdir -p /app/data

# Mark this as a cloud deployment — disables scraper endpoints
ENV DEPLOYMENT_ENV=gcp

# Cloud Run sets PORT env var; default to 8080
ENV PORT=8080

EXPOSE ${PORT}

# Use shell form so $PORT is expanded at runtime
CMD uvicorn main:app --host 0.0.0.0 --port $PORT