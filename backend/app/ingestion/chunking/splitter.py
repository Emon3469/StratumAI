import re

_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def _split_long(paragraph: str, chunk_size: int) -> list[str]:
    pieces: list[str] = []
    current = ""
    for sentence in _SENTENCE_RE.split(paragraph):
        while len(sentence) > chunk_size:
            pieces.append(sentence[:chunk_size])
            sentence = sentence[chunk_size:]
        if len(current) + len(sentence) + 1 > chunk_size and current:
            pieces.append(current.strip())
            current = ""
        current += sentence + " "
    if current.strip():
        pieces.append(current.strip())
    return pieces


def chunk_text(text: str, chunk_size: int = 1200, overlap: int = 200) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text.replace("\r\n", "\n")).strip()
    if not text:
        return []

    paragraphs: list[str] = []
    for paragraph in text.split("\n\n"):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        paragraphs.extend(_split_long(paragraph, chunk_size) if len(paragraph) > chunk_size else [paragraph])

    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > chunk_size:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap else ""
            current = tail[tail.find(" ") + 1 :] if " " in tail else tail
            current = f"{current}\n\n" if current else ""
        current += paragraph + "\n\n"
    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) > 40]
