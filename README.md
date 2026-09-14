# RAG Lab

Production document question answering — hybrid retrieval, cross-encoder reranking, and an
evaluation loop that scores every answer against the context it was built from.

![Architecture](docs/architecture.png)

---

## Why this exists

A retrieval system will always return something. Ask it a question and it hands back passages
ranked by similarity, and a language model turns those passages into fluent prose. Nothing in
that pipeline tells you whether the answer was *earned* — whether it came from the documents
or from the model's own priors.

RAG Lab closes that gap in two places:

- **Retrieval is hybrid, not semantic-only.** Dense vector search finds passages that *mean* the
  same thing; sparse full-text search catches exact terms, product codes and names that
  embeddings routinely miss. Their rankings are merged with Reciprocal Rank Fusion, which needs
  no tuned weight between the two, then reordered by a cross-encoder that reads each candidate
  against the question directly.
- **Every answer is graded.** A second model scores the response for groundedness, context
  relevance and answer relevance on a 0.0–1.0 scale and writes down its reasoning. The scores
  come back with the answer, not in a separate offline report.

## Pipeline

| Stage | What happens | Implementation |
|---|---|---|
| **Ingest** | Parse PDF/TXT page by page, split into passages with page metadata preserved | `ingestion.py` · pypdf · recursive splitter |
| **Embed** | Vectorise through a cloud API so the server never loads an embedding model | `genai.embed_content` · `gemini-embedding-2` · 768-dim |
| **Index** | Vectors to Pinecone, text to Supabase full-text | `ingestion.py` |
| **Retrieve** | Dense and sparse search in parallel, fused by RRF | `retriever.py` · Pinecone + Supabase/BM25 |
| **Rerank** | Cross-encoder reorders candidates by true relevance | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Generate** | Answer strictly from retrieved passages, with citations enforced by the prompt | `llm_manager.py` · Gemini / GPT-4o |
| **Judge** | Score the answer against its own retrieved context | `evaluator.py` |

### The memory constraint

The embedding step is the reason this deploys at all. A local `BAAI/bge-base-en-v1.5` needs
over 1 GB of RAM to load, which kills the process instantly on a 512 MB free tier. Moving
embedding to the Gemini API drops the server's footprint below 100 MB — the vector maths happens
on Google's hardware, and the web process only ever holds text and HTTP.

That single decision is what makes the difference between a system that runs on a laptop and
one that runs in production for free.

## Quickstart

```bash
git clone https://github.com/Princeyadav774623/RAG-LAB.git
cd RAG-LAB
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then fill in the keys below
uvicorn api:app --reload --port 8000
```

The API is then at `http://localhost:8000`. `main.py` runs the same pipeline from the terminal,
and `static/index.html` is a dependency-free console that talks to the running API.

### Next.js frontend

```bash
cd frontend
npm install
npm run dev
```

Next.js 16 / React 19 / TypeScript, with a chat console, an upload panel and live evaluation
gauges.

## Configuration

All five are required. Copy `.env.example` to `.env` and fill it in.

| Variable | Used for |
|---|---|
| `GEMINI_API_KEY` | Embeddings and generation |
| `OPENAI_API_KEY` | Alternative generation provider |
| `PINECONE_API_KEY` | Dense vector index |
| `SUPABASE_URL` | Text store and full-text search |
| `SUPABASE_KEY` | Text store and full-text search |

Run `init_db.sql` against your Supabase project once to create the tables and the full-text index.

## API

| Method | Route | Purpose |
|---|---|---|
| `POST` | `/query` | Ask a question. Returns the answer, its citations and its evaluation scores |
| `POST` | `/upload` | Ingest a document into both indexes |
| `POST` | `/clear` | Empty the indexes |
| `GET` | `/status` | Index state and document count |
| `GET` | `/health` | Liveness check |

## Project structure

```
api.py            FastAPI application and routes
ingestion.py      Parsing, chunking, embedding, indexing
retriever.py      Hybrid search, RRF, cross-encoder reranking
llm_manager.py    Provider clients, prompt construction, citation mapping
evaluator.py      LLM-as-a-judge scoring
main.py           Command-line entry point
verify_rag.py     End-to-end integration test
init_db.sql       Supabase schema and full-text index
frontend/         Next.js 16 + React 19 + TypeScript interface
static/           Dependency-free HTML/JS console
```

## Evaluation

`verify_rag.py` runs the whole path end to end — ingests sample pages, searches, generates a
cited answer, and scores it. On its sample corpus it reports groundedness 0.95, context
relevance 0.90 and answer relevance 0.95.

```bash
python verify_rag.py
```

## Deployment

`render.yaml` defines a Docker web service on Render's free tier. `start.sh` runs uvicorn with
two workers. The five environment variables above must be set in the Render dashboard.

## Limitations

Worth stating plainly:

- **Evaluation is model-graded, not human-labelled.** The scores measure self-consistency
  between answer and retrieved context. They are a useful regression signal, not ground truth.
- **The reported scores come from a sample corpus**, not a held-out benchmark.
- **Free-tier cold starts.** The Render instance sleeps when idle; the first request after a
  sleep is slow.
- **`chroma_db/` is local-development only.** Production retrieval runs on Pinecone and Supabase.
- Chunking is tuned for prose. Tables and multi-column PDFs are extracted, but not well.

## License

MIT — see [LICENSE](LICENSE).
