"""Orchestrator: run RawRule -> Rule extraction with caching.

Extraction is I/O-bound (one LLM call per uncached rule), so uncached rules are
extracted concurrently with a thread pool. Cache hits are resolved first and the
output preserves input order, so results stay deterministic (§8) regardless of
concurrency. Set ``RCG_EXTRACT_CONCURRENCY`` (default 8) or pass ``concurrency``;
1 forces the old sequential path.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from rcg.extractors.cache import ExtractionCache
from rcg.providers.llm import LLMProvider
from rcg.schema import RawRule, Rule

_DEFAULT_CONCURRENCY = 8


def _resolve_concurrency(concurrency: int | None) -> int:
    if concurrency is not None:
        return max(1, concurrency)
    env = os.environ.get("RCG_EXTRACT_CONCURRENCY")
    if env:
        try:
            return max(1, int(env))
        except ValueError:
            pass
    return _DEFAULT_CONCURRENCY


def extract_all(
    raws: Iterable[RawRule],
    provider: LLMProvider,
    cache: ExtractionCache | None = None,
    concurrency: int | None = None,
) -> list[Rule]:
    cache = cache or ExtractionCache()
    raws = list(raws)
    results: list[Rule | None] = [None] * len(raws)

    # Resolve cache hits first (cheap, no I/O races), collect the misses.
    pending: list[tuple[int, RawRule]] = []
    for i, raw in enumerate(raws):
        cached = cache.get(raw, provider.model_id, provider.prompt_version)
        if cached is not None:
            results[i] = cached
        else:
            pending.append((i, raw))

    workers = min(_resolve_concurrency(concurrency), len(pending))
    if workers <= 1:
        for i, raw in pending:
            rule = provider.extract(raw)
            cache.put(raw, provider.model_id, provider.prompt_version, rule)
            results[i] = rule
    else:
        from concurrent.futures import ThreadPoolExecutor

        def _work(item: tuple[int, RawRule]) -> tuple[int, RawRule, Rule]:
            i, raw = item
            return i, raw, provider.extract(raw)

        with ThreadPoolExecutor(max_workers=workers) as pool:
            # Cache writes happen here in the consumer (single-threaded) to avoid
            # any write contention; order is reattached via the index.
            for i, raw, rule in pool.map(_work, pending):
                cache.put(raw, provider.model_id, provider.prompt_version, rule)
                results[i] = rule

    return [r for r in results if r is not None]
