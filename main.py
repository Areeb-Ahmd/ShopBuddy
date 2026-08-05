import os
import csv
from typing import List, Optional
import uvicorn 
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from retriever.retrieval import Retriever
from utils.model_loader import ModelLoader
from prompt_library.prompt import PROMPT_TEMPLATES
from data_scrapper.scrape_data import scrape_flipkart_products, save_to_csv
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
retriever_obj = Retriever()
model_loader = ModelLoader()

class ScrapeRequest(BaseModel):
    product_inputs: List[str]
    product_description: Optional[str] = ""
    max_products: int = 1
    review_count: int = 2

def invoke_chain(query:str):
    retriever = retriever_obj.load_retriever()
    prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATES["product_bot"])
    llm = model_loader.load_llm()
    
    chain=(
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
    output = chain.invoke(query)
    return output

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """
    Render the unified portal interface.
    """
    return templates.TemplateResponse(request=request, name="chat.html")

@app.post("/get", response_class=HTMLResponse)
async def chat(msg:str=Form(...)):
    result = invoke_chain(msg)
    print(f'Response: {result}')
    return result

@app.post("/api/scrape")
async def scrape_products(payload: ScrapeRequest):
    """
    Trigger product review scraping from Flipkart.
    """
    try:
        search_queries = [p.strip() for p in payload.product_inputs if p.strip()]
        if payload.product_description and payload.product_description.strip():
            search_queries.append(payload.product_description.strip())

        if not search_queries:
            raise HTTPException(status_code=400, detail="Please enter at least one product name or description.")

        final_data = []
        for query in search_queries:
            results = scrape_flipkart_products(query, max_products=payload.max_products, review_count=payload.review_count)
            final_data.extend(results)

        # Deduplicate products by product title/link
        unique_products = {}
        for row in final_data:
            if len(row) > 1 and row[1] not in unique_products:
                unique_products[row[1]] = row

        scraped_list = list(unique_products.values())
        os.makedirs("data", exist_ok=True)
        csv_output_path = "data/product_reviews.csv"
        save_to_csv(scraped_list, csv_output_path)

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
    try:
        ingestion = DataIngestion()
        inserted_count = ingestion.run_pipeline()
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
    csv_path = "data/product_reviews.csv"
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="CSV file not found. Please run scraper first.")
    return FileResponse(path=csv_path, filename="product_reviews.csv", media_type="text/csv")