"""Discovery sets source.pack from the top path segment (pack attribution)."""

from __future__ import annotations

from pathlib import Path

from rcg.parsers.discovery import discover


def test_discovery_sets_pack_from_top_segment(tmp_path: Path) -> None:
    (tmp_path / "packA").mkdir()
    (tmp_path / "packA" / "CLAUDE.md").write_text("# H\n- rule a one\n")
    (tmp_path / "packB").mkdir()
    (tmp_path / "packB" / "CLAUDE.md").write_text("# H\n- rule b one\n")
    # A file directly under the root belongs to no distinct pack.
    (tmp_path / "CLAUDE.md").write_text("# H\n- root rule\n")

    raws = discover(tmp_path)
    by_file = {r.source.file: r.source.pack for r in raws}

    assert by_file["packA/CLAUDE.md"] == "packA"
    assert by_file["packB/CLAUDE.md"] == "packB"
    assert by_file["CLAUDE.md"] is None
