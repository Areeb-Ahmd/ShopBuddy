# ShopBuddy - AI Customer Support System

An AI-powered e-commerce customer support system & data collection system that answers product-related queries using Retrieval-Augmented Generation (RAG). The unified platform scrapes product reviews from Flipkart, stores vector embeddings in DataStax AstraDB, and serves a modern, multi-tab web interface backed by Google Gemini.

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
- [Docker](#docker)
- [CI/CD](#cicd)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)

---

## Overview

The Customer Support System is a unified, full-pipeline RAG web portal featuring:

1. 💬 **AI Assistant (ShopBuddy Chat)** — Natural-language product Q&A interface retrieving semantically relevant product reviews from AstraDB and generating grounded answers using Gemini `gemini-2.5-flash`.
2. 📦 **Product Scraper & AstraDB Vector Ingestion** — Web interface to search and scrape Flipkart product reviews using Selenium and BeautifulSoup, and ingest embeddings directly into AstraDB in one click.
3. 📊 **Scraped Reviews Explorer** — Searchable data table displaying scraped product reviews with CSV export/download functionality.

---

## Architecture

```
                       Unified FastAPI Web Server (main.py)
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
  [Tab 1: AI Assistant]     [Tab 2: Scraper & Ingest]    [Tab 3: Review Explorer]
  POST /get                 POST /api/scrape & /api/ingest GET /api/reviews & /api/download
         |                            |                            |
         v                            v                            v
LangChain LCEL Chain      Flipkart Scraper (Selenium)     Interactive HTML Table & CSV
 (Gemini 2.5 Flash)                   |                            |
         |                   data/product_reviews.csv              |
         +----------------------------+----------------------------+
                                      |
                                      v
                             DataIngestion Pipeline
                           (Gemini Embedding 001)
                                      |
                                      v
                         DataStax AstraDB Vector DB
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
| Web Scraping | Selenium (`undetected-chromedriver`), BeautifulSoup4 |
| Data Processing | Pandas |
| Frontend UI | HTML5, CSS3, JavaScript (Bootstrap 4, FontAwesome, jQuery, Jinja2) |
| Containerization | Docker |
| CI/CD | GitHub Actions + Amazon ECR |
| Config Management | YAML (`config/config.yaml`) |

---

## Project Structure

```
Customer-Support-System/
|-- config/
|   |-- config.yaml              # Central configuration (models, DB, retriever settings)
|   |-- config_loader.py         # YAML config loader utility
|
|-- data/                        # Scraped CSV data (gitignored)
|   |-- product_reviews.csv
|
|-- data_ingestion/
|   |-- ingestion_pipeline.py    # Transforms CSV data and loads into AstraDB
|
|-- data_scrapper/
|   |-- scrape_data.py           # Flipkart product and review scraper (Selenium + BeautifulSoup)
|
|-- prompt_library/
|   |-- prompt.py                # LangChain prompt templates for the RAG chain
|
|-- retriever/
|   |-- retrieval.py             # AstraDB vector store retriever wrapper
|
|-- static/
|   |-- style.css                # Portal stylesheet
|
|-- templates/
|   |-- chat.html                # Unified Multi-Tab Portal (ShopBuddy)
|   |-- base.html                # Base HTML template
|   |-- index.html               # Legacy search page
|   |-- results.html             # Legacy results table
|
|-- utils/
|   |-- model_loader.py          # Loads Gemini LLM and embedding model instances
|
|-- .github/
|   |-- workflows/
|       |-- main.yaml            # GitHub Actions: build and push Docker image to ECR
|
|-- main.py                      # FastAPI application entry point & API routes
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

Start the unified application server with a single command:

```bash
python main.py
```
*or*
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and navigate to `http://localhost:8000` to access all features:

- 💬 **AI Assistant Tab**: Click the floating chat icon or "Start Chatting Now" to ask product questions.
- 📦 **Scraper & Ingestion Tab**: Enter product keywords, click **🚀 Start Scraping**, and click **🧠 Store in Vector DB (AstraDB)** to update the vector database.
- 📊 **Reviews Explorer Tab**: Filter and search through scraped review data or download `product_reviews.csv`.

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

