import os
from whoosh import index
from whoosh.fields import Schema, TEXT, ID, STORED, DATETIME
from whoosh.qparser import MultifieldParser, QueryParser
from whoosh.query import FuzzyTerm
from whoosh import scoring
from datetime import datetime

INDEX_DIR = os.environ.get("INDEX_DIR", "./data/index")

# Schema — every crawled page becomes one document
SCHEMA = Schema(
    url=ID(stored=True, unique=True),
    title=TEXT(stored=True, field_boost=2.0),   # title matches score 2x higher
    body=TEXT(stored=True),
    domain=STORED(),
    crawled_at=DATETIME(stored=True),
    description=STORED(),
)

def get_or_create_index():
    os.makedirs(INDEX_DIR, exist_ok=True)
    if index.exists_in(INDEX_DIR):
        return index.open_dir(INDEX_DIR)
    return index.create_in(INDEX_DIR, SCHEMA)

def add_document(url: str, title: str, body: str, domain: str, description: str = ""):
    idx = get_or_create_index()
    writer = idx.writer()
    writer.update_document(
        url=url,
        title=title,
        body=body,
        domain=domain,
        crawled_at=datetime.utcnow(),
        description=description,
    )
    writer.commit()

def bulk_add(documents: list[dict]):
    """Add many documents at once — much faster than one-by-one."""
    idx = get_or_create_index()
    writer = idx.writer()
    for doc in documents:
        writer.update_document(
            url=doc["url"],
            title=doc.get("title", ""),
            body=doc.get("body", ""),
            domain=doc.get("domain", ""),
            crawled_at=datetime.utcnow(),
            description=doc.get("description", ""),
        )
    writer.commit()

def search(query_str: str, page: int = 1, per_page: int = 10) -> dict:
    idx = get_or_create_index()
    results = []
    total = 0

    with idx.searcher(weighting=scoring.BM25F()) as searcher:
        parser = MultifieldParser(["title", "body"], schema=SCHEMA)
        try:
            query = parser.parse(query_str)
        except Exception:
            # Fallback: treat as plain text
            query = QueryParser("body", schema=SCHEMA).parse(query_str)

        hits = searcher.search_page(query, page, pagelen=per_page)
        total = hits.total

        for hit in hits:
            # Generate a snippet with highlights
            snippet = hit.highlights("body", top=3) or hit["description"] or ""
            results.append({
                "url": hit["url"],
                "title": hit["title"] or hit["url"],
                "snippet": snippet,
                "domain": hit["domain"],
                "score": hit.score,
            })

    return {
        "query": query_str,
        "total": total,
        "page": page,
        "per_page": per_page,
        "results": results,
    }

def index_stats() -> dict:
    idx = get_or_create_index()
    with idx.searcher() as s:
        return {
            "doc_count": s.doc_count(),
            "index_dir": INDEX_DIR,
        }