"""Tests for the bullet-less fallback in markdown/mdc rule extraction.

Some .cursorrules/.mdc files express rules as prose paragraphs or as quoted items
inside a `name = [ ... ]` list literal. The fallback recovers those, but ONLY when
a file has no top-level bullets (bullet files must be unaffected)."""

from __future__ import annotations

from pathlib import Path

from rcg.parsers.mdc import MdcParser


def test_prose_paragraph_fallback(tmp_path: Path) -> None:
    f = tmp_path / "p.mdc"
    f.write_text(
        "---\ndescription: Anti-overeng\n---\n"
        "# Anti-Over-Engineering\n\n"
        "Only change what was asked. Simplest solution first. When unsure, ask.\n"
    )
    texts = [r.text for r in MdcParser().parse(f)]
    assert "Only change what was asked." in texts
    assert "Simplest solution first." in texts
    assert "When unsure, ask." in texts


def test_list_literal_fallback(tmp_path: Path) -> None:
    f = tmp_path / "p.mdc"
    f.write_text(
        "---\ndescription: FastAPI\n---\n"
        "# FastAPI best practices\n\n"
        "best_practices = [\n"
        '    "Use Pydantic models for schemas",\n'
        '    "Implement dependency injection",\n'
        "]\n"
    )
    texts = [r.text for r in MdcParser().parse(f)]
    assert "Use Pydantic models for schemas" in texts
    assert "Implement dependency injection" in texts


def test_triple_quoted_block_is_skipped(tmp_path: Path) -> None:
    f = tmp_path / "p.mdc"
    f.write_text(
        "# Layout\n\n"
        'folder_structure = """\n'
        "app/\n  main.py\n"
        '"""\n'
        "Always keep handlers thin.\n"
    )
    texts = [r.text for r in MdcParser().parse(f)]
    assert "Always keep handlers thin." in texts
    assert not any("main.py" in t for t in texts)


def test_bullets_take_precedence_no_fallback(tmp_path: Path) -> None:
    # When real bullets exist, the prose line must NOT be turned into a rule.
    f = tmp_path / "p.mdc"
    f.write_text("# H\n- a real bullet rule\nsome stray prose sentence here.\n")
    texts = [r.text for r in MdcParser().parse(f)]
    assert texts == ["a real bullet rule"]
