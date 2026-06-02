"""Render detector findings + score as a stable machine-readable JSON object.

Sibling of :mod:`rcg.reports.markdown`. The shape is intentionally flat and stable
so downstream tools (e.g. the ARCI aggregator) can consume `rcg check --json` /
`rcg score --json` without scraping the markdown report.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any

from rcg.compose import pack_of
from rcg.detectors.base import Finding
from rcg.scoring import TYPE_WEIGHTS

if TYPE_CHECKING:
    from rcg.schema import Rule
    from rcg.scoring import ScoreReport


def build_report(
    findings: Sequence[Finding],
    score: ScoreReport | None = None,
    suppressed: int = 0,
) -> dict[str, Any]:
    """Build the JSON-serialisable report dict."""
    report: dict[str, Any] = {"type_weights": TYPE_WEIGHTS}
    if score is not None:
        report["score"] = round(score.score, 4)
        report["n_rules"] = score.n_rules
        report["weighted_penalty"] = round(score.weighted, 4)
        report["by_type"] = score.by_type
    report["suppressed"] = suppressed
    report["n_findings"] = len(findings)
    report["findings"] = [_finding(f) for f in findings]
    return report


def render_json(
    findings: Sequence[Finding],
    score: ScoreReport | None = None,
    suppressed: int = 0,
    *,
    indent: int | None = 2,
) -> str:
    return json.dumps(build_report(findings, score, suppressed), indent=indent)


def _finding(f: Finding) -> dict[str, Any]:
    return {
        "type": f.type,
        "severity": f.severity,
        "weight": TYPE_WEIGHTS.get(f.type, 1.0),
        "reason": f.reason,
        "rule_a": _rule(f.rule_a),
        "rule_b": _rule(f.rule_b),
    }


def _rule(r: Rule) -> dict[str, Any]:
    return {
        "id": r.id,
        "pack": pack_of(r),
        "file": r.source.file,
        "line_start": r.source.line_start,
        "action_class": r.trigger.action_class,
        "scope": r.trigger.scope_pattern,
        "modality": r.directive.modality.value,
        "raw_text": r.raw_text,
        "action": r.directive.action,
        "original_language": r.source.original_language,
    }
