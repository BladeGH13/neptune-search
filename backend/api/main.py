from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os

from backend.search.index import search, index_stats, bulk_add
from backend.ai.assistant import ai

app = FastAPI(
    title="Neptune Search API",
    description="Search API powering Neptune Browser — by BLUOM Tech",
    version="1.0.0",
)

# Allow Neptune browser and GitHub Pages frontend
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ── Models ────────────────────────────────────────────────────────────────────

class IndexRequest(BaseModel):
    url: str
    title: str
    body: str
    domain: str
    description: Optional[str] = ""

class BulkIndexRequest(BaseModel):
    documents: list[IndexRequest]
    secret: str   # shared secret from env to protect this endpoint

# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"name": "Neptune Search API", "by": "BLUOM Tech", "status": "online"}

@app.get("/search")
def search_endpoint(
    q: str = Query(..., min_length=1, description="Search query"),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
):
    if not q.strip():
        raise HTTPException(400, "Query cannot be empty")

    # Run full-text search
    results = search(q, page=page, per_page=per_page)

    # Ask AI for an instant answer or summary
    instant_answer = ai.answer(q)
    ai_summary = ai.summarise_results(q, results["results"])

    return {
        **results,
        "instant_answer": instant_answer,
        "ai_summary": ai_summary,
    }

@app.get("/suggest")
def suggest(q: str = Query(..., min_length=1)):
    """
    Simple prefix-based autocomplete.
    For a full implementation, keep a sorted term list from Whoosh.
    """
    # Placeholder — returns query echoed back with common suffixes
    suggestions = [
        q,
        q + " tutorial",
        q + " examples",
        q + " vs",
        q + " how to",
    ]
    return {"suggestions": suggestions[:5]}

@app.post("/index")
def index_single(req: IndexRequest):
    secret = os.environ.get("CRAWLER_SECRET", "dev-secret")
    # For single doc, just add directly (crawler uses bulk endpoint)
    from backend.search.index import add_document
    add_document(req.url, req.title, req.body, req.domain, req.description)
    return {"status": "indexed", "url": req.url}

@app.post("/bulk-index")
def bulk_index(req: BulkIndexRequest):
    expected_secret = os.environ.get("CRAWLER_SECRET", "dev-secret")
    if req.secret != expected_secret:
        raise HTTPException(403, "Invalid crawler secret")
    docs = [d.model_dump() for d in req.documents]
    bulk_add(docs)
    return {"status": "indexed", "count": len(docs)}

@app.get("/stats")
def stats():
    return index_stats()

@app.get("/health")
def health():
    return {"status": "ok"}