import os
import shutil
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

from ingestion import DocumentIngester
from retriever import HybridRetriever
from llm_manager import LLMManager
from evaluator import RAGEvaluator

# Initialize FastAPI application
app = FastAPI(
    title="RAG Document Q&A REST API",
    description="Production-grade, evaluation-first RAG pipeline backend exposing indexing and hybrid Q&A endpoints.",
    version="1.0.0"
)

# Enable CORS for all domains to allow direct frontend integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files folder
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def read_root():
    """
    Serves the premium Apple.com-style UI frontend.
    """
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>RAG OS Apple Frontend index.html not found! Check directory paths.</h1>"

# Initialize core pipeline modules
ingester = DocumentIngester()
retriever = HybridRetriever()
llm = LLMManager()
evaluator = RAGEvaluator(llm_manager=llm)

# Define directories
UPLOAD_DIR = "./temp_uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Pydantic data schemas
class QueryRequest(BaseModel):
    query: str
    top_k: int = 5
    enable_rerank: bool = True
    gemini_key: Optional[str] = None
    openai_key: Optional[str] = None
    chat_history: Optional[List[dict]] = None  # List of {"role": "user"|"assistant", "content": str}

class QueryResponse(BaseModel):
    query: str
    answer: str
    citations: List[str]
    retrieved_chunks: List[dict]
    evaluations: dict
    provider: str

@app.get("/health")
def health_check():
    """
    Basic health check endpoint.
    """
    return {
        "status": "healthy",
        "llm_provider": llm.provider,
        "database_connected": ingester.index is not None and ingester.supabase is not None
    }

@app.get("/status")
def system_status():
    """
    Fetches database corpus stats (total files, total chunks, document details).
    """
    try:
        stats = ingester.get_stats()
        return {
            "status": "success",
            "stats": stats,
            "provider": llm.provider
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking status: {str(e)}")

def _process_upload_in_background(temp_file_paths: List[str], filenames: List[str], chunk_size: int, chunk_overlap: int):
    """Background task to process files, chunk them, and upload to Pinecone/Supabase without blocking the HTTP request."""
    for temp_file_path, filename in zip(temp_file_paths, filenames):
        try:
            file_ext = os.path.splitext(filename)[1].lower()
            if file_ext == ".pdf":
                raw_docs = ingester.load_pdf(temp_file_path)
            else:
                raw_docs = ingester.load_txt(temp_file_path)
                
            if raw_docs:
                chunks = ingester.split_text(raw_docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
                ingester.add_documents(chunks)
        except Exception as e:
            print(f"Background processing error for {filename}: {str(e)}")
        finally:
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

@app.post("/upload")
async def upload_documents(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...), 
    chunk_size: int = Form(500), 
    chunk_overlap: int = Form(50)
):
    """
    Receives PDF/TXT documents, saves them to temp files, and schedules them for background processing.
    """
    temp_paths = []
    filenames = []
    
    for upload_file in files:
        file_ext = os.path.splitext(upload_file.filename)[1].lower()
        if file_ext not in [".pdf", ".txt"]:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {upload_file.filename}. Only PDF and TXT are supported.")
            
        temp_file_path = os.path.join(UPLOAD_DIR, upload_file.filename)
        
        try:
            with open(temp_file_path, "wb") as buffer:
                shutil.copyfileobj(upload_file.file, buffer)
            temp_paths.append(temp_file_path)
            filenames.append(upload_file.filename)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save file: {upload_file.filename}. Error: {str(e)}")
            
    # Dispatch to background task
    background_tasks.add_task(_process_upload_in_background, temp_paths, filenames, chunk_size, chunk_overlap)
    
    return {
        "status": "success",
        "message": f"Successfully received {len(files)} document(s). Processing in the background...",
        "processed_files": filenames,
        "db_stats": ingester.get_stats()
    }

@app.post("/clear")
def clear_corpus():
    """
    Clears all documents from the vector database.
    """
    try:
        ingester.clear_database()
        # Re-initialize hybrid retriever to bind to clean database
        global retriever
        retriever = HybridRetriever()
        return {"status": "success", "message": "Corpus successfully wiped. Vector DB collection re-initialized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to wipe collection: {str(e)}")

@app.post("/query", response_model=QueryResponse)
def execute_query(request: QueryRequest):
    """
    Runs full RAG Query pipeline:
    1. Hybrid retrieval (dense + sparse keyword search)
    2. Reciprocal Rank Fusion
    3. Cross-Encoder Reranking
    4. Inline-citations LLM generation
    5. Faithfulness & Relevance evaluations
    """
    try:
        # Dynamically inject keys if provided in requests (useful for dynamic frontend)
        if request.gemini_key or request.openai_key:
            llm.set_keys(gemini_key=request.gemini_key, openai_key=request.openai_key)
            
        # 1. Retrieve top context candidates
        retrieved_chunks = retriever.retrieve(
            query=request.query,
            top_k=request.top_k,
            enable_rerank=request.enable_rerank
        )
        
        if not retrieved_chunks:
            return QueryResponse(
                query=request.query,
                answer="No documents are currently indexed in the system. Please upload TXT or PDF documents first.",
                citations=[],
                retrieved_chunks=[],
                evaluations={
                    "faithfulness": {"score": 0.0, "explanation": "No context available."},
                    "context_relevance": {"score": 0.0, "explanation": "No context retrieved."},
                    "answer_relevance": {"score": 0.0, "explanation": "Query could not be answered."},
                    "average_score": 0.0
                },
                provider=llm.provider
            )
            
        # 2. LLM response generation (with conversation memory)
        generation_results = llm.generate_answer(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            chat_history=request.chat_history
        )
        
        answer = generation_results["answer"]
        citations = generation_results["citations"]
        
        # 3. LLM-as-a-judge automated evaluation
        evaluations = evaluator.run_all_evaluations(
            query=request.query,
            retrieved_chunks=retrieved_chunks,
            answer=answer
        )
        
        return QueryResponse(
            query=request.query,
            answer=answer,
            citations=citations,
            retrieved_chunks=retrieved_chunks,
            evaluations=evaluations,
            provider=llm.provider
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute Q&A query: {str(e)}")

def start(port: int = 8000):
    """
    Utility method to boot up Uvicorn.
    """
    uvicorn.run("api:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    start()
