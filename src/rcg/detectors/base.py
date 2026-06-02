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
