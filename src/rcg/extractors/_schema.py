"""Shared extraction prompt, tool schema, and payload→Rule mapping.

Both the Anthropic and OpenAI-compatible providers normalise rules into the same
structured payload (``action_class``, ``scope_pattern``, ``modality``, ``action``,
``confidence``, ``original_language``, ``tags``, ``approval_stance``) and then call
:func:`to_rule`. Keeping the prompt, tool schema, and mapping here means there is a
single source of truth — bumping :data:`PROMPT_VERSION` invalidates every provider's
extraction cache identically.
"""

from __future__ import annotations

from typing import Any

from rcg.detectors.syntactic import APPROVAL_STANCES
from rcg.schema import Directive, Modality, RawRule, Rule, Source, Trigger

PROMPT_VERSION = "2026-06-01.v3"

TOOL_NAME = "record_rule"

# Keys the tool schema marks as required; providers validate against this list
# before mapping so a malformed structured response is caught (and retried).
REQUIRED_KEYS: tuple[str, ...] = (
    "action_class",
    "scope_pattern",
    "modality",
    "action",
    "confidence",
    "original_language",
    "tags",
)

TOOL_SCHEMA: dict[str, Any] = {
    "name": TOOL_NAME,
    "description": "Record the structured form of a single agent rule.",
    "input_schema": {
        "type": "object",
        "required": list(REQUIRED_KEYS),
        "properties": {
            "action_class": {
                "type": "string",
                "description": (
                    "Dotted verb class naming the SPECIFIC activity the rule governs, "
                    "as `<domain>.<verb>`. Pick the narrowest class that fits the rule's "
                    "actual subject. Examples: deploy.production, db.write, fs.delete, "
                    "rules.modify_self, permissions.grant, code.style, code.structure, "
                    "code.naming, error.handling, deps.manage, testing.write, docs.write, "
                    "logging.write, secrets.handle, vcs.commit. "
                    "Do NOT use the catch-all 'agent.execute_action' for ordinary coding/"
                    "style/content rules — reserve 'agent.*' for rules about the AGENT's "
                    "own runtime behaviour (autonomy, confirmation, scope of edits). Two "
                    "rules should share an action_class ONLY when they genuinely govern the "
                    "same activity, because the detectors treat a shared class as grounds "
                    "for a conflict."
                ),
            },
            "scope_pattern": {
                "type": "string",
                "description": "Glob-like scope. Use '*' if the rule has no narrower scope.",
            },
            "modality": {
                "type": "string",
                "enum": [m.value for m in Modality],
            },
            "action": {
                "type": "string",
                "description": (
                    "Normalised English summary of what the rule requires or forbids. "
                    "Always English, even when raw_text is in another language."
                ),
            },
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
            "original_language": {
                "type": "string",
                "description": (
                    "BCP-47 language tag of the raw_text. Use 'en' for English, "
                    "'vi' for Vietnamese, etc."
                ),
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "e.g. security, autonomy, style, data, rules-meta.",
            },
            "approval_stance": {
                "type": "string",
                "enum": ["requires_human_approval", "bypasses_human_approval", "none"],
                "description": (
                    "Human-in-the-loop stance. Use 'requires_human_approval' if the "
                    "rule demands human approval/confirmation before acting (this "
                    "INCLUDES prohibitions phrased as 'do not X without approval'); "
                    "'bypasses_human_approval' if it removes the human gate (e.g. "
                    "auto-deploy, never prompt, act immediately); 'none' if the rule "
                    "is not about approval gating."
                ),
            },
        },
    },
}

SYSTEM = """You normalise AI-agent rules into a canonical structured form.

For each rule you receive, call the `record_rule` tool exactly once.

Translation policy: if the rule text is not in English, set `original_language`
to the BCP-47 tag of the source language and write the `action` field in English.
The original verbatim text will be preserved separately; do not translate it.

Modality mapping:
- "must", "always", "never" -> MUST or MUST_NOT
- "should", "prefer", "avoid" -> SHOULD or SHOULD_NOT
- "may", "can" -> MAY

action_class granularity: choose the *narrowest* `<domain>.<verb>` class that names
what the rule is actually about (e.g. a rule about chaining helper calls is
`code.style`, a rule about avoiding `eval` is `secrets.handle` or `code.security`,
a rule about writing tests is `testing.write`). The catch-all `agent.execute_action`
is for genuine agent-runtime behaviour only — never the default for code/style/content
rules. Over-using one class manufactures false conflicts between unrelated rules.

When a rule grants or describes a permission the agent has (e.g. "agent may modify
its rule files"), use MAY and set action_class to `rules.modify_self` or similar
meta-class — these are flagged as critical at the detector layer.

Set `approval_stance` to capture the human-in-the-loop posture: use
`requires_human_approval` when the rule demands human approval/confirmation before
acting (this INCLUDES prohibitions phrased as "do not X without approval"), use
`bypasses_human_approval` when the rule removes the human gate (auto-deploy, never
prompt, act immediately), and `none` when the rule is not about approval gating.
The detector treats two approval-gated rules as conflicting only when their
stances differ, so classify this carefully.
"""


def user_content(raw: RawRule) -> str:
    """Build the user message the extractor sends for one raw rule."""
    return (
        f"Rule text (verbatim, may not be English):\n{raw.text}\n\n"
        f"Source file: {raw.source.file}\n"
        f"Section: {raw.source.section or '(none)'}\n"
    )


def to_rule(raw: RawRule, payload: dict[str, Any]) -> Rule:
    """Map a structured extraction payload onto a canonical :class:`Rule`."""
    lang = payload.get("original_language") or "en"
    source = Source(
        file=raw.source.file,
        line_start=raw.source.line_start,
        line_end=raw.source.line_end,
        format=raw.source.format,
        section=raw.source.section,
        original_language=None if lang == "en" else lang,
        pack=raw.source.pack,
    )
    stance = payload.get("approval_stance")
    conditions = [stance] if stance in APPROVAL_STANCES else []
    return Rule(
        raw_text=raw.text,
        source=source,
        trigger=Trigger(
            action_class=payload["action_class"],
            scope_pattern=payload.get("scope_pattern", "*"),
            context_conditions=conditions,
        ),
        directive=Directive(
            modality=Modality(payload["modality"]),
            action=payload["action"],
        ),
        confidence=float(payload.get("confidence", 1.0)),
        tags=list(payload.get("tags", [])),
    )
