"""Composition analysis: measure conflict that arises only when rule *packs* are
combined.

A *pack* is one independently-installed rule/skill bundle (``source.pack``). Two
packs can each be internally coherent yet contradict each other when stacked. The
composition penalty for a group ``G`` of packs is the weighted set of *cross-pack*
findings — findings whose two rules belong to different packs::

    ΔC(G)             = Σ type_weight(f)  for f in findings with pack(rule_a) != pack(rule_b)
    composition_index = ΔC(G) / n_rules(G)

Because every detector is pairwise and deterministic, the cross-pack findings of a
single union run *are* exactly ``conflicts(∪G) − Σ conflicts(Pᵢ)`` — so one ingest
over all packs yields every pack's internal score and every pair's ΔC at once.
This module computes that from already-extracted rules and already-run findings;
the CLI ``compose`` command wires ingest + detect + this together and emits JSON.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import combinations
from typing import Any

from rcg.detectors.base import Finding
from rcg.schema import Rule
from rcg.scoring import TYPE_WEIGHTS, ScoreReport, score_corpus


def pack_of(rule: Rule) -> str:
    """The pack a rule belongs to: explicit ``source.pack``, else the top path
    segment of ``source.file``, else the file itself (flat corpus)."""
    if rule.source.pack:
        return rule.source.pack
    file = rule.source.file
    return file.split("/", 1)[0] if "/" in file else file


def _weight(f: Finding) -> float:
    return TYPE_WEIGHTS.get(f.type, 1.0)


@dataclass
class PackCoherence:
    """One pack's internal (intra-pack) coherence."""

    pack: str
    n_rules: int
    internal: ScoreReport

    def to_dict(self) -> dict[str, Any]:
        return {
            "pack": self.pack,
            "n_rules": self.n_rules,
            "internal_score": round(self.internal.score, 4),
            "weighted_penalty": round(self.internal.weighted, 4),
            "by_type": self.internal.by_type,
            "n_internal_findings": sum(self.internal.by_type.values()),
            "conflict_density": (
                round(sum(self.internal.by_type.values()) / self.n_rules, 4)
                if self.n_rules
                else 0.0
            ),
        }


@dataclass
class Composition:
    """The composition penalty for one group (pair, stack) of packs."""

    packs: tuple[str, ...]
    n_rules: int
    delta_c: float
    cross_count: int
    by_type: dict[str, int]
    composition_index: float
    cross_findings: list[Finding] = field(default_factory=list)

    def to_dict(self, *, include_findings: bool = False) -> dict[str, Any]:
        d: dict[str, Any] = {
            "packs": list(self.packs),
            "n_rules": self.n_rules,
            "delta_c": round(self.delta_c, 4),
            "cross_count": self.cross_count,
            "by_type": self.by_type,
            "composition_index": round(self.composition_index, 4),
        }
        if include_findings:
            d["cross_findings"] = [_finding_dict(f) for f in self.cross_findings]
        return d


@dataclass
class CompositionReport:
    packs: list[str]
    per_pack: dict[str, PackCoherence]
    pairs: list[Composition]
    n_rules: int
    n_findings: int
    n_cross_pack: int

    def to_dict(self, *, include_findings: bool = False) -> dict[str, Any]:
        return {
            "type_weights": TYPE_WEIGHTS,
            "n_packs": len(self.packs),
            "n_rules": self.n_rules,
            "n_findings": self.n_findings,
            "n_cross_pack_findings": self.n_cross_pack,
            "packs": self.packs,
            "internal": {p: c.to_dict() for p, c in self.per_pack.items()},
            "pairs": [c.to_dict(include_findings=include_findings) for c in self.pairs],
        }


def _finding_dict(f: Finding) -> dict[str, Any]:
    return {
        "type": f.type,
        "severity": f.severity,
        "weight": _weight(f),
        "reason": f.reason,
        "rule_a": _rule_dict(f.rule_a),
        "rule_b": _rule_dict(f.rule_b),
    }


def _rule_dict(r: Rule) -> dict[str, Any]:
    return {
        "pack": pack_of(r),
        "file": r.source.file,
        "action_class": r.trigger.action_class,
        "modality": r.directive.modality.value,
        "text": r.raw_text[:240],
    }


def _split(
    rules: Sequence[Rule], findings: Sequence[Finding]
) -> tuple[
    dict[str, list[Rule]], dict[str, list[Finding]], dict[frozenset[str], list[Finding]]
]:
    rules_by_pack: dict[str, list[Rule]] = defaultdict(list)
    for r in rules:
        rules_by_pack[pack_of(r)].append(r)
    intra: dict[str, list[Finding]] = defaultdict(list)
    cross: dict[frozenset[str], list[Finding]] = defaultdict(list)
    for f in findings:
        pa, pb = pack_of(f.rule_a), pack_of(f.rule_b)
        if pa == pb:
            intra[pa].append(f)
        else:
            cross[frozenset({pa, pb})].append(f)
    return rules_by_pack, intra, cross


def composition_for(
    group: Sequence[str], rules: Sequence[Rule], findings: Sequence[Finding]
) -> Composition:
    """Composition penalty for an arbitrary group of packs."""
    members = set(group)
    n_rules = sum(1 for r in rules if pack_of(r) in members)
    cross = [
        f
        for f in findings
        if pack_of(f.rule_a) != pack_of(f.rule_b)
        and pack_of(f.rule_a) in members
        and pack_of(f.rule_b) in members
    ]
    delta_c = sum(_weight(f) for f in cross)
    return Composition(
        packs=tuple(sorted(members)),
        n_rules=n_rules,
        delta_c=delta_c,
        cross_count=len(cross),
        by_type=dict(Counter(f.type for f in cross)),
        composition_index=(delta_c / n_rules if n_rules else 0.0),
        cross_findings=cross,
    )


def compose(rules: Sequence[Rule], findings: Sequence[Finding]) -> CompositionReport:
    """Full composition report: per-pack internal coherence + every pack pair's ΔC."""
    rules_by_pack, intra, cross = _split(rules, findings)
    packs = sorted(rules_by_pack)

    per_pack = {
        p: PackCoherence(
            pack=p,
            n_rules=len(rules_by_pack[p]),
            internal=score_corpus(len(rules_by_pack[p]), intra[p]),
        )
        for p in packs
    }

    pairs = [
        composition_for((a, b), rules, findings)
        for a, b in combinations(packs, 2)
        if cross.get(frozenset({a, b}))
    ]
    pairs.sort(key=lambda c: c.composition_index, reverse=True)

    return CompositionReport(
        packs=packs,
        per_pack=per_pack,
        pairs=pairs,
        n_rules=len(rules),
        n_findings=len(findings),
        n_cross_pack=sum(len(v) for v in cross.values()),
    )
