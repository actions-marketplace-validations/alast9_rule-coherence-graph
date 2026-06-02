"""Shared detector primitives.

All three detectors (syntactic, semantic, precedence) emit findings that share a
common structural shape. The :class:`Finding` protocol captures that shape so
scoring, reporting and the baseline can treat any finding uniformly.

This module also hosts :func:`scopes_overlap`, the public scope-matching helper
reused by the syntactic and precedence passes.
"""

from __future__ import annotations

from fnmatch import fnmatch
from typing import Literal, Protocol, runtime_checkable

from rcg.schema import Rule

Severity = Literal["low", "medium", "high", "critical"]

# Action classes that carry no specific subject — the extractor's catch-all for
# rules it could not classify. Two rules sharing only such a class are NOT evidence
# that they govern the same activity, so structural passes that key off
# action-class equality (precedence) must not treat them as co-firing: doing so
# turns every unclassified pair into an O(n²) pile of spurious ambiguities (the
# dominant noise source observed at composition scale). Genuine contradictions
# between such rules are left to the semantic (LLM-judge) pass.
GENERIC_ACTION_CLASSES: frozenset[str] = frozenset({"agent.execute_action"})


def is_generic_action_class(action_class: str) -> bool:
    return action_class in GENERIC_ACTION_CLASSES


# Default thresholds for corpus-relative "hub" action classes (see
# :func:`hub_action_classes`). A class carried by a large share of the corpus is a
# generic bucket (e.g. ``code.style``), not evidence two rules govern the *same*
# concrete action. Tuned on the ARCI 10-pack pilot, where a handful of hub classes
# drove ~94% of cross-pack precedence findings and made the count swing 4x between
# extraction models purely on labelling concentration.
HUB_MIN_RULES = 6
HUB_FRACTION = 0.08


def hub_action_classes(
    rules: list[Rule],
    *,
    min_rules: int = HUB_MIN_RULES,
    fraction: float = HUB_FRACTION,
) -> frozenset[str]:
    """Action classes common enough in ``rules`` to be generic buckets.

    A class qualifies when it is carried by at least ``max(min_rules, fraction*N)``
    rules. The absolute ``min_rules`` floor makes the guard self-disable on small
    inputs (so a 2-rule pair where both share a class is never treated as a hub),
    while ``fraction`` catches dominant buckets at corpus scale. Returned classes
    carry no co-governance signal for the precedence pass and are deferred to the
    semantic (LLM-judge) pass, mirroring :data:`GENERIC_ACTION_CLASSES`.
    """
    from collections import Counter

    n = len(rules)
    if n == 0:
        return frozenset()
    threshold = max(min_rules, fraction * n)
    freq = Counter(r.trigger.action_class for r in rules)
    return frozenset(c for c, k in freq.items() if k >= threshold)


@runtime_checkable
class Finding(Protocol):
    """Structural shape shared by every detector's output.

    Members are declared as read-only properties so that ``@dataclass(frozen=True)``
    findings (whose attributes are read-only) structurally satisfy the protocol,
    and so that a finding's ``severity``/``type`` ``Literal`` types are accepted
    where the protocol only requires ``str``.
    """

    @property
    def rule_a(self) -> Rule: ...

    @property
    def rule_b(self) -> Rule: ...

    @property
    def type(self) -> str: ...

    @property
    def severity(self) -> str: ...

    @property
    def reason(self) -> str: ...


def scopes_overlap(a: Rule, b: Rule) -> bool:
    """Return ``True`` if two rules' glob scope patterns can match the same path.

    Patterns are glob-like (v1). ``*`` matches everything. We over-report rather
    than miss a real clash: a pair overlaps if either pattern matches the other.
    """
    sa, sb = a.trigger.scope_pattern, b.trigger.scope_pattern
    if sa == sb:
        return True
    return fnmatch(sa, sb) or fnmatch(sb, sa)
