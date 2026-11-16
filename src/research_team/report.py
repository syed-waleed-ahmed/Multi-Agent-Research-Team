"""Post-processing and validation of the final research report.

The manager agent writes free-form Markdown. Before it is returned this module:

* enforces a maximum size so a runaway generation cannot bloat storage,
* extracts every link the model cited and checks it against the URLs that the
  web-search tool *actually* returned during the run. Links that were never
  retrieved are reported as "not found in search results" — they may be real,
  but the system cannot vouch for them, and it says so,
* builds a factual methodology section (queries, model, timings) from data the
  engine recorded, never from model output.

Nothing here claims a source was independently verified: retrieved sources are
labelled as search results, not as fact-checked references.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from .search import SearchResult, normalize_url, safe_url

# Link text may contain one level of balanced brackets, e.g. [[4]](https://...).
_MARKDOWN_LINK = re.compile(r"\[(?:[^\[\]]|\[[^\[\]]*\])*\]\((https?://[^)\s]+)\)")
_BARE_URL = re.compile(r"(?<![(\[<])\bhttps?://[^\s<>()\[\]\"'`【】]+")
# OpenAI-style citation markers emitted by gpt-oss models, e.g. 【4†https://x.y/z】.
_CITATION_MARKER = re.compile(r"【(\d+)†\s*(https?://[^\s】]+)\s*】")
# Markers without a URL (e.g. 【3†L10-L20】) carry no usable information.
_EMPTY_CITATION_MARKER = re.compile(r"【[^【】\n]{0,40}】")


def normalize_citation_markers(markdown: str) -> str:
    """Convert ``【n†URL】`` markers into Markdown links and drop URL-less markers."""
    converted = _CITATION_MARKER.sub(lambda m: f" [[{m.group(1)}]]({m.group(2)})", markdown)
    return _EMPTY_CITATION_MARKER.sub("", converted)


_TRAILING_PUNCTUATION = ".,;:!?*_"

TRUNCATION_NOTICE = "\n\n> _Report truncated: it exceeded the maximum allowed length._\n"


@dataclass(frozen=True)
class CitationCheck:
    """Which cited links appeared in the run's real search results."""

    matched: list[str] = field(default_factory=list)
    unmatched: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"matched": list(self.matched), "unmatched": list(self.unmatched)}


def extract_urls(markdown: str) -> list[str]:
    """Return the unique http(s) URLs cited in ``markdown`` in first-seen order.

    URLs inside fenced code blocks are ignored: they are example code, not
    citations.
    """
    without_code = re.sub(r"```.*?```", "", markdown, flags=re.DOTALL)
    found: list[str] = []
    seen: set[str] = set()
    candidates = _MARKDOWN_LINK.findall(without_code) + _BARE_URL.findall(without_code)
    for candidate in candidates:
        url = safe_url(candidate.rstrip(_TRAILING_PUNCTUATION))
        if url is None:
            continue
        key = normalize_url(url)
        if key not in seen:
            seen.add(key)
            found.append(url)
    return found


def is_public_url(url: str) -> bool:
    """False for local/private addresses (e.g. ``http://localhost:16686``).

    Such links appear in setup instructions ("open the dashboard at ...") and
    are never citations, so the citation check ignores them.
    """
    import ipaddress
    from urllib.parse import urlsplit

    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if not host or host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        return False
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return "." in host  # single-label names (e.g. "db") are internal
    return address.is_global


def check_citations(markdown: str, sources: Sequence[SearchResult]) -> CitationCheck:
    """Compare the report's public links with the URLs retrieved during the run."""
    retrieved = {normalize_url(source.url) for source in sources}
    matched: list[str] = []
    unmatched: list[str] = []
    for url in extract_urls(markdown):
        if not is_public_url(url):
            continue
        (matched if normalize_url(url) in retrieved else unmatched).append(url)
    return CitationCheck(matched=matched, unmatched=unmatched)


