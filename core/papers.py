from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx


OPENALEX_URL = "https://api.openalex.org/works"
PAPERS_DIR = Path(r"D:\Sage\data\papers")


def search_papers(
    query: str,
    max_results: int = 10,
    year_from: int | None = None,
    year_to: int | None = None,
) -> list[dict[str, Any]]:
    if not query.strip():
        raise ValueError("Paper query cannot be empty.")

    params: dict[str, Any] = {
        "search": query,
        "per-page": max(1, min(max_results, 50)),
        "sort": "relevance_score:desc",
    }

    filters: list[str] = []
    if year_from is not None:
        filters.append(f"from_publication_date:{year_from}-01-01")
    if year_to is not None:
        filters.append(f"to_publication_date:{year_to}-12-31")

    if filters:
        params["filter"] = ",".join(filters)

    response = httpx.get(
        OPENALEX_URL,
        params=params,
        headers={"User-Agent": "Sage Research Engine/0.1"},
        timeout=30.0,
    )
    response.raise_for_status()

    data = response.json()
    results: list[dict[str, Any]] = []

    for work in data.get("results", []):
        primary_location = work.get("primary_location") or {}
        best_oa = work.get("best_oa_location") or {}
        source = primary_location.get("source") or {}
        authorships = work.get("authorships") or []

        results.append(
            {
                "id": work.get("id", ""),
                "title": work.get("title", ""),
                "year": work.get("publication_year"),
                "doi": work.get("doi", ""),
                "type": work.get("type", ""),
                "cited_by_count": work.get("cited_by_count", 0),
                "journal": source.get("display_name", ""),
                "authors": [
                    a.get("author", {}).get("display_name", "")
                    for a in authorships
                    if a.get("author")
                ],
                "abstract": _reconstruct_abstract(
                    work.get("abstract_inverted_index")
                ),
                "landing_page": primary_location.get("landing_page_url", ""),
                "pdf_url": (
                    best_oa.get("pdf_url")
                    or primary_location.get("pdf_url")
                    or ""
                ),
                "is_open_access": bool(
                    (work.get("open_access") or {}).get("is_oa")
                ),
            }
        )

    return results


def _reconstruct_abstract(
    inverted: dict[str, list[int]] | None,
) -> str:
    if not inverted:
        return ""

    positions: dict[int, str] = {}
    for word, indexes in inverted.items():
        for index in indexes:
            positions[index] = word

    return " ".join(
        positions[index] for index in sorted(positions)
    )


def pypaperbot_bibtex(
    query: str,
    scholar_pages: int = 1,
    scholar_results: int = 10,
) -> dict[str, Any]:
    """
    Use PyPaperBot for Scholar/BibTeX collection only.
    This deliberately does not enable Sci-Hub/other bypass mirrors.
    """
    if not query.strip():
        raise ValueError("Paper query cannot be empty.")

    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    command = [
        sys.executable,
        "-m",
        "PyPaperBot",
        f"--query={query}",
        f"--scholar-pages={max(1, scholar_pages)}",
        f"--scholar-results={max(1, scholar_results)}",
        f'--dwn-dir={PAPERS_DIR}',
        "--restrict=0",
    ]

    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=180,
    )

    return {
        "returncode": completed.returncode,
        "stdout": completed.stdout[-12000:],
        "stderr": completed.stderr[-12000:],
        "directory": str(PAPERS_DIR),
    }
