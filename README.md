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
- [Docker & Docker Compose](#docker--docker-compose)
- [Google Cloud Run Deployment](#google-cloud-run-deployment)
- [CI/CD Pipeline](#cicd-pipeline)
- [Environment Variables](#environment-variables)
- [Contributing](#contributing)

---

## Overview

The Customer Support System is a unified, full-pipeline RAG web portal featuring:

1. 💬 **AI Assistant (ShopBuddy Chat)** — Natural-language product Q&A interface retrieving semantically relevant product reviews from AstraDB and generating grounded answers using Gemini `gemini-2.5-flash`.
2. 📦 **Product Scraper & AstraDB Vector Ingestion** — Web interface to search and scrape Flipkart product reviews using Selenium and BeautifulSoup, and ingest embeddings directly into AstraDB in one click (functional when running locally).
3. 📊 **Scraped Reviews Explorer** — Searchable data table displaying scraped product reviews with CSV export/download functionality (functional when running locally).

---

## Architecture

```
                       Unified FastAPI Web Server (main.py)
                                      |
         +----------------------------+----------------------------+
         |                            |                            |
         v                            v                            v
  [Tab 1: AI Assistant]     [Tab 2: Scraper & Ingest]*   [Tab 3: Review Explorer]*
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
*\*Note: Scraper and data pipeline endpoints are gated when deployed on Google Cloud Run (`DEPLOYMENT_ENV=gcp`) and return a friendly 403 response indicating the feature is local-only.*

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
| Containerization | Docker & Docker Compose |
| Cloud Hosting | Google Cloud Run |
| Artifact Repository | GCP Artifact Registry |
| Secrets Management | GCP Secret Manager |
| CI/CD | GitHub Actions |
| Config Management | YAML (`config/config.yaml`) |

---

## Project Structure

```
ShopBuddy/
├── .github/
│   └── workflows/
│       └── deploy.yml              # GCP Cloud Run CI/CD pipeline
├── config/
│   ├── config.yaml              # Central configuration (models, DB, retriever settings)
│   └── config_loader.py         # YAML config loader utility
├── data/                        # Scraped CSV data (gitignored)
│   └── product_reviews.csv
├── data_ingestion/
│   └── ingestion_pipeline.py    # Transforms CSV data and loads into AstraDB
├── data_scrapper/
│   └── scrape_data.py           # Flipkart product and review scraper (Selenium + BeautifulSoup)
├── prompt_library/
│   └── prompt.py                # LangChain prompt templates for the RAG chain
├── retriever/
│   └── retrieval.py             # AstraDB vector store retriever wrapper
├── static/
│   ├── style.css                # Portal stylesheet
│   └── f6634145-...png
├── templates/
│   ├── base.html                # Base HTML template
│   ├── chat.html                # Unified Multi-Tab Portal (ShopBuddy)
│   ├── index.html               # Search page template
│   └── results.html             # Results table template
├── utils/
│   └── model_loader.py          # Loads Gemini LLM and embedding model instances
├── .dockerignore
├── .env.example                 # Template for required environment variables
├── Dockerfile                   # Multi-stage container build definition
├── docker-compose.yml           # Local multi-service development compose file
├── main.py                      # FastAPI application entry point, health check & API routes
├── requirements.txt             # Python dependencies
├── setup.py                     # Python package setup
└── README.md
```

---

## Prerequisites

- Python 3.10 or higher
- Google Chrome (for Selenium-based scraping when running locally)
- A [DataStax AstraDB](https://astra.datastax.com/) account with a vector-enabled database
- A [Google AI Studio](https://aistudio.google.com/) API key with access to Gemini models
- Docker & Docker Compose (optional, for local containerized development)
- Google Cloud SDK (`gcloud` CLI) for GCP deployment

---

## Installation

**1. Clone the repository**

```bash
git clone https://github.com/Areeb-Ahmd/ShopBuddy.git
cd ShopBuddy
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
pip install -e .
```

---

## Configuration

**1. Create a `.env` file** in the project root based on `.env.example`:

```env
GOOGLE_API_KEY=your_google_api_key
ASTRA_DB_API_ENDPOINT=your_astradb_api_endpoint
ASTRA_DB_APPLICATION_TOKEN=your_astradb_application_token
ASTRA_DB_KEYSPACE=your_astradb_keyspace
DEPLOYMENT_ENV=local
PORT=8080
```

**2. Review `config/config.yaml`** to adjust model names, AstraDB collection name, and retriever `top_k`:

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

Start the application server locally:

```bash
python main.py
```
*or*
```bash
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

Open your browser and navigate to `http://localhost:8080` to access all features:

- 💬 **AI Assistant Tab**: Ask product queries and get AI answers backed by Gemini and AstraDB.
- 📦 **Scraper & Ingestion Tab**: Search and scrape Flipkart reviews locally, then store embeddings into AstraDB.
- 📊 **Reviews Explorer Tab**: Filter, search, and download scraped product review CSVs locally.

---

## Docker & Docker Compose

### Local Development with Docker Compose

Run the entire application locally via Docker Compose (with `DEPLOYMENT_ENV=local` so scraper endpoints are enabled):

```cmd
docker compose up --build -d
```

Check application health:

```cmd
curl http://localhost:8080/health
```

Stop container:

```cmd
docker compose down
```

---

## Google Cloud Run Deployment

### 1. Initial Setup via gcloud CLI

```cmd
gcloud config set project shopbuddy-504620
gcloud services enable run.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com cloudbuild.googleapis.com
```

### 2. Create Artifact Registry Repository

```cmd
gcloud artifacts repositories create shopbuddy-repo --repository-format=docker --location=asia-south1 --description="ShopBuddy Docker images"
```

### 3. Store Secrets in Secret Manager

```cmd
echo YOUR_GOOGLE_API_KEY | gcloud secrets create GOOGLE_API_KEY --data-file=- --replication-policy=automatic
echo YOUR_ASTRA_DB_API_ENDPOINT | gcloud secrets create ASTRA_DB_API_ENDPOINT --data-file=- --replication-policy=automatic
echo YOUR_ASTRA_DB_APPLICATION_TOKEN | gcloud secrets create ASTRA_DB_APPLICATION_TOKEN --data-file=- --replication-policy=automatic
echo YOUR_ASTRA_DB_KEYSPACE | gcloud secrets create ASTRA_DB_KEYSPACE --data-file=- --replication-policy=automatic
```

### 4. Create Service Account & Grant Permissions

```cmd
gcloud iam service-accounts create github-actions-deployer --display-name="GitHub Actions Cloud Run Deployer"

gcloud projects add-iam-policy-binding shopbuddy-504620 --member="serviceAccount:github-actions-deployer@shopbuddy-504620.iam.gserviceaccount.com" --role="roles/run.admin"
gcloud projects add-iam-policy-binding shopbuddy-504620 --member="serviceAccount:github-actions-deployer@shopbuddy-504620.iam.gserviceaccount.com" --role="roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding shopbuddy-504620 --member="serviceAccount:github-actions-deployer@shopbuddy-504620.iam.gserviceaccount.com" --role="roles/iam.serviceAccountUser"
gcloud projects add-iam-policy-binding shopbuddy-504620 --member="serviceAccount:github-actions-deployer@shopbuddy-504620.iam.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding shopbuddy-504620 --member="serviceAccount:672313940192-compute@developer.gserviceaccount.com" --role="roles/secretmanager.secretAccessor"
```

### 5. Generate Key JSON

```cmd
gcloud iam service-accounts keys create key.json --iam-account=github-actions-deployer@shopbuddy-504620.iam.gserviceaccount.com
```

---

## CI/CD Pipeline

The repository includes a GitHub Actions workflow (`.github/workflows/deploy.yml`) that automatically builds and deploys the container to **Google Cloud Run** whenever changes are pushed to the `main` branch.

**Required GitHub Repository Secrets:**

| Secret Name | Description |
|---|---|
| `GCP_SA_KEY` | Contents of `key.json` service account private key |
| `GCP_PROJECT_ID` | GCP Project ID (`shopbuddy-504620`) |

---

## Environment Variables

| Variable | Required | Description | Default |
|---|---|---|---|
| `GOOGLE_API_KEY` | Yes | API key for Google Gemini (LLM and embeddings) | - |
| `ASTRA_DB_API_ENDPOINT` | Yes | DataStax AstraDB REST API endpoint | - |
| `ASTRA_DB_APPLICATION_TOKEN` | Yes | DataStax AstraDB application token | - |
| `ASTRA_DB_KEYSPACE` | Yes | AstraDB keyspace (namespace) to use | `default_keyspace` |
| `DEPLOYMENT_ENV` | No | Set to `gcp` on Cloud Run to gate local-only features | `local` |
| `PORT` | No | Web server port injected by Cloud Run or local server | `8080` |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature-name`)
3. Commit your changes (`git commit -m 'Add feature: your-feature-name'`)
4. Push to the branch (`git push origin feature/your-feature-name`)
5. Open a Pull Request

---

**Author:** Syed Areeb Ahmad — [ahmad.syedareeb7@gmail.com](mailto:ahmad.syedareeb7@gmail.com)
