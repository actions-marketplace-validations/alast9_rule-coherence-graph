"""Tests for the precedence detector."""

from __future__ import annotations

from rcg.detectors.precedence import PrecedenceDetector
from rcg.schema import Directive, Modality, Rule, Source, Trigger


def _rule(
    text: str,
    file: str,
    action_class: str = "rules.precedence",
    precedence_over: tuple[str, ...] = (),
) -> Rule:
    return Rule(
        raw_text=text,
        source=Source(file=file, format="markdown"),
        trigger=Trigger(action_class=action_class, scope_pattern="*"),
        directive=Directive(modality=Modality.MUST, action="x"),
        priority={"declared_precedence_over": list(precedence_over)},
    )


def test_cross_file_unordered_pair_flagged() -> None:
    a = _rule("cursor wins", "a.md")
    b = _rule("agent wins", "b.md")
    found = PrecedenceDetector().detect([a, b])
    assert len(found) == 1
    assert found[0].type == "precedence"
    assert found[0].severity == "critical"  # rules.* action class


def test_declared_order_suppresses() -> None:
    b = _rule("agent wins", "b.md")
    a = _rule("cursor wins", "a.md", precedence_over=(b.id,))
    found = PrecedenceDetector().detect([a, b])
    assert found == []


def test_same_file_not_flagged() -> None:
    a = _rule("rule one", "same.md")
    b = _rule("rule two", "same.md")
    found = PrecedenceDetector().detect([a, b])
    assert found == []


def test_excluded_pair_not_flagged() -> None:
    a = _rule("cursor wins", "a.md")
    b = _rule("agent wins", "b.md")
    exclude = {frozenset({a.id, b.id})}
    found = PrecedenceDetector().detect([a, b], exclude=exclude)
    assert found == []


def test_non_co_firing_not_flagged() -> None:
    a = _rule("a", "a.md", action_class="deploy.release")
    b = _rule("b", "b.md", action_class="data.export")
    found = PrecedenceDetector().detect([a, b])
    assert found == []


def test_non_rules_action_class_is_medium() -> None:
    a = _rule("a", "a.md", action_class="deploy.release")
    b = _rule("b", "b.md", action_class="deploy.release")
    found = PrecedenceDetector().detect([a, b])
    assert len(found) == 1
    assert found[0].severity == "medium"


def test_generic_catch_all_action_class_not_flagged() -> None:
    # Two rules sharing only the unclassified catch-all class are not evidence of
    # co-firing — flagging them is the O(n^2) precedence noise the guard removes.
    a = _rule("a", "a.md", action_class="agent.execute_action")
    b = _rule("b", "b.md", action_class="agent.execute_action")
    found = PrecedenceDetector().detect([a, b])
    assert found == []


def test_hub_action_class_deferred() -> None:
    # A class carried by a large share of the corpus is a generic bucket, not
    # evidence two rules govern the same concrete action. Cross-file pairs on it
    # are deferred to the semantic pass, killing the O(n^2) precedence explosion.
    rules = [
        _rule(f"style rule {i}", f"pack{i % 4}.md", action_class="code.style")
        for i in range(10)
    ]
    found = PrecedenceDetector().detect(rules)
    assert found == []  # code.style is 10/10 of the corpus -> hub -> all deferred


def test_specific_class_still_flagged_amid_hub() -> None:
    # In the same corpus, a *specific* (non-hub) class that two cross-file rules
    # share still raises a precedence ambiguity. Hub suppression must not silence
    # genuine narrow co-governance.
    rules = [
        _rule(f"style {i}", f"pack{i % 3}.md", action_class="code.style")
        for i in range(8)
    ]
    rules.append(_rule("deploy A", "pack-a.md", action_class="deploy.release"))
    rules.append(_rule("deploy B", "pack-b.md", action_class="deploy.release"))
    found = PrecedenceDetector().detect(rules)
    assert len(found) == 1
    assert found[0].rule_a.trigger.action_class == "deploy.release"


def test_hub_guard_can_be_disabled() -> None:
    # hub_fraction > 1.0 disables the guard, restoring the pre-fix behavior.
    rules = [
        _rule(f"style {i}", f"pack{i % 2}.md", action_class="code.style")
        for i in range(10)
    ]
    found = PrecedenceDetector(hub_fraction=2.0).detect(rules)
    assert len(found) > 0


def test_small_corpus_below_floor_unaffected() -> None:
    # The absolute min_rules floor self-disables the hub guard on small inputs:
    # two rules sharing a class are still flagged even though the class is 100%
    # of the (tiny) corpus.
    a = _rule("a", "a.md", action_class="deploy.release")
    b = _rule("b", "b.md", action_class="deploy.release")
    found = PrecedenceDetector().detect([a, b])
    assert len(found) == 1
