"""TF-IDF cosine-similarity scientific literature RAG over verified open-access papers."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from backend.core.data import DATA_DIR

PAPERS_DIR = DATA_DIR / "papers"


class PaperChunk(BaseModel):
    doc_id: str
    filename: str
    title: str
    citation: str
    pmcid: str | None = None
    doi: str | None = None
    url: str | None = None
    section: str
    text: str


class RagHit(BaseModel):
    filename: str
    title: str
    citation: str
    pmcid: str | None = None
    doi: str | None = None
    url: str | None = None
    section: str
    excerpt: str
    score: float


def _parse_paper(path: Path) -> list[PaperChunk]:
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()
    title = path.stem
    citation = ""
    pmcid = None
    doi = None
    url = None

    for line in lines[:12]:
        if line.startswith("# "):
            title = line[2:].strip()
        elif "**Citation:**" in line:
            citation = line.split("**Citation:**", 1)[1].strip()
        elif "**PMCID:**" in line:
            pmcid = line.split("**PMCID:**", 1)[1].strip()
        elif "**DOI:**" in line:
            doi = line.split("**DOI:**", 1)[1].strip().strip("`")
        elif "**URL:**" in line:
            url = line.split("**URL:**", 1)[1].strip()

    # Split into section-level chunks around ## headings
    chunks: list[PaperChunk] = []
    cur_section = "Overview"
    cur_buf: list[str] = []

    for line in lines:
        if line.startswith("## "):
            body = "\n".join(cur_buf).strip()
            if len(body) > 40 and cur_section != "Overview":
                chunks.append(
                    PaperChunk(
                        doc_id=f"{path.stem}::{cur_section}",
                        filename=path.name,
                        title=title,
                        citation=citation,
                        pmcid=pmcid,
                        doi=doi,
                        url=url,
                        section=cur_section,
                        text=body,
                    )
                )
            cur_section = line[3:].strip()
            cur_buf = []
        else:
            if not line.startswith("# ") and not line.startswith("- **"):
                cur_buf.append(line)

    tail = "\n".join(cur_buf).strip()
    if len(tail) > 40:
        chunks.append(
            PaperChunk(
                doc_id=f"{path.stem}::{cur_section}",
                filename=path.name,
                title=title,
                citation=citation,
                pmcid=pmcid,
                doi=doi,
                url=url,
                section=cur_section,
                text=tail,
            )
        )
    return chunks


class LiteratureIndex:
    def __init__(self, chunks: list[PaperChunk]):
        self.chunks = chunks
        corpus = [f"{c.title} {c.section} {c.text}" for c in chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=4000)
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, top_k: int = 4) -> list[RagHit]:
        clean_q = re.sub(r"[^\w\s+-]", " ", query).strip() or "plant protein meat analogue texture"
        q_vec = self.vectorizer.transform([clean_q])
        sims = cosine_similarity(q_vec, self.matrix).flatten()
        ranked_indices = sims.argsort()[::-1]

        hits: list[RagHit] = []
        seen_files: set[str] = set()
        for idx in ranked_indices:
            chunk = self.chunks[int(idx)]
            score = float(sims[int(idx)])
            # Prefer diversity across distinct papers on first pass
            if chunk.filename in seen_files and len(hits) + 1 < top_k:
                continue
            seen_files.add(chunk.filename)
            hits.append(
                RagHit(
                    filename=chunk.filename,
                    title=chunk.title,
                    citation=chunk.citation,
                    pmcid=chunk.pmcid,
                    doi=chunk.doi,
                    url=chunk.url,
                    section=chunk.section,
                    excerpt=chunk.text[:480] + ("..." if len(chunk.text) > 480 else ""),
                    score=round(score, 3),
                )
            )
            if len(hits) >= top_k:
                break
        return hits


@lru_cache(maxsize=1)
def get_literature_index() -> LiteratureIndex:
    chunks: list[PaperChunk] = []
    for path in sorted(PAPERS_DIR.glob("*.md")):
        chunks.extend(_parse_paper(path))
    if not chunks:
        raise RuntimeError(f"No scientific paper files found in {PAPERS_DIR}")
    return LiteratureIndex(chunks)


def search_literature(query: str, top_k: int = 4) -> list[RagHit]:
    return get_literature_index().search(query, top_k=top_k)


def list_all_papers() -> list[dict[str, str | None]]:
    seen: dict[str, dict[str, str | None]] = {}
    for c in get_literature_index().chunks:
        if c.filename not in seen:
            seen[c.filename] = {
                "filename": c.filename,
                "title": c.title,
                "citation": c.citation,
                "pmcid": c.pmcid,
                "doi": c.doi,
                "url": c.url,
            }
    return list(seen.values())