def enforce_max_length(markdown: str, max_chars: int) -> tuple[str, bool]:
    """Truncate ``markdown`` to ``max_chars`` (at a line boundary when possible)."""
    if len(markdown) <= max_chars:
        return markdown, False
    cut = markdown[:max_chars]
    newline = cut.rfind("\n")
    if newline > max_chars * 0.8:
        cut = cut[:newline]
    # Close an unterminated code fence so the truncated Markdown still renders.
    if cut.count("```") % 2 == 1:
        cut += "\n```"
    return cut + TRUNCATION_NOTICE, True


_FENCED_BLOCK = re.compile(r"```([\w+-]*)[^\n]*\n(.*?)```", re.DOTALL)


def check_python_blocks(markdown: str) -> tuple[int, int]:
    """Syntax-check fenced Python blocks with :func:`ast.parse` (never executed).

    Returns ``(passed, total)``. This is a static check only: it catches
    malformed code, not logic errors.
    """
    import ast

    passed = total = 0
    for language, body in _FENCED_BLOCK.findall(markdown):
        if language.lower() not in {"python", "py", "python3"}:
            continue
        total += 1
        try:
            ast.parse(body)
        except (SyntaxError, ValueError):
            continue
        passed += 1
    return passed, total


def build_methodology(
    *,
    model: str,
    provider: str,
    queries: Sequence[str],
    sources: Sequence[SearchResult],
    stage_durations: dict[str, float],
    citation_check: CitationCheck,
    search_provider: str,
    python_blocks: tuple[int, int] = (0, 0),
) -> str:
    """Factual description of how the report was produced (engine data only)."""
    lines = [
        "## Research Methodology",
        "",
        "This report was produced automatically by three AI agents running in sequence:",
        "a Research Agent (web search and note-taking), a Coding Agent (practical",
        "examples) and a Manager Agent (review and synthesis).",
        "",
        f"- **Model:** `{model}` via {provider}",
        f"- **Web search provider:** {search_provider}",
        f"- **Search queries executed:** {len(queries)}",
        f"- **Unique sources retrieved:** {len(sources)}",
    ]
    if stage_durations:
        timing = ", ".join(f"{stage} {seconds:.1f}s" for stage, seconds in stage_durations.items())
        lines.append(f"- **Stage timings:** {timing}")
    total_cited = len(citation_check.matched) + len(citation_check.unmatched)
    if total_cited:
        lines.append(
            f"- **Citation check:** {len(citation_check.matched)} of {total_cited} links in the "
            "report appear in the retrieved search results."
        )
    passed, total = python_blocks
    if total:
        lines.append(
            f"- **Code check:** {passed} of {total} Python code blocks passed a syntax check "
            "(static parsing only; the code was not executed)."
        )
    if queries:
        lines += ["", "**Queries:**", ""]
        lines += [f"{index}. {query}" for index, query in enumerate(queries, start=1)]
    lines += [
        "",
        "> **Limitations.** Content is AI-generated. Sources were retrieved by web search and",
        "> were not independently fact-checked. Links that do not appear in the retrieved results",
        "> may be inaccurate. Verify important facts and test code before relying on them.",
    ]
    return "\n".join(lines)


def build_sources_section(sources: Sequence[SearchResult]) -> str:
    """Markdown list of every source the search tool actually returned."""
    if not sources:
        return "## Sources Retrieved During Research\n\n_No web sources were retrieved._"
    lines = ["## Sources Retrieved During Research", ""]
    for index, source in enumerate(sources, start=1):
        title = source.title.replace("[", "(").replace("]", ")") or source.url
        suffix = f" — {source.published}" if source.published else ""
        lines.append(f"{index}. [{title}]({source.url}){suffix}")
    return "\n".join(lines)


def assemble_document(report: str, *, sources_section: str, methodology: str) -> str:
    """The full downloadable Markdown document."""
    return f"{report.rstrip()}\n\n---\n\n{sources_section}\n\n{methodology}\n"
