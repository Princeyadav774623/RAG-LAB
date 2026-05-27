# 🚀 Production-Grade RAG Document Q&A Portfolio System

An enterprise-grade, evaluation-first **Retrieval-Augmented Generation (RAG)** pipeline designed for multi-format document Q&A. This system moves away from basic "vibe-based" AI development by implementing **Hybrid Multi-Stage Retrieval**, **Cross-Encoder Reranking**, **Strict Citation Grounding**, and a **Self-Contained LLM-as-a-Judge Evaluation Suite** that measures Faithfulness, Context Relevance, and Answer Relevance in real-time.

Features a beautiful, highly interactive **Streamlit Dashboard** and a production-ready **FastAPI REST API**.

---

## 🛠️ System Architecture

The pipeline consists of two distinct workflows: the **Offline Ingestion & Indexing Pipeline** and the **Online Query, Rerank, & Evaluation Pipeline**.

### 1. Ingestion Pipeline (Offline)
```
[Raw PDFs / TXT] ──> [Recursive Parser (Page Tracking)] ──> [Overlapping Recursive Chunking]
                                                                      │
                                                                      ▼
[ChromaDB Vector Store] <── [Local dense embeddings (all-MiniLM-L6)] ─┘
```

### 2. Query, Reranking & Evaluation Pipeline (Online)
```
[User Question] 
       │
       ├─► [Dense Semantic Search] ──► Query ChromaDB (Top 20 Matches) ──┐
       │                                                                 ▼
       └─► [Sparse Keyword Search] ──► Local BM25 Index (Top 20 Matches) ─┼─► [Reciprocal Rank Fusion (RRF)]
                                                                         │                │
[User Answer] <── [LLM Generation with Citations] <── [Cross-Encoder Reranker] <─────────┘
      │                                                (ms-marco-MiniLM-L-6-v2)
      ▼
[Automated Evaluation Suite] (LLM-as-a-Judge) ──► Faithfulness, Context & Answer Relevance Metrics
```

---

## 🌟 Key Technical Highlights

1. **Hybrid Retrieval (Dense + Sparse)**: Combines semantic embeddings (ChromaDB + SentenceTransformers `all-MiniLM-L6-v2`) with lexical matches (`BM25Okapi`), ensuring that exact terms, codes, and conceptual semantics are captured.
2. **Reciprocal Rank Fusion (RRF)**: Leverages the reciprocal positions of search candidates across dense and sparse algorithms to unify rankings.
3. **Cross-Encoder Reranking**: Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` locally to grade candidate text-segments directly against the user query, resolving the limitation where standard vector distances retrieve out-of-context paragraphs.
4. **Citations & Anti-Hallucination**: The LLM prompt is structurally engineered to force grounded statements. Citations are extracted and highlighted as badge links in the UI, pointing to the exact page and document name.
5. **Standalone Evaluation suite**: Evaluates system answers instantly using an LLM-as-a-judge method, grading Groundedness, Context Relevance, and Answer Relevance (0.0 to 1.0) with detailed reasoning.

---

## 📁 Repository Directory Structure

*   `app.py`: Premium interactive visual Streamlit dashboard.
*   `api.py`: Production FastAPI REST server exposing indexing, Q&A, and health endpoints.
*   `ingestion.py`: Document loading, page-aware recursive chunk splitters, and local ChromaDB integrations.
*   `retriever.py`: Hybrid search, RRF scoring, and local Cross-Encoder reranker.
*   `llm_manager.py`: Connects Gemini & OpenAI APIs, handles generation prompts, and provides an offline fallback demo mode.
*   `evaluator.py`: Real-time RAG metric scoring system.
*   `main.py`: Command Line Interface launcher.
*   `verify_rag.py`: Automated end-to-end integration testing suite.
*   `requirements.txt`: Python package dependencies.
*   `.env`: Local environment configuration keys.

---

## 🚀 Installation & Setup

Ensure you have **Python 3.10 to 3.13** installed.

### 1. Clone & Navigate
```bash
cd /Users/princeyadav/Documents/RAG_full
```

### 2. Configure Virtual Environment & Packages
```bash
# Create virtual environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Add API Credentials
Create or edit the `.env` file in the root directory:
```env
GEMINI_API_KEY=your_google_gemini_api_key
OPENAI_API_KEY=your_openai_api_key
```
*Note: If no API key is specified, the system will seamlessly fall back to **Offline Demo Mode**, permitting you to upload documents, perform hybrid search, run rerankers, and inspect metrics locally without charging any tokens.*

---

## 🕹️ How to Run

Activate the virtual environment first (`source .venv/bin/activate`).

### Run Streamlit Dashboard UI
```bash
python main.py --ui
```
*   **Default Port**: `8501`
*   **Usage**: Drag and drop PDF or TXT documents under the "Ingestion Manager" tab, adjust chunk sizes, and start chatting. Inspect vector retrieval rankings and judge critiques in the right sidebar.

### Run FastAPI REST Service
```bash
python main.py --api
```
*   **Default Port**: `8000`
*   **Documentation Swagger**: [http://localhost:8000/docs](http://localhost:8000/docs)
*   **Endpoints**:
    *   `POST /upload`: accepts multi-part file uploads.
    *   `POST /query`: runs Q&A + evaluation.
    *   `GET /status`: reports DB stats.
    *   `POST /clear`: wipes DB collection.

---

## 🧪 Automated Testing

We provide a self-contained integration test that spins up a mock vector index, ingests sample pages, searches queries, generates citation answers, and measures evaluation accuracy:

```bash
python verify_rag.py
```

### Successful Test Output Example:
```text
[*] Starting RAG End-to-End Pipeline Integration Verification...
[*] Initializing components...
[+] Created sample testing file: ./sample_antigravity_doc.txt
[*] Loading and parsing document...
[*] Chunking document...
[+] Created 6 chunks.
[*] Indexing chunks into local ChromaDB with embeddings...
[+] Successfully indexed 6 chunks.
[*] Querying Hybrid Search Retriever: 'Who designed Antigravity?'
[+] Retrieved 2 relevant chunks:
  Rank 1: sample_antigravity_doc.txt | Page 1 | CE Score: 8.2870 | RRF Score: 0.0328
  Rank 2: sample_antigravity_doc.txt | Page 1 | CE Score: -1.1990 | RRF Score: 0.0161
[*] Requesting LLM answer generation with inline citations...
[+] LLM Response:
--- ANSWER ---
We found matching details in the file sample_antigravity_doc.txt on page 1. The text segment discusses that Antigravity is an advanced agentic AI coding assistant designed by the Google DeepMind team [Source: sample_antigravity_doc.txt, page 1].
--------------
[+] Parsed Citations: ['sample_antigravity_doc.txt (Page 1)']
[*] Running LLM-as-a-judge automated pipeline evaluation...
[+] Evaluation Suite Scores:
  - Faithfulness (Groundedness): 0.95
  - Context Relevance: 0.90
  - Answer Relevance: 0.95
  - Combined RAG score: 0.93

[+] SUCCESS: All stages of the production RAG pipeline integrated and verified successfully!
```
