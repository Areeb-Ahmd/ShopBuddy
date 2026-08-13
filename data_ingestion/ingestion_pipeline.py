import os
import time
import pandas as pd
from dotenv import load_dotenv
from typing import List, Tuple
from langchain_core.documents import Document
from langchain_astradb import AstraDBVectorStore
from utils.model_loader import ModelLoader
from config.config_loader import load_config

class DataIngestion:
    """
    Class to handle data transformation and ingestion into AstraDB vector store.
    """

    def __init__(self):
        """
        Initialize environment variables, embedding model, and set CSV file path.
        """
        print("Initializing DataIngestion pipeline...")
        self.model_loader=ModelLoader()
        self._load_env_variables()
        self.csv_path = self._get_csv_path()
        self.product_data = self._load_csv()
        self.config=load_config()

    def _load_env_variables(self):
        """
        Load and validate required environment variables.
        """
        load_dotenv()
        
        required_vars = ["GOOGLE_API_KEY", "ASTRA_DB_API_ENDPOINT", "ASTRA_DB_APPLICATION_TOKEN", "ASTRA_DB_KEYSPACE"]
        
        missing_vars = [var for var in required_vars if os.getenv(var) is None]
        if missing_vars:
            raise EnvironmentError(f"Missing environment variables: {missing_vars}")
        
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.db_api_endpoint = os.getenv("ASTRA_DB_API_ENDPOINT")
        self.db_application_token = os.getenv("ASTRA_DB_APPLICATION_TOKEN")
        self.db_keyspace = os.getenv("ASTRA_DB_KEYSPACE")

       

    def _get_csv_path(self):
        """
        Get path to the CSV file located inside 'data' folder.
        """
        current_dir = os.getcwd()
        csv_path = os.path.join(current_dir, 'data', 'product_reviews.csv')

        if not os.path.exists(csv_path):
            csv_path = os.path.join(current_dir, 'data', 'flipkart_product_review.csv')

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")

        return csv_path

    def _load_csv(self):
        """
        Load product data from CSV.
        """
        df = pd.read_csv(self.csv_path)
        # Check for scraped format or legacy format
        is_scraped = 'top_reviews' in df.columns
        is_legacy = 'review' in df.columns

        if not (is_scraped or is_legacy):
            raise ValueError(f"CSV must contain either 'top_reviews' or 'review' column. Found columns: {list(df.columns)}")

        return df

    def transform_data(self):
        """
        Transform product data into list of LangChain Document objects (Option A).
        """
        documents = []

        is_scraped = 'top_reviews' in self.product_data.columns

        for _, row in self.product_data.iterrows():
            if is_scraped:
                review_content = str(row['top_reviews']) if pd.notna(row['top_reviews']) else ""
                if not review_content.strip() or review_content.strip() in ["No reviews found", "Invalid product URL"]:
                    continue

                metadata = {
                    "product_name": str(row.get('product_title', '')),
                    "product_rating": str(row.get('rating', '')),
                    "price": str(row.get('price', '')),
                    "total_reviews": str(row.get('total_reviews', '')),
                    "product_id": str(row.get('product_id', ''))
                }
            else:
                review_content = str(row['review']) if pd.notna(row['review']) else ""
                if not review_content.strip():
                    continue

                metadata = {
                    "product_name": str(row.get('product_title', '')),
                    "product_rating": str(row.get('rating', '')),
                    "product_summary": str(row.get('summary', ''))
                }

            doc = Document(page_content=review_content, metadata=metadata)
            documents.append(doc)

        print(f"Transformed {len(documents)} documents.")
        return documents

    def store_in_vector_db(self, documents: List[Document]):
        """
        Store documents into AstraDB vector store.
        """
        if not documents:
            print("No valid documents to store.")
            return None, []

        collection_name=self.config["astra_db"]["collection_name"]
        vstore = AstraDBVectorStore(
            embedding= self.model_loader.load_embeddings(),
            collection_name=collection_name,
            api_endpoint=self.db_api_endpoint,
            token=self.db_application_token,
            namespace=self.db_keyspace,
        )

        batch_size = 50
        inserted_ids = []
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            print(f"Inserting batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} ({len(batch)} documents)...")
            batch_ids = vstore.add_documents(batch)
            if batch_ids:
                inserted_ids.extend(batch_ids)
                
            if i + batch_size < len(documents):
                print("Waiting 60 seconds to avoid hitting API rate limits...")
                time.sleep(60)

        print(f"Successfully inserted {len(inserted_ids)} documents into AstraDB.")
        return vstore, inserted_ids

    def run_pipeline(self):
        """
        Run the full data ingestion pipeline: transform data and store into vector DB.
        """
        documents = self.transform_data()
        vstore, inserted_ids = self.store_in_vector_db(documents)
        return len(inserted_ids)

# Run if this file is executed directly
if __name__ == "__main__":
    ingestion = DataIngestion()
    ingestion.run_pipeline()