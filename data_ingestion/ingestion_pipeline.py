import os
import time
import hashlib
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
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(base_dir, 'data', 'product_reviews.csv')

        if not os.path.exists(csv_path):
            current_dir = os.getcwd()
            csv_path = os.path.join(current_dir, 'data', 'product_reviews.csv')

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"CSV file not found at: {csv_path}")

        return csv_path

    def _load_csv(self):
        """
        Load product data from CSV.
        """
        df = pd.read_csv(self.csv_path)
        if 'top_reviews' not in df.columns:
            raise ValueError(f"CSV must contain 'top_reviews' column. Found columns: {list(df.columns)}")

        return df

    def transform_data(self):
        """
        Transform product data into list of LangChain Document objects.
        """
        documents = []

        for _, row in self.product_data.iterrows():
            review_content = str(row['top_reviews']) if pd.notna(row['top_reviews']) else ""
            if not review_content.strip() or any(invalid in review_content for invalid in ["No reviews found", "Invalid product URL", "Sorry, no results found"]):
                continue

            metadata = {
                "product_name": str(row.get('product_title', '')),
                "product_rating": str(row.get('rating', '')),
                "price": str(row.get('price', '')),
                "total_reviews": str(row.get('total_reviews', '')),
                "product_id": str(row.get('product_id', ''))
            }

            doc = Document(page_content=review_content, metadata=metadata)
            documents.append(doc)

        print(f"Transformed {len(documents)} documents.")
        return documents

    def store_in_vector_db(self, documents: List[Document]):
        """
        Store documents into AstraDB vector store with deterministic document IDs for UPSERT deduplication.
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

            # Generate deterministic document IDs to enforce native AstraDB UPSERT behavior
            batch_ids_keys = []
            for doc in batch:
                pid = str(doc.metadata.get("product_id", "")).strip()
                if not pid or pid in ["N/A", "nan"]:
                    pname = str(doc.metadata.get("product_name", "")).strip()
                    pid = f"doc_{hashlib.md5(pname.encode('utf-8')).hexdigest()}"
                batch_ids_keys.append(pid)

            print(f"Inserting batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1} ({len(batch)} documents)...")
            batch_ids = vstore.add_documents(batch, ids=batch_ids_keys)
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