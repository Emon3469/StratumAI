import argparse
import json
import uuid
from pathlib import Path

from qdrant_client.http import models

from app.config import BACKEND_DIR, settings
from app.ingestion.chunking.splitter import chunk_text
from app.services.retrieval.embedding import embed_documents
from app.services.retrieval.qdrant_service import ensure_collection, sync_client

PROCESSED_DIR = BACKEND_DIR / "processed_data"
SUPPORTED = {".pdf", ".html", ".htm", ".txt", ".md", ".docx", ".pptx"}
UPSERT_BATCH = 128


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        from app.ingestion.loaders.pdf import parse_pdf

        return parse_pdf(str(path))
    if suffix in (".html", ".htm"):
        from app.ingestion.loaders.html import parse_html

        return parse_html(str(path))
    if suffix in (".txt", ".md"):
        from app.ingestion.loaders.text import parse_text

        return parse_text(str(path))
    from app.ingestion.loaders.office import parse_office

    return parse_office(str(path))


def source_type_for(path: Path, explicit: str | None) -> str:
    if explicit:
        return explicit
    folder = path.parent.name.lower()
    if "true" in folder:
        return "true"
    if "noisy" in folder:
        return "noisy"
    return folder or "general"


def load_chunks(path: Path, source_type: str, reuse_cache: bool) -> list[str]:
    cache_file = PROCESSED_DIR / source_type / f"{path.name}.json"
    if reuse_cache and cache_file.exists():
        return json.loads(cache_file.read_text(encoding="utf-8")).get("chunks", [])

    text = extract_text(path)
    chunks = chunk_text(text)
    if chunks:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(
            json.dumps({"filename": path.name, "source_type": source_type, "chunks": chunks}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return chunks


def index_file(path: Path, source_type: str, reuse_cache: bool) -> int:
    chunks = load_chunks(path, source_type, reuse_cache)
    if not chunks:
        print(f"  skipped {path.name}: no extractable text")
        return 0

    vectors = embed_documents(chunks)
    client = sync_client()
    client.delete(
        collection_name=settings.qdrant_collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(must=[models.FieldCondition(key="source", match=models.MatchValue(value=path.name))])
        ),
    )
    points = [
        models.PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, f"{path.name}:{index}")),
            vector=vector,
            payload={"text": chunk, "source": path.name, "source_type": source_type, "chunk": index},
        )
        for index, (chunk, vector) in enumerate(zip(chunks, vectors))
    ]
    for start in range(0, len(points), UPSERT_BATCH):
        client.upsert(collection_name=settings.qdrant_collection, points=points[start : start + UPSERT_BATCH])
    return len(points)


def discover(target: Path) -> list[Path]:
    if target.is_file():
        return [target]
    return sorted(p for p in target.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED)


def run(target: Path, explicit_type: str | None, recreate: bool, reuse_cache: bool, limit: int | None) -> None:
    ensure_collection(recreate=recreate)
    files = discover(target)[: limit or None]
    print(f"Indexing {len(files)} files into '{settings.qdrant_collection}' ({settings.embedding_dim}-dim)")
    total = 0
    for path in files:
        try:
            count = index_file(path, source_type_for(path, explicit_type), reuse_cache)
            total += count
            print(f"  {path.name}: {count} chunks")
        except Exception as error:
            print(f"  failed {path.name}: {error}")
    print(f"Done. {total} chunks indexed.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index documents into the StratumAI knowledge base.")
    parser.add_argument("path", nargs="?", default=str(BACKEND_DIR / "DATA" / "true_data"))
    parser.add_argument("--source-type", default=None)
    parser.add_argument("--recreate", action="store_true", help="drop and recreate the collection first")
    parser.add_argument("--no-cache", action="store_true", help="re-parse files even if processed chunks exist")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    run(Path(args.path), args.source_type, args.recreate, not args.no_cache, args.limit)


if __name__ == "__main__":
    main()
