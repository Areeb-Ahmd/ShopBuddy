# Customer Support System

An AI-powered e-commerce customer support chatbot that answers product-related queries using Retrieval-Augmented Generation (RAG). The system scrapes product reviews from Flipkart, stores them as vector embeddings in DataStax AstraDB, and serves a conversational chat interface backed by Google Gemini.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [1. Scrape and Ingest Data](#1-scrape-and-ingest-data)
  - [2. Run the Chat Application](#2-run-the-chat-application)
- [Docker](#docker)
- [CI/CD](#cicd)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)

---

## Overview

The Customer Support System is a full-pipeline RAG application designed for e-commerce use cases. It consists of three distinct stages:

1. **Data Collection** — Scrapes product listings and customer reviews from Flipkart using Selenium and BeautifulSoup, and saves the results to a local CSV file.
2. **Data Ingestion** — Transforms the scraped data into LangChain `Document` objects, generates vector embeddings using the Google Gemini embedding model (`gemini-embedding-001`), and stores them in a DataStax AstraDB vector collection in configurable batches.
3. **Inference** — Accepts natural-language questions from users via a web chat interface, retrieves the top-k most semantically relevant documents from AstraDB, and generates a grounded, context-aware response using the Gemini `gemini-2.5-flash` LLM through a LangChain LCEL chain.

---

## Architecture

```
User Query
    |
    v
FastAPI Web Server (main.py)
    |
    v
LangChain LCEL Chain
    |--- Retriever (AstraDBVectorStore) <--- AstraDB Vector Collection
    |--- ChatPromptTemplate (prompt_library/prompt.py)
    |--- ChatGoogleGenerativeAI (Gemini 2.5 Flash)
    |--- StrOutputParser
    |
    v
Response rendered in chat UI (templates/chat.html)


Data Pipeline (run separately):
Flipkart Website
    |
    v
data_scrapper/scrape_data.py  (Selenium + BeautifulSoup)
    |
    v
data/product_reviews.csv
    |
    v
data_ingestion/ingestion_pipeline.py
    |--- Google Gemini Embeddings
    |--- AstraDBVectorStore (batched ingestion)
    |
    v
AstraDB Vector Collection
```

---

## Tech Stack

| Component | Technology |
|---|---|
| Web Framework | FastAPI |
| ASGI Server | Uvicorn |
| LLM | Google Gemini 2.5 Flash (`langchain-google-genai`) |
| Embedding Model | Google Gemini Embedding 001 |
| Vector Store | DataStax AstraDB (`langchain-astradb`) |
| RAG Orchestration | LangChain / LangChain Core (LCEL) |
| Web Scraping | Selenium (`undetected-chromedriver`), BeautifulSoup |
| Data Processing | Pandas |
| Ingestion UI | Streamlit |
| Templating | Jinja2 |
| Containerization | Docker |
| CI/CD | GitHub Actions + Amazon ECR |
| Config Management | YAML (`config/config.yaml`) |

---

## Project Structure

```
customer-support-system/
|
|-- config/
|   |-- config.yaml              # Central configuration (models, DB, retriever settings)
|   |-- config_loader.py         # YAML config loader utility
|
|-- data/                        # Scraped CSV data (gitignored)
|   |-- flipkart_product_review.csv
|
|-- data_ingestion/
|   |-- ingestion_pipeline.py    # Transforms CSV data and loads into AstraDB
|
|-- data_scrapper/
|   |-- scrape_data.py           # Flipkart product and review scraper (Selenium)
|
|-- prompt_library/
|   |-- prompt.py                # LangChain prompt templates for the RAG chain
|
|-- retriever/
|   |-- retrieval.py             # AstraDB vector store retriever wrapper
|
|-- scripts/
|   |-- flipkart_scapper.py      # Standalone scraper script placeholder
|
|-- static/
|   |-- style.css                # Application stylesheet
|
|-- templates/
|   |-- chat.html                # Main chat UI (ShopBuddy)
|   |-- base.html                # Base HTML template
|   |-- index.html               # Landing page
|   |-- results.html             # Search results page
|
|-- utils/
|   |-- model_loader.py          # Loads Gemini LLM and embedding model instances
|
|-- .github/
|   |-- workflows/
|       |-- main.yaml            # GitHub Actions: build and push Docker image to Amazon ECR
|
|-- main.py                      # FastAPI application entry point
|-- scrapper_ingestion_ui.py     # Streamlit UI for scraping and ingesting data
|-- setup.py                     # Python package setup
|-- requirements.txt             # Python dependencies
|-- Dockerfile                   # Container build definition
|-- .gitignore
```

---

## Prerequisites

- Python 3.10 or higher
- Google Chrome (for Selenium-based scraping)
- A [DataStax AstraDB](https://astra.datastax.com/) account with a vector-enabled database
- A [Google AI Studio](https://aistudio.google.com/) API key with access to Gemini models
- Docker (optional, for containerized deployment)

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/Areeb-Ahmd/Customer-Support-System.git
cd Customer-Support-System
```

**2. Create and activate a virtual environment**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

---

## Configuration

**1. Create a `.env` file** in the project root with the following variables:

```env
GOOGLE_API_KEY=your_google_api_key
ASTRA_DB_API_ENDPOINT=your_astradb_api_endpoint
ASTRA_DB_APPLICATION_TOKEN=your_astradb_application_token
ASTRA_DB_KEYSPACE=your_astradb_keyspace
```

**2. Review `config/config.yaml`** to adjust model names, the AstraDB collection name, and the retriever's `top_k` value:

```yaml
astra_db:
  collection_name: "customersupportsystem"

embedding_model:
  provider: "google"
  model_name: "models/gemini-embedding-001"

retriever:
  top_k: 10

llm:
  provider: "google"
  model_name: "gemini-2.5-flash"
```

---

## Usage

### 1. Scrape and Ingest Data

The data pipeline must be run before starting the chat application to populate the vector store.

**Option A — Streamlit UI (recommended)**

The Streamlit interface provides a graphical workflow to scrape products and trigger ingestion:

```bash
streamlit run scrapper_ingestion_ui.py
```

This launches a UI where you can:
- Enter one or more product names to search on Flipkart
- Configure the number of products and reviews to scrape per query
- Download the resulting CSV
- Push the scraped data into AstraDB with a single click

**Option B — Run ingestion directly**

If you already have a CSV file at `data/flipkart_product_review.csv` with the required columns (`product_title`, `rating`, `summary`, `review`), run the ingestion pipeline directly:

```bash
python -m data_ingestion.ingestion_pipeline
```

The pipeline ingests documents in batches of 50 and respects API rate limits by pausing between batches.

### 2. Run the Chat Application

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open your browser and navigate to `http://localhost:8000`. Click the chat icon in the bottom-right corner to open the ShopBuddy chat widget and begin asking product-related queries.

---

## Docker

Build the Docker image:

```bash
docker build -t customer-support-system .
```

Run the container, passing in your environment variables:

```bash
docker run -p 8000:8000 \
  -e GOOGLE_API_KEY=your_google_api_key \
  -e ASTRA_DB_API_ENDPOINT=your_astradb_api_endpoint \
  -e ASTRA_DB_APPLICATION_TOKEN=your_astradb_application_token \
  -e ASTRA_DB_KEYSPACE=your_astradb_keyspace \
  customer-support-system
```

The application will be accessible at `http://localhost:8000`.

---

## CI/CD

The repository includes a GitHub Actions workflow (`.github/workflows/main.yaml`) that automatically builds and pushes the Docker image to **Amazon ECR** on every push to the `main` branch.

**Required GitHub Secrets:**

| Secret | Description |
|---|---|
| `AWS_ACCESS_KEY_ID` | AWS IAM access key ID |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM secret access key |
| `AWS_SESSION_TOKEN` | AWS session token (if using temporary credentials) |

The workflow targets the `us-east-1` region and pushes to an ECR repository named `customer-support-system`.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GOOGLE_API_KEY` | Yes | API key for Google Gemini (LLM and embeddings) |
| `ASTRA_DB_API_ENDPOINT` | Yes | DataStax AstraDB REST API endpoint |
| `ASTRA_DB_APPLICATION_TOKEN` | Yes | DataStax AstraDB application token |
| `ASTRA_DB_KEYSPACE` | Yes | AstraDB keyspace (namespace) to use |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature-name`)
3. Commit your changes (`git commit -m 'Add feature: your-feature-name'`)
4. Push to the branch (`git push origin feature/your-feature-name`)
5. Open a Pull Request

---

**Author:** Syed Areeb Ahmad — [ahmad.syedareeb7@gmail.com](mailto:ahmad.syedareeb7@gmail.com)
