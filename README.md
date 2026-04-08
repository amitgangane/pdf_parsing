# RAG Research Paper Assistant

A Retrieval-Augmented Generation (RAG) system that lets you upload PDF documents and ask questions about them. It combines OpenSearch for vector search, Ollama for local embeddings, and OpenAI or Ollama for answer generation — all wrapped in a FastAPI backend with a Gradio chat UI.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Project](#running-the-project)
- [Using the Application](#using-the-application)
- [API Endpoints](#api-endpoints)
- [How It Works](#how-it-works)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Gradio UI  │────▶│  FastAPI    │────▶│   PostgreSQL     │
│ :7860       │     │  :8000      │     │   :5433          │
└─────────────┘     └──────┬──────┘     └──────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
       ┌──────▼──────┐          ┌───────▼──────┐
       │  OpenSearch │          │    Ollama    │
       │  :9200      │          │    :11434    │
       │ (vectors)   │          │ (embeddings) │
       └─────────────┘          └──────────────┘
```

**Data flow:**
1. User uploads a PDF → FastAPI saves it and starts background ingestion
2. Ingestion extracts text/images/tables → Ollama embeds them → stored in OpenSearch
3. User asks a question → OpenSearch retrieves relevant chunks → OpenAI or Ollama generates an answer

---

## Project Structure

```
RAG-rp/
├── api/                          # FastAPI backend
│   ├── main.py                   # App entry point, router registration, table creation
│   ├── config.py                 # Settings loaded from .env
│   ├── db.py                     # SQLAlchemy engine and session setup
│   ├── crud.py                   # Database CRUD helpers
│   ├── dependencies.py           # FastAPI dependency injection (get_db)
│   ├── models/
│   │   ├── orm.py                # SessionRecord SQLAlchemy model
│   │   ├── requests.py           # Pydantic request schemas
│   │   └── responses.py          # Pydantic response schemas
│   └── routers/
│       ├── upload.py             # POST /upload/ — PDF upload + background ingestion
│       ├── sessions.py           # GET /sessions/, GET /sessions/{id}
│       └── query.py              # POST /query/, POST /query/stream
│
├── Ingestion/                    # Core RAG pipeline
│   ├── helper.py                 # Ollama embeddings + OpenSearch client
│   ├── chunking.py               # PDF parsing: text, images, tables via unstructured
│   ├── ingestion.py              # Index creation + bulk insert into OpenSearch
│   ├── retrieval.py              # Keyword, semantic, hybrid search
│   └── generation.py             # RAG prompt + OpenAI/Ollama response generation
│
├── gradio_app.py                 # Gradio chat UI
├── docker-compose.yml            # OpenSearch, PostgreSQL containers
├── requirements.txt              # Python dependencies
├── .env                          # API keys (not committed)
└── paper/                        # Sample PDF files
```

---

## Prerequisites

- **Python 3.10+**
- **Docker Desktop** (for OpenSearch and PostgreSQL)
- **Ollama Docker container** running on port `11434`
- **OpenAI API key** (for image/table captioning during ingestion, and optionally for generation)

---

## Installation

### 1. Clone the repository

```bash
git clone <repo-url>
cd RAG-rp
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up Ollama

Run Ollama as a Docker container:

```bash
docker run -d -p 11434:11434 --name ollama ollama/ollama:latest
```

Pull the required models:

```bash
# Required: embedding model (used for all ingestion and search)
docker exec -it ollama ollama pull embeddinggemma

# Required if using Ollama for generation
docker exec -it ollama ollama pull llama2
```

### 5. Start infrastructure services

```bash
docker-compose up -d
```

This starts:
- **OpenSearch** on port `9200`
- **OpenSearch Dashboards** on port `5601`
- **PostgreSQL** on port `5433`

Verify all containers are running:

```bash
docker ps
```

You should see `opensearch`, `rag_postgres`, and `ollama` all with status `Up`.

---

## Configuration

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=sk-your-openai-api-key-here
```

Other settings (in `api/config.py`) with their defaults:

| Setting | Default | Description |
|---|---|---|
| `OPENSEARCH_HOST` | `localhost` | OpenSearch host |
| `OPENSEARCH_PORT` | `9200` | OpenSearch port |
| `DATABASE_URL` | `postgresql://rag:rag@localhost:5433/rag` | PostgreSQL connection string |
| `UPLOAD_DIR` | `uploads` | Temporary PDF storage directory |

---

## Running the Project

You need **two terminals** open simultaneously.

### Terminal 1 — Start the FastAPI backend

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Wait until you see:
```
INFO: Application startup complete.
```

### Terminal 2 — Start the Gradio UI

```bash
python gradio_app.py
```

Then open **http://localhost:7860** in your browser.

---

## Using the Application

### Step 1: Upload a PDF

1. Go to the **Upload** tab
2. Click to select a PDF file
3. Click **Upload**
4. Copy the `session_id` shown in the output
5. Click **Check Status** — wait until it shows `ready` (ingestion runs in background, may take 1-3 minutes depending on PDF size)

### Step 2: Ask Questions

1. Go to the **Chat** tab
2. Click **Refresh Sessions** to populate the dropdown
3. Select your session from the dropdown
4. Choose a **retrieval type**:
   - `hybrid` — combines keyword + semantic search (recommended)
   - `semantic` — vector similarity only
   - `keyword` — BM25 text matching only
5. Choose a **model**:
   - `openai` — faster, uses `gpt-4o-mini` (requires API key)
   - `ollama` — local, uses `llama2` (slower on CPU)
6. Type your question and click **Send**

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload/` | Upload a PDF. Returns `202` immediately; ingestion runs in background |
| `GET` | `/sessions/` | List all sessions with their status |
| `GET` | `/sessions/{session_id}` | Get status of a specific session (`processing` / `ready` / `failed`) |
| `POST` | `/query/` | Blocking RAG query — waits for full response |
| `POST` | `/query/stream` | Streaming RAG query — returns chunks as they are generated |
| `GET` | `/health` | Health check |

Interactive API docs available at **http://localhost:8000/docs**

### Example: Query request body

```json
{
  "session_id": "bdfd0b0f-23d0-4bb6-a5ef-ef3308bc3d14",
  "question": "What is the core difference between RAG and fine-tuning?",
  "search_type": "hybrid",
  "top_k": 5,
  "model_type": "openai"
}
```

---

## How It Works

### Ingestion Pipeline

When a PDF is uploaded:

1. **Parsing** — `unstructured` library extracts content with `hi_res` strategy, separating text, images, and tables
2. **Captioning** — OpenAI `gpt-4o-mini` generates descriptions for images and tables
3. **Chunking** — text is split into semantic chunks by title and character limits
4. **Embedding** — each chunk is embedded using Ollama `embeddinggemma` (768-dimensional vectors)
5. **Indexing** — chunks + vectors are bulk-inserted into a dedicated OpenSearch index named `pdf_{session_id}`

### Retrieval

Three search strategies are supported:

- **Keyword** — BM25 `match` query on the `content` field
- **Semantic** — KNN search using cosine similarity against the `embedding` field
- **Hybrid** — combines both in a `bool` query with `should` clauses; falls back to keyword on error

### Generation

Retrieved chunks are formatted as:
```
[Document 1 - text]
<chunk content>

[Document 2 - image]
<image description>
...
```

This context is injected into a RAG prompt template and sent to either OpenAI or Ollama to generate a grounded answer.

---

## Troubleshooting

### "Connection refused" on port 11434 (Ollama)
Ollama container is not running. Start it:
```bash
docker start ollama
```

### "Connection refused" on port 8000 (FastAPI)
The FastAPI server is not running. Start it:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### "No relevant information found"
- The session may still be ingesting — check status via `GET /sessions/{session_id}` and wait for `ready`
- Make sure you selected the correct session in the Gradio dropdown

### Ingestion is slow
Large PDFs with many images/tables take longer because each image is sent to OpenAI for captioning. Text-only PDFs are faster.

### Generation is slow with Ollama
Ollama runs on CPU by default. Switch to `openai` in the model dropdown for faster responses, or enable GPU passthrough if you have an NVIDIA GPU.

### OpenSearch index errors (404)
The session's index was not created yet. Wait for ingestion to complete (status = `ready`).
