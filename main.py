import os
import csv
import asyncio
from typing import List, Optional
import uvicorn 
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from retriever.chain_loader import ChainLoader
from data_ingestion.ingestion_pipeline import DataIngestion

app = FastAPI(title="ShopBuddy - Unified E-Commerce Assistant")


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()
chain_loader = ChainLoader()

def is_cloud_deployment() -> bool:
    """Check if running on cloud (GCP Cloud Run)."""
    return os.environ.get("DEPLOYMENT_ENV", "local").lower() == "gcp"

class ScrapeRequest(BaseModel):
    product_inputs: List[str]
    product_description: Optional[str] = ""
    max_products: int = Field(default=1, ge=1, le=10, description="Max products per search query (1 to 10)")
    review_count: int = Field(default=2, ge=1, le=10, description="Reviews per product (1 to 10)")

def invoke_chain(query: str):
    return chain_loader.invoke(query)

@app.get("/health")
async def health_check():
    """
    Health check endpoint for Cloud Run liveness probes.
    """
    return {"status": "healthy", "service": "shopbuddy"}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render the unified portal interface.
    """
    return templates.TemplateResponse(request=request, name="chat.html")

@app.post("/get", response_class=HTMLResponse)
async def chat(msg: str = Form(...)):
    result = await asyncio.to_thread(invoke_chain, msg)
    print(f'Response: {result}')
    return result

@app.post("/api/scrape")
async def scrape_products(payload: ScrapeRequest):
    """
    Trigger product review scraping from Flipkart.
    """
    if is_cloud_deployment():
        raise HTTPException(
            status_code=403,
            detail="This feature is only available when running locally. Please run ShopBuddy on your local machine to use the scraper and data pipeline."
        )

    from data_scrapper.scrape_data import run_scrape_workflow

    try:
        search_queries = [p.strip() for p in payload.product_inputs if p.strip()]
        if payload.product_description and payload.product_description.strip():
            search_queries.append(payload.product_description.strip())

        if not search_queries:
            raise HTTPException(status_code=400, detail="Please enter at least one product name or description.")

        scraped_list = await asyncio.to_thread(
            run_scrape_workflow, search_queries, payload.max_products, payload.review_count
        )

        return {
            "status": "success",
            "message": f"Successfully scraped {len(scraped_list)} products.",
            "count": len(scraped_list),
            "data": scraped_list
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scraping failed: {str(e)}")

@app.post("/api/ingest")
async def ingest_vector_db():
    """
    Run data ingestion pipeline to store CSV reviews into AstraDB.
    """
    if is_cloud_deployment():
        raise HTTPException(
            status_code=403,
            detail="This feature is only available when running locally. Please run ShopBuddy on your local machine to use the scraper and data pipeline."
        )

    try:
        ingestion = DataIngestion()
        inserted_count = await asyncio.to_thread(ingestion.run_pipeline)
        return {
            "status": "success",
            "message": f"Data successfully ingested into AstraDB! ({inserted_count} document batches processed)",
            "inserted_count": inserted_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@app.get("/api/reviews")
async def get_reviews():
    """
    Return scraped reviews from product_reviews.csv for HTML table rendering.
    """
    if is_cloud_deployment():
        raise HTTPException(
            status_code=403,
            detail="This feature is only available when running locally. Please run ShopBuddy on your local machine to use the scraper and data pipeline."
        )

    csv_path = "data/product_reviews.csv"
    if not os.path.exists(csv_path):
        return {"status": "empty", "reviews": []}

    reviews = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                reviews.append(row)
        return {"status": "success", "reviews": reviews}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read reviews CSV: {str(e)}")

@app.get("/api/download")
async def download_csv():
    """
    Download product_reviews.csv file.
    """
    if is_cloud_deployment():
        raise HTTPException(
            status_code=403,
            detail="This feature is only available when running locally. Please run ShopBuddy on your local machine to use the scraper and data pipeline."
        )

    csv_path = "data/product_reviews.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file not found. Please run scraper first.")
    return FileResponse(path=csv_path, filename="product_reviews.csv", media_type="text/csv")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port)