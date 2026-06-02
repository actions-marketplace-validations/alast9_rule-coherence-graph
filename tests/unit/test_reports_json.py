"""Tests for the JSON report renderer."""

from __future__ import annotations

import json

from rcg.detectors.syntactic import SyntacticDetector
from rcg.reports.json_report import build_report, render_json
from rcg.schema import Directive, Modality, Rule, Source, Trigger
from rcg.scoring import score_corpus


def _rule(text: str, file: str, modality: Modality) -> Rule:
    return Rule(
        raw_text=text,
        source=Source(file=file, format="markdown", pack=file.split("/")[0]),
        trigger=Trigger(action_class="deploy.production", scope_pattern="*"),
        directive=Directive(modality=modality, action=text),
    )


def test_build_report_shape() -> None:
    a = _rule("require approval", "A/x.md", Modality.MUST)
    b = _rule("auto deploy", "B/y.md", Modality.MUST_NOT)
    findings = SyntacticDetector().detect([a, b])
    score = score_corpus(2, findings)

    report = build_report(findings, score=score, suppressed=0)
    assert report["n_findings"] == 1
    assert report["score"] == round(score.score, 4)
    assert report["by_type"] == {"syntactic": 1}

    f = report["findings"][0]
    assert f["type"] == "syntactic"
    assert f["weight"] == 1.0
    assert {f["rule_a"]["pack"], f["rule_b"]["pack"]} == {"A", "B"}
    assert f["rule_a"]["action_class"] == "deploy.production"


def test_render_json_is_valid_json() -> None:
    a = _rule("require approval", "A/x.md", Modality.MUST)
    b = _rule("auto deploy", "B/y.md", Modality.MUST_NOT)
    findings = SyntacticDetector().detect([a, b])
    parsed = json.loads(render_json(findings, score=score_corpus(2, findings)))
    assert parsed["findings"][0]["rule_a"]["raw_text"]
