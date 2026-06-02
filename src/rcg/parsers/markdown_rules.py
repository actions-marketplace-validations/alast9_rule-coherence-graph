"""Parser for markdown rule files: CLAUDE.md, AGENTS.md, memory.md, .agent/rules/*.md.

Splitting heuristic: each top-level markdown bullet (`- ` or `* ` at column 0,
with optional continuation lines indented under it) becomes one RawRule. The
nearest preceding `#`-level heading is captured as `source.section`.
"""

from __future__ import annotations

import re
from pathlib import Path

from rcg.schema import RawRule, Source

_BULLET = re.compile(r"^[-*]\s+(.+)$")
_HEADING = re.compile(r"^(#+)\s+(.+)$")
_CONTINUATION_INDENT = re.compile(r"^[ \t]+\S")

# Fallback (no-bullet) recognisers. Some .cursorrules/.mdc files express rules as
# prose paragraphs or as quoted items inside a `name = [ "...", "..." ]` list
# literal rather than markdown bullets; without a fallback those parse to zero
# rules. These fire ONLY when a file contains no top-level bullets, so bullet
# files are completely unaffected.
_LIST_OPEN = re.compile(r"^\s*[A-Za-z_]\w*\s*=\s*\[")
_TRIPLE_QUOTE = re.compile(r'"""|\'\'\'')
_QUOTED = re.compile(r"""(?:"([^"]+)"|'([^']+)')""")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_CODEY = re.compile(r"^\s*[\]\}\)]|^\s*[A-Za-z_]\w*\s*=\s*[\"'\[{]?\s*$")


def has_markdown_bullets(lines: list[str]) -> bool:
    """Return True if any line is a markdown bullet (`- ` / `* `) at column 0."""
    return any(_BULLET.match(line) for line in lines)


def extract_markdown_rules(
    lines: list[str],
    *,
    file: str,
    fmt: str,
    line_offset: int = 0,
    default_section: str | None = None,
) -> list[RawRule]:
    """Extract bullet rules + nearest-heading sections from markdown lines.

    ``line_offset`` is added to every recorded line number so callers that
    stripped a prefix (e.g. YAML frontmatter) still report 1-based positions
    relative to the original file. ``default_section`` seeds the section for
    bullets that appear before the first heading.
    """
    rules: list[RawRule] = []
    section: str | None = default_section

    i = 0
    while i < len(lines):
        line = lines[i]
        heading = _HEADING.match(line)
        if heading:
            section = heading.group(2).strip()
            i += 1
            continue

        bullet = _BULLET.match(line)
        if not bullet:
            i += 1
            continue

        start_line = i + 1 + line_offset
        parts = [bullet.group(1).strip()]
        j = i + 1
        while j < len(lines) and _CONTINUATION_INDENT.match(lines[j]):
            parts.append(lines[j].strip())
            j += 1
        end_line = j + line_offset  # j is exclusive index → 1-based inclusive end
        text = " ".join(p for p in parts if p)

        rules.append(
            RawRule(
                text=text,
                source=Source(
                    file=file,
                    line_start=start_line,
                    line_end=end_line,
                    format=fmt,
                    section=section,
                ),
            )
        )
        i = j

    if rules:
        return rules
    # No bullets found anywhere: fall back to prose + list-literal extraction so
    # bullet-less rule files (common in older .cursorrules/.mdc) still yield rules.
    return _extract_fallback_rules(
        lines, file=file, fmt=fmt, line_offset=line_offset, default_section=default_section
    )


def _extract_fallback_rules(
    lines: list[str],
    *,
    file: str,
    fmt: str,
    line_offset: int,
    default_section: str | None,
) -> list[RawRule]:
    """Extract rules from a bullet-less body: quoted items in `name = [...]` list
    literals, and otherwise prose split into sentences. Triple-quoted blocks (e.g.
    a folder-structure dump) are skipped — they are illustrative, not rules."""
    rules: list[RawRule] = []
    section: str | None = default_section
    in_list = False
    in_triple = False

    def add(text: str, line_idx: int) -> None:
        text = text.strip()
        if len(text.split()) < 2:  # drop fragments / single tokens
            return
        ln = line_idx + 1 + line_offset
        rules.append(
            RawRule(
                text=text,
                source=Source(
                    file=file, line_start=ln, line_end=ln, format=fmt, section=section
                ),
            )
        )

    for idx, line in enumerate(lines):
        if in_triple:
            if _TRIPLE_QUOTE.search(line):
                in_triple = False
            continue
        heading = _HEADING.match(line)
        if heading:
            section = heading.group(2).strip()
            in_list = False
            continue
        if not in_list and _TRIPLE_QUOTE.search(line):
            # opening triple-quote with no closing one on the same line
            if len(_TRIPLE_QUOTE.findall(line)) % 2 == 1:
                in_triple = True
            continue
        if _LIST_OPEN.match(line):
            in_list = True
        if in_list:
            for m in _QUOTED.finditer(line):
                add(m.group(1) or m.group(2), idx)
            if "]" in line:
                in_list = False
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")) or _CODEY.match(line):
            continue
        for sentence in _SENTENCE_SPLIT.split(stripped):
            add(sentence, idx)

    return rules


class MarkdownRulesParser:
    format = "markdown"

    _RECOGNISED_NAMES = {"CLAUDE.md", "AGENTS.md", "memory.md"}

    def matches(self, path: Path) -> bool:
        if path.suffix != ".md":
            return False
        if path.name in self._RECOGNISED_NAMES:
            return True
        return ".agent" in path.parts and "rules" in path.parts

    def parse(self, path: Path) -> list[RawRule]:
        lines = path.read_text(encoding="utf-8").splitlines()
        return extract_markdown_rules(lines, file=str(path), fmt=self.format)
