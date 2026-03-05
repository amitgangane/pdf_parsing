# RAG Research Paper Assistant

A full-stack Retrieval-Augmented Generation (RAG) system for uploading and querying research papers (PDFs). It parses PDFs including text, tables, and images, stores embeddings in OpenSearch, and answers questions using OpenAI or Ollama models.

---

## Architecture Overview

```
PDF Upload
    │
    ▼
FastAPI (api/)
    │
    ├── Saves PDF to disk
    ├── Creates session in PostgreSQL
    └── Runs ingestion as BackgroundTask
            │
            ▼
    Ingestion Pipeline (Ingestion/)
            │
            ├── partition_pdf()       ← unstructured: extract text, tables, images
            ├── process_images()      ← caption images via OpenAI Vision
            ├── process_tables()      ← describe tables via OpenAI
            ├── create_semantic_chunks() ← chunk text by title + semantics
            └── ingest_all_content_into_opensearch() ← embed + index
                        │
                        ▼
                  OpenSearch Index
                  (one per PDF session)
                        │
Query ──────────────────┘
    │
    ├── keyword_search / semantic_search / hybrid_search
    └── generate_rag_response() → OpenAI (gpt-4o-mini) or Ollama (llama2)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| PDF Parsing | Unstructured (hi_res strategy) |
| Vector Store | OpenSearch 2.11 |
| Embeddings | Ollama `embeddinggemma` (768-dim) |
| Generation | OpenAI `gpt-4o-mini` / Ollama `llama2` |
| Session Store | PostgreSQL 16 (via SQLAlchemy) |
| UI | Gradio 6 |
| Containers | Docker Compose (OpenSearch, OpenSearch Dashboards, PostgreSQL) |

---

## Project Structure

```
RAG-rp/
├── api/
│   ├── main.py               # FastAPI app entry point
│   ├── config.py             # Settings (pydantic-settings + .env)
│   ├── db.py                 # SQLAlchemy engine + SessionLocal
│   ├── crud.py               # DB helpers (create/get/update session)
│   ├── dependencies.py       # get_db() dependency
│   ├── models/
│   │   ├── orm.py            # SessionRecord ORM model
│   │   ├── requests.py       # Pydantic request schemas
│   │   └── responses.py      # Pydantic response schemas
│   └── routers/
│       ├── upload.py         # POST /upload/
│       ├── sessions.py       # GET /sessions/, GET /sessions/{id}
│       └── query.py          # POST /query/, POST /query/stream
├── Ingestion/
│   ├── chunking.py           # Semantic chunking, image/table processing
│   ├── ingestion.py          # OpenSearch indexing
│   ├── retrieval.py          # keyword / semantic / hybrid search
│   ├── generation.py         # RAG response generation (OpenAI + Ollama)
│   └── helper.py             # Shared utilities
├── paper/                    # Sample PDFs
├── docker-compose.yml        # OpenSearch + PostgreSQL
├── gradio_app.py             # Gradio UI
├── requirements.txt
└── .env                      # API keys and config (not committed)
```

---

## Setup

### 1. Prerequisites
- Python 3.10+
- Docker Desktop
- Ollama running locally with `embeddinggemma` model pulled

### 2. Clone and install
```bash
git clone <repo>
cd RAG-rp
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 3. Environment variables
Create a `.env` file in the project root:
```
OPENAI_API_KEY=sk-...
```

### 4. Start containers
```bash
docker-compose up -d
```
This starts:
- OpenSearch at `localhost:9200`
- OpenSearch Dashboards at `localhost:5601`
- PostgreSQL at `localhost:5433`

### 5. Pull embedding model (Ollama)
```bash
ollama pull embeddinggemma
```

---

## Running

**API server:**
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
Swagger docs: http://localhost:8000/docs

**Gradio UI:**
```bash
python gradio_app.py
```
UI: http://localhost:7860

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/upload/` | Upload PDF → 202, ingestion runs in background |
| GET | `/sessions/` | List all sessions |
| GET | `/sessions/{session_id}` | Get session status (`processing` / `ready` / `failed`) |
| POST | `/query/` | Blocking RAG query |
| POST | `/query/stream` | Streaming RAG query |
| GET | `/health` | Health check |

### Query request body
```json
{
  "session_id": "...",
  "question": "What problem does this paper solve?",
  "search_type": "hybrid",
  "model_type": "openai",
  "top_k": 5
}
```
- `search_type`: `keyword` | `semantic` | `hybrid`
- `model_type`: `openai` | `ollama`

---

## How Ingestion Works

1. **Upload** — PDF saved to `uploads/`, session created in PostgreSQL with status `processing`
2. **Parse** — `unstructured` partition_pdf extracts raw elements (text, tables, images) using `hi_res` strategy
3. **Process** — Images captioned and tables described via OpenAI Vision
4. **Chunk** — Text chunked by title (max 2000 chars) then semantically grouped
5. **Embed** — Each chunk embedded using Ollama `embeddinggemma` (768-dim)
6. **Index** — All chunks ingested into a dedicated OpenSearch index (`pdf_{session_id}`)
7. **Ready** — Session status updated to `ready` in PostgreSQL

---

## How Retrieval Works

Three search modes available:

- **Keyword** — BM25 full-text search on OpenSearch
- **Semantic** — KNN vector similarity search using embeddings
- **Hybrid** — Combines both with score normalization (recommended)

Retrieved chunks are assembled into a context window and passed to the LLM with a RAG prompt.

---

## Gradio UI Features

- **Upload tab** — Upload a PDF, monitor ingestion status with a polling button
- **Chat tab** — Select a ready session from dropdown, choose retrieval type and model, chat with streaming responses

---

## What's Next (Planned)

- [ ] **Celery + Redis** — Move ingestion out of FastAPI process into a dedicated worker for reliability and retry logic
- [ ] **Ingestion progress** — Real-time progress updates (pages processed, chunks indexed)
- [ ] **Multi-PDF sessions** — Query across multiple uploaded documents at once
- [ ] **Chat history persistence** — Save and reload past conversations per session
- [ ] **Re-ranking** — Add a cross-encoder re-ranker step after retrieval
- [ ] **Metadata filtering** — Filter search by page number, section, content type (text/table/image)
- [ ] **Delete session** — API + UI to delete a session and its OpenSearch index
- [ ] **Authentication** — API key or OAuth for multi-user deployments
