"""Tests for report post-processing: citations, size limits, methodology."""

from __future__ import annotations

from research_team.report import (
    TRUNCATION_NOTICE,
    CitationCheck,
    assemble_document,
    build_methodology,
    build_sources_section,
    check_citations,
    check_python_blocks,
    enforce_max_length,
    extract_urls,
    normalize_citation_markers,
)
from research_team.search import SearchResult

SOURCES = [
    SearchResult("Docs", "https://docs.example.org/guide", "s", published="2026-01-01"),
    SearchResult("Blog", "https://blog.example.com/post", "s"),
]


def test_normalize_citation_markers():
    text = "Fact【4†https://docs.example.org/guide】 and noise【3†L10-L20】."
    assert (
        normalize_citation_markers(text) == "Fact [[4]](https://docs.example.org/guide) and noise."
    )


def test_extract_urls_handles_links_bare_urls_and_ignores_code():
    markdown = (
        "See [docs](https://docs.example.org/guide), [[2]](https://blog.example.com/post) "
        "and https://other.example/page.\n```python\nrequests.get('https://in-code.example')\n```"
    )
    assert extract_urls(markdown) == [
        "https://docs.example.org/guide",
        "https://blog.example.com/post",
        "https://other.example/page",
    ]


def test_check_citations_flags_links_not_in_search_results():
    report = "[a](https://docs.example.org/guide/) [b](https://invented.example/x)"
    check = check_citations(report, SOURCES)
    assert check.matched == ["https://docs.example.org/guide/"]
    assert check.unmatched == ["https://invented.example/x"]


def test_enforce_max_length_truncates_and_closes_code_fence():
    text = "intro\n```python\n" + "x = 1\n" * 100
    truncated, was_truncated = enforce_max_length(text, 120)
    assert was_truncated
    assert truncated.endswith(TRUNCATION_NOTICE)
    assert truncated.count("```") % 2 == 0


def test_enforce_max_length_noop_when_small():
    assert enforce_max_length("short", 100) == ("short", False)


def test_check_python_blocks_parses_without_executing():
    markdown = (
        "```python\nimport os\nprint(os.getcwd())\n```\n"
        "```py\ndef broken(:\n```\n"
        "```bash\nrm -rf /\n```"
    )
    assert check_python_blocks(markdown) == (1, 2)


def test_methodology_is_factual_and_honest():
    text = build_methodology(
        model="m",
        provider="Groq",
        queries=["q1", "q2"],
        sources=SOURCES,
        stage_durations={"research": 1.0},
        citation_check=CitationCheck(matched=["a"], unmatched=["b"]),
        search_provider="serper",
        python_blocks=(1, 2),
    )
    assert "Search queries executed:** 2" in text
    assert "1 of 2 links" in text
    assert "1 of 2 Python code blocks" in text
    assert "not independently fact-checked" in text
    assert "verified" not in text.replace("not independently fact-checked", "").lower().replace(
        "verify important", ""
    )


def test_sources_section_and_document():
    section = build_sources_section(SOURCES)
    assert "[Docs](https://docs.example.org/guide) — 2026-01-01" in section
    assert "No web sources" in build_sources_section([])
    document = assemble_document("# R", sources_section=section, methodology="## M")
    assert document.index("# R") < document.index("## Sources") < document.index("## M")
