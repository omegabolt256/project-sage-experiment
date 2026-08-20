$ErrorActionPreference = "Stop"

$root = "D:\Sage"
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$backup = Join-Path $root "backups\papers-$stamp"
New-Item -ItemType Directory -Force $backup | Out-Null

foreach ($file in @(
    "core\capability_registry.py",
    "core\sage.py"
)) {
    $src = Join-Path $root $file
    if (Test-Path $src) {
        Copy-Item $src (Join-Path $backup ($file -replace "\\","_"))
    }
}

Write-Host "Installing academic research dependencies..." -ForegroundColor Cyan
py -m pip install PyPaperBot

# OpenAlex wrapper + PyPaperBot integration.
@'
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
'@ | Set-Content -Encoding UTF8 "$root\core\papers.py"

# Update research capability registration.
@'
from __future__ import annotations

from core.capabilities import Capability, CapabilityRouter


def create_capability_router() -> CapabilityRouter:
    router = CapabilityRouter()

    router.register(
        Capability(
            name="research",
            description=(
                "Find, retrieve, inspect, compare, and synthesize "
                "information from the web and scholarly sources."
            ),
            tools=(
                "web_search",
                "web_fetch",
                "paper_search",
                "paper_bibtex",
            ),
        )
    )

    router.register(
        Capability(
            name="memory",
            description=(
                "Read and update persistent information about the user."
            ),
            tools=("remember",),
        )
    )

    router.register(
        Capability(
            name="calculation",
            description="Perform deterministic arithmetic.",
            tools=("calculator",),
        )
    )

    router.register(
        Capability(
            name="browser",
            description=(
                "Interact with websites requiring JavaScript, sessions, "
                "or browser automation."
            ),
            tools=(),
        )
    )

    router.register(
        Capability(
            name="conversation",
            description=(
                "Answer questions, reason about information, "
                "and maintain conversational context."
            ),
            tools=(),
        )
    )

    return router
'@ | Set-Content -Encoding UTF8 "$root\core\capability_registry.py"

# Patch deterministic research planning + imports/registrations in SageCore.
$agentPath = Join-Path $root "tools\agent.py"
if (Test-Path $agentPath) {
    $agent = Get-Content $agentPath -Raw

    $agent = $agent -replace (
        'r"\bcurrent news\b",',
        'r"\bcurrent news\b",' + "`r`n" +
        '            r"\bfind papers\b",' + "`r`n" +
        '            r"\bfind research\b",' + "`r`n" +
        '            r"\bfind papers on\b",' + "`r`n" +
        '            r"\bsearch papers\b",' + "`r`n" +
        '            r"\bscholarly\b",' +
        ''
    )

    $agent = $agent -replace (
        'return \{\r?\n                "use_tool": True,\r?\n                "capability": "research",\r?\n                "tool": "web_search",',
        'if re.search(r"(?i)\b(find papers|find research|search papers|scholarly|academic papers)\b", text):' + "`r`n" +
        '                return {' + "`r`n" +
        '                    "use_tool": True,' + "`r`n" +
        '                    "capability": "research",' + "`r`n" +
        '                    "tool": "paper_search",' + "`r`n" +
        '                    "arguments": {' + "`r`n" +
        '                        "query": re.sub(r"(?i)^(please\s+)?(find papers on|find research on|search papers for|search papers on)\s*", "", text).strip() or text,' + "`r`n" +
        '                        "max_results": 10,' + "`r`n" +
        '                    },' + "`r`n" +
        '                }' + "`r`n`r`n" +
        '            return {' + "`r`n" +
        '                "use_tool": True,' + "`r`n" +
        '                "capability": "research",' + "`r`n" +
        '                "tool": "web_search",'
    )

    Set-Content -Encoding UTF8 $agentPath $agent
}

# Patch core/sage.py to import paper functions and register tools.
$sagePath = Join-Path $root "core\sage.py"
$sage = Get-Content $sagePath -Raw

if ($sage -notmatch 'from core.papers import') {
    $sage = $sage -replace (
        'from core.research import ResearchEngine',
        'from core.papers import pypaperbot_bibtex, search_papers' + "`r`n" +
        'from core.research import ResearchEngine'
    )
}

$registration = @'
    tools.register(
        Tool(
            name="paper_search",
            description="Search scholarly literature using OpenAlex.",
            handler=search_papers,
            parameters=[
                ToolParameter(
                    name="query",
                    description="Scholarly search query.",
                    type="string",
                ),
                ToolParameter(
                    name="max_results",
                    description="Maximum number of papers.",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="year_from",
                    description="Earliest publication year.",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="year_to",
                    description="Latest publication year.",
                    type="integer",
                    required=False,
                ),
            ],
        )
    )

    tools.register(
        Tool(
            name="paper_bibtex",
            description=(
                "Use PyPaperBot to collect Google Scholar/BibTeX metadata "
                "for a scholarly query. Does not enable bypass mirrors."
            ),
            handler=pypaperbot_bibtex,
            parameters=[
                ToolParameter(
                    name="query",
                    description="Scholarly search query.",
                    type="string",
                ),
                ToolParameter(
                    name="scholar_pages",
                    description="Scholar pages to inspect.",
                    type="integer",
                    required=False,
                ),
                ToolParameter(
                    name="scholar_results",
                    description="Results to request from the Scholar page.",
                    type="integer",
                    required=False,
                ),
            ],
        )
    )

'@

if ($sage -notmatch 'name="paper_search"') {
    $marker = '    agent = AgentExecutor('
    $sage = $sage.Replace($marker, $registration + $marker)
}

Set-Content -Encoding UTF8 $sagePath $sage

# Syntax check.
Push-Location $root
py -m py_compile core\papers.py core\capability_registry.py tools\agent.py core\sage.py
if ($LASTEXITCODE -ne 0) {
    throw "Python syntax check failed."
}
Pop-Location

Write-Host ""
Write-Host "Academic research capability installed." -ForegroundColor Green
Write-Host "OpenAlex search + PyPaperBot BibTeX collection are now available." -ForegroundColor Green
Write-Host "Backups: $backup"
Write-Host ""
Write-Host "NOTE: PyPaperBot is configured here for Scholar/BibTeX collection only;"
Write-Host "Sage does not enable Sci-Hub or other bypass mirrors." -ForegroundColor Yellow
