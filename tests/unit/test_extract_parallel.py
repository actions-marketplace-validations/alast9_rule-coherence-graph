"""Parallel extraction must preserve input order and results (determinism, §8)."""

from __future__ import annotations

from pathlib import Path

from rcg.extractors.cache import ExtractionCache
from rcg.extractors.extract import extract_all
from rcg.extractors.mock_provider import MockProvider
from rcg.schema import RawRule, Source


def _raws(n: int) -> list[RawRule]:
    return [
        RawRule(
            text=f"Rule {i}: you must always do thing {i}.",
            source=Source(file=f"pack/{i}.md", format="markdown", pack="pack"),
        )
        for i in range(n)
    ]


def test_parallel_matches_sequential(tmp_path: Path) -> None:
    raws = _raws(25)
    seq = extract_all(raws, MockProvider(), cache=ExtractionCache(tmp_path / "s"), concurrency=1)
    par = extract_all(raws, MockProvider(), cache=ExtractionCache(tmp_path / "p"), concurrency=8)

    assert [r.id for r in seq] == [r.id for r in par]
    assert [r.raw_text for r in seq] == [r.raw_text for r in par]
    assert [r.directive.modality for r in seq] == [r.directive.modality for r in par]


def test_parallel_pulls_from_cache(tmp_path: Path) -> None:
    raws = _raws(10)
    cache = ExtractionCache(tmp_path / "c")
    first = extract_all(raws, MockProvider(), cache=cache, concurrency=4)
    # Second run is fully cached; order and ids must be identical.
    second = extract_all(raws, MockProvider(), cache=cache, concurrency=4)
    assert [r.id for r in first] == [r.id for r in second]
