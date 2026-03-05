from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.db import engine, Base
import api.models.orm  # registers SessionRecord with Base
from api.routers import upload, sessions, query

app = FastAPI(
    title="RAG API",
    description="Multi-PDF RAG pipeline over HTTP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(sessions.router)
app.include_router(query.router)


@app.on_event("startup")
def create_tables():
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}
