from __future__ import annotations
import re

_SENTENCE_RE = re.compile(
    r'(?<=[.!?])\s+(?=[A-Z"\'\(0-9])'
    r'|(?<=;)\s+'
)

def clean_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def split_sentences(text: str, min_sent_chars: int = 20) -> list[str]:
    raw = [s.strip() for s in _SENTENCE_RE.split(text) if s.strip()]
    merged: list[str] = []
    buf = ""
    for sent in raw:
        buf = (buf + " " + sent).strip() if buf else sent
        if len(buf) >= min_sent_chars:
            merged.append(buf)
            buf = ""


    if buf: 
        if merged:
            merged[-1] = (merged[-1] + " " + buf).strip()
        else:
            merged.append(buf)

    return merged

def make_chunks(text: str, chunk_size: int = 1000,
    overlap_sentences: int = 2, min_chunk_chars: int = 100, min_sent_chars: int = 20,) -> list[str]:

    cleaned = clean_text(text)
    paragraphs = [p.strip() for p in cleaned.split("\n\n") if p.strip()]
    chunks: list[str] = []

    for para in paragraphs:
        sentences = split_sentences(para, min_sent_chars=min_sent_chars)

        if not sentences:
            continue

        window: list[str] = []
        window_len = 0

        for sent in sentences:
            sent_len = len(sent) + 1

            if window and window_len + sent_len > chunk_size:
                candidate = " ".join(window)
                if len(candidate) >= min_chunk_chars:
                    chunks.append(candidate)
                if overlap_sentences > 0 and len(window) > overlap_sentences:
                    window = window[-overlap_sentences:]
                    window_len = sum(len(s) + 1 for s in window)
                else:
                    window = []
                    window_len = 0
            window.append(sent)
            window_len += sent_len

        if window:
            candidate = " ".join(window)
            if len(candidate) >= min_chunk_chars:
                chunks.append(candidate)

    return chunks