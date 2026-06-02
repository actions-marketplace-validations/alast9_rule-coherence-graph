"""Tests for the composition analysis (ΔC) module."""

from __future__ import annotations

from rcg.compose import compose, composition_for, pack_of
from rcg.detectors.syntactic import SyntacticDetector
from rcg.schema import Directive, Modality, Rule, Source, Trigger


def _rule(
    text: str,
    file: str,
    *,
    pack: str | None = None,
    action_class: str = "deploy.production",
    modality: Modality = Modality.MUST,
) -> Rule:
    return Rule(
        raw_text=text,
        source=Source(file=file, format="markdown", pack=pack),
        trigger=Trigger(action_class=action_class, scope_pattern="*"),
        directive=Directive(modality=modality, action=text),
    )


def test_pack_of_prefers_explicit_then_path_then_file() -> None:
    assert pack_of(_rule("x", "A/a.md", pack="packA")) == "packA"
    assert pack_of(_rule("x", "packB/a.md")) == "packB"  # derived from top segment
    assert pack_of(_rule("x", "a.md")) == "a.md"  # flat corpus


def test_cross_pack_conflict_is_the_composition_penalty() -> None:
    a = _rule("require approval", "A/x.md", pack="A", modality=Modality.MUST)
    b = _rule("auto deploy", "B/y.md", pack="B", modality=Modality.MUST_NOT)
    findings = SyntacticDetector().detect([a, b])
    assert len(findings) == 1  # opposing modality, same action_class -> 1 conflict

    report = compose([a, b], findings)
    assert report.n_cross_pack == 1
    assert len(report.pairs) == 1
    pair = report.pairs[0]
    assert pair.packs == ("A", "B")
    assert pair.delta_c == 1.0  # one syntactic finding, weight 1.0
    assert pair.composition_index == 1.0 / 2  # ΔC / (n_rules A + B)
    # both packs are internally clean
    assert report.per_pack["A"].internal.score == 1.0
    assert report.per_pack["B"].internal.score == 1.0


def test_intra_pack_conflict_excluded_from_delta_c() -> None:
    # Two conflicting rules in the SAME pack: internal incoherence, ΔC = 0.
    a = _rule("require approval", "A/x.md", pack="A", modality=Modality.MUST)
    b = _rule("auto deploy", "A/y.md", pack="A", modality=Modality.MUST_NOT)
    findings = SyntacticDetector().detect([a, b])
    report = compose([a, b], findings)

    assert report.n_cross_pack == 0
    assert report.pairs == []
    assert report.per_pack["A"].internal.score < 1.0  # internal conflict counted here


def test_composition_for_arbitrary_group() -> None:
    a = _rule("a", "A/x.md", pack="A", modality=Modality.MUST)
    b = _rule("b", "B/y.md", pack="B", modality=Modality.MUST_NOT)
    c = _rule("c", "C/z.md", pack="C", action_class="db.write")
    findings = SyntacticDetector().detect([a, b, c])

    only_ab = composition_for(["A", "B"], [a, b, c], findings)
    assert only_ab.cross_count == 1
    only_ac = composition_for(["A", "C"], [a, b, c], findings)
    assert only_ac.cross_count == 0  # different action_class -> no conflict
