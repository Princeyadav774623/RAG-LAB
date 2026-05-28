import os
import re
import uuid
from typing import List, Dict, Any, Optional
import pypdf
from pinecone import Pinecone, ServerlessSpec
from supabase import create_client, Client
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class DocumentIngester:
    def __init__(self, index_name: str = "rag-documents"):
        """
        Initializes the document ingestion pipeline.
        Connects to Pinecone (Vector Search) and Supabase (Full-text/Metadata).
        """
        self.index_name = index_name
        
        # Initialize Gemini API for Embeddings
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
        else:
            print("WARNING: GEMINI_API_KEY not set for embeddings")
        
        # Initialize Pinecone
        pinecone_key = os.environ.get("PINECONE_API_KEY")
        if pinecone_key:
            self.pc = Pinecone(api_key=pinecone_key)
            
            # Check if index exists, create if not (768 dims for Gemini text-embedding-004)
            existing_indexes = [index_info["name"] for index_info in self.pc.list_indexes()]
            if self.index_name not in existing_indexes:
                print(f"Creating Pinecone index '{self.index_name}'...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=768,
                    metric="cosine",
                    spec=ServerlessSpec(cloud='aws', region='us-east-1')
                )
            self.index = self.pc.Index(self.index_name)
        else:
            self.pc = None
            self.index = None
            print("WARNING: PINECONE_API_KEY not set in .env")

        # Initialize Supabase
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_KEY")
        if supabase_url and supabase_key:
            self.supabase: Client = create_client(supabase_url, supabase_key)
        else:
            self.supabase = None
            print("WARNING: SUPABASE_URL and SUPABASE_KEY not set in .env")

    def load_pdf(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        filename = os.path.basename(file_path)
        documents = []
        
        try:
            reader = pypdf.PdfReader(file_path)
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text and text.strip():
                    documents.append({
                        "text": text,
                        "metadata": {
                            "source": filename,
                            "page": page_num + 1,
                            "type": "pdf"
                        }
                    })
        except Exception as e:
            print(f"Error reading PDF {file_path}: {e}")
            
        return documents

    def load_txt(self, file_path: str) -> List[Dict[str, Any]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        filename = os.path.basename(file_path)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text = f.read()
            if text.strip():
                return [{
                    "text": text,
                    "metadata": {
                        "source": filename,
                        "page": 1,
                        "type": "txt"
                    }
                }]
        except Exception as e:
            print(f"Error reading TXT {file_path}: {e}")
            
        return []

    def split_text(self, documents: List[Dict[str, Any]], chunk_size: int = 500, chunk_overlap: int = 50) -> List[Dict[str, Any]]:
        chunks = []
        for doc in documents:
            text = doc["text"]
            metadata = doc["metadata"]
            
            raw_chunks = self._recursive_split(text, chunk_size, chunk_overlap)
            
            for idx, text_chunk in enumerate(raw_chunks):
                if text_chunk.strip():
                    chunk_metadata = metadata.copy()
                    chunk_metadata["chunk_index"] = idx
                    chunks.append({
                        "text": text_chunk,
                        "metadata": chunk_metadata
                    })
        return chunks

    def _recursive_split(self, text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        separators = ["\n\n", "\n", ". ", " ", ""]
        return self._split_on_separators(text, separators, chunk_size, chunk_overlap)

    def _split_on_separators(self, text: str, separators: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
        if len(text) <= chunk_size or not separators:
            return [text]
            
        separator = separators[0]
        next_separators = separators[1:]
        
        if separator == "":
            splits = list(text)
        elif separator == ". ":
            splits = [s + "." for s in text.split(". ") if s]
        else:
            splits = text.split(separator)
            
        chunks = []
        current_chunk = []
        current_len = 0
        
        for part in splits:
            part_len = len(part)
            if part_len > chunk_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                    current_chunk = []
                    current_len = 0
                sub_chunks = self._split_on_separators(part, next_separators, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks)
                continue
                
            if current_len + part_len + (len(separator) if current_chunk else 0) > chunk_size:
                if current_chunk:
                    chunks.append(separator.join(current_chunk))
                
                overlap_chunk = []
                overlap_len = 0
                for prev_part in reversed(current_chunk):
                    prev_len = len(prev_part) + (len(separator) if overlap_chunk else 0)
                    if overlap_len + prev_len <= chunk_overlap:
                        overlap_chunk.insert(0, prev_part)
                        overlap_len += prev_len
                    else:
                        break
                        
                current_chunk = overlap_chunk + [part]
                current_len = overlap_len + part_len + (len(separator) if overlap_chunk else 0)
            else:
                current_chunk.append(part)
                current_len += part_len + (len(separator) if len(current_chunk) > 1 else 0)
                
        if current_chunk:
            chunks.append(separator.join(current_chunk))
            
        return chunks

    def add_documents(self, chunks: List[Dict[str, Any]]) -> int:
        if not chunks:
            return 0
            
        if not self.index or not self.supabase:
            raise Exception("Cannot insert documents: Pinecone or Supabase is not configured properly.")
            
        texts = [chunk["text"] for chunk in chunks]
        
        # Generate embeddings via Gemini API
        try:
            embed_response = genai.embed_content(
                model="models/gemini-embedding-2",
                content=texts,
                output_dimensionality=768
            )
            embeddings = embed_response['embedding']
            
            # If the API returned a single dictionary (only 1 chunk) instead of a list, fix it
            if not isinstance(embeddings[0], list):
                embeddings = [embeddings]
        except Exception as e:
            raise Exception(f"Gemini API Embedding Error: {str(e)}")
        
        pinecone_vectors = []
        supabase_records = []
        
        for i, chunk in enumerate(chunks):
            # Unique ID for both databases
            doc_id = str(uuid.uuid4())
            meta = chunk["metadata"]
            
            # Prepare Pinecone vector (ID, embedding, basic metadata)
            pinecone_vectors.append({
                "id": doc_id,
                "values": embeddings[i],
                "metadata": {
                    "source": meta.get("source", ""),
                    "page": meta.get("page", 1),
                    "chunk_index": meta.get("chunk_index", 0)
                }
            })
            
            # Prepare Supabase record (Full text for BM25 search)
            supabase_records.append({
                "id": doc_id,
                "source": meta.get("source", ""),
                "page": meta.get("page", 1),
                "chunk_index": meta.get("chunk_index", 0),
                "content": texts[i]
            })
            
        # Batch upsert to Supabase
        try:
            self.supabase.table('documents').insert(supabase_records).execute()
        except Exception as e:
            raise Exception(f"Failed to insert into Supabase: {e}")
            
        # Batch upsert to Pinecone
        try:
            self.index.upsert(vectors=pinecone_vectors)
        except Exception as e:
            raise Exception(f"Failed to upsert to Pinecone: {e}")
        
        return len(chunks)

    def clear_database(self):
        if self.index:
            try:
                self.index.delete(delete_all=True)
            except Exception as e:
                print(f"Warning: Could not clear Pinecone: {e}")
        
        if self.supabase:
            try:
                # In Supabase REST API, deleting all requires a filter. 
                # e.g., filter where id is not null.
                self.supabase.table('documents').delete().neq('page', -1).execute() # Dummy filter matching all
            except Exception as e:
                print(f"Warning: Could not clear Supabase: {e}")

    def get_stats(self) -> Dict[str, Any]:
        stats = {"total_chunks": 0, "unique_documents": 0, "documents": []}
        if self.index:
            try:
                pinecone_stats = self.index.describe_index_stats()
                stats["total_chunks"] = pinecone_stats.total_vector_count
            except Exception:
                pass
                
        if self.supabase:
            try:
                # Get unique sources from Supabase
                response = self.supabase.table('documents').select('source').execute()
                sources = [row['source'] for row in response.data]
                unique_docs = set(sources)
                doc_details = {}
                for src in sources:
                    doc_details[src] = doc_details.get(src, 0) + 1
                    
                stats["unique_documents"] = len(unique_docs)
                stats["documents"] = [{"filename": k, "chunks": v} for k, v in doc_details.items()]
            except Exception:
                pass
                
        return stats

if __name__ == "__main__":
    print("Initializing DocumentIngester test...")
    try:
        ingester = DocumentIngester()
        print("Database connected. Stats:", ingester.get_stats())
    except Exception as e:
        print("Initialization failed:", e)
