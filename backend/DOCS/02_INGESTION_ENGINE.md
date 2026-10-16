# Ingestion Engine

Ingestion is an offline step that turns raw documents into searchable vectors. It is not part of the deployed API, which keeps the production build small.

## Pipeline

1. **Discover** supported files (`.pdf`, `.html`, `.txt`, `.md`, `.docx`, `.pptx`) in a file or folder.
2. **Parse** with format-specific loaders:
   - PDF: `pypdf`, with `pdfplumber` as a per-page fallback for pages that return no text
   - HTML: BeautifulSoup, keeping headings, paragraphs, list items, tables and code blocks while dropping navigation and scripts
   - DOCX: paragraphs and tables via `python-docx`
   - PPTX: slide text and speaker notes via `python-pptx`
3. **Chunk** into roughly 1,200-character passages on paragraph boundaries with a 200-character overlap. Oversized paragraphs are split by sentence.
4. **Cache** chunks as JSON under `processed_data/<source_type>/` so re-indexing does not re-parse.
5. **Embed** with `gemini-embedding-001` using the `RETRIEVAL_DOCUMENT` task type, 768 dimensions, L2-normalised, in batches with exponential backoff on rate limits.
6. **Upsert** into Qdrant with deterministic point IDs (`uuid5(file:chunk)`), after deleting previous points for the same file. Re-running is idempotent.

## Usage

```bash
python -m app.ingestion.processor DATA/true_data --recreate
python -m app.ingestion.processor "DATA/noisy_data/<file>" --source-type noisy
python -m app.ingestion.processor DATA --no-cache --limit 20
```

| Flag | Effect |
| --- | --- |
| `--recreate` | Drop and recreate the collection |
| `--source-type` | Override the `true` / `noisy` label inferred from the folder name |
| `--no-cache` | Re-parse files even when cached chunks exist |
| `--limit` | Index only the first N files |

## Payload schema

| Field | Description |
| --- | --- |
| `text` | Chunk content |
| `source` | File name, indexed as a keyword |
| `source_type` | `true`, `noisy` or folder name, indexed as a keyword |
| `chunk` | Position of the chunk within the file |
