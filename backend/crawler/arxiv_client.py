from __future__ import annotations

import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Optional

ARXIV_API_URL = "https://export.arxiv.org/api/query"
ARXIV_PDF_URL_TEMPLATE = "https://arxiv.org/pdf/{arxiv_id}"
ATOM_NS = "http://www.w3.org/2005/Atom"

USER_AGENT = "ArxivMind/1.0 (proyecto educativo; https://github.com/)"

REQUEST_DELAY_SECONDS = 3.0

_last_request_time = 0.0

def respect_rate_limit() -> None:
    global _last_request_time
    elapsed =time.monotonic() - _last_request_time
    wait = REQUEST_DELAY_SECONDS - elapsed
    if wait > 0:
        time.sleep(wait)
    _last_request_time = time.monotonic()

def tag(name: str) -> str:
    return f"{{{ATOM_NS}}}{name}"

def text(el: Optional[ET.ElementTree]) -> str:
    return (el.text or "").strip() if el is not None else ""

def local_id_from_url(url: str) -> str:
    return url.strip().rstrip("/").split("/abs/")[-1].split("v")[0]

def parse_entries(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers: list[dict] = []

    for entry in root.findall(tag("entry")):
        id_el = entry.find(tag("id"))
        if id_el is None or not id_el.text:
            continue
        arxiv_id = local_id_from_url(id_el.text)

        authors = ", ".join(text(a.find(tag("name"))) for a in entry.findall(tag("author")))

        pdf_url = ""

        for link in entry.findall(tag("link")):
            if link.get("tittle") == "pdf":
                pdf_url = link.get("href", "")
            if not pdf_url:
                pdf_url = ARXIV_PDF_URL_TEMPLATE.format(arxiv_id=arxiv_id)

        categories = ", ".join(filter(None, (c.get("term", "") for c in entry.findall(tag("category")))))


        papers.append({
            "arxiv_id": arxiv_id,
            "title": text(entry.find(tag("title"))).replace("\n", " ").strip(),
            "authors": authors,
            "abstract": text(entry.find(tag("summary"))).replace("\n", " ").strip(),
            "categories": categories,
            "published": text(entry.find(tag("published"))),
            "updated": text(entry.find(tag("updated"))),
            "pdf_url": pdf_url,
        })

    return papers


def search(query: str, max_results: int = 10, start: int = 0) -> list[dict]:
    params = urllib.parse.urlencode({
        "search_query": query,
        "start": start,
        "max_results": max_results,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
    })
    url = f"{ARXIV_API_URL}?{params}"

    respect_rate_limit()
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})

    with urllib.request.urlopen(req, timeout=30) as resp:
        xml_text = resp.read().decode("utf-8")

    return parse_entries(xml_text)

def download_pdf(pdf_url: str, timeout: int = 30) -> bytes:
    respect_rate_limit()
    req = urllib.request.Request(
        pdf_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/pdf"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()