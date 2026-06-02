"""CLI tests for `rcg compose` (offline, mock provider)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from rcg.cli import app


def _make_packs(root: Path) -> None:
    (root / "safety").mkdir()
    (root / "safety" / "CLAUDE.md").write_text(
        "# Safety\n- Always require explicit human approval before any deploy to production.\n"
    )
    (root / "autonomy").mkdir()
    (root / "autonomy" / "CLAUDE.md").write_text(
        "# Autonomy\n- Auto-deploy every merge to production; never prompt for confirmation.\n"
    )


def test_compose_reports_cross_pack_penalty(tmp_path: Path) -> None:
    _make_packs(tmp_path)
    result = CliRunner().invoke(
        app,
        ["compose", str(tmp_path), "--provider", "mock", "--json"],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["n_packs"] == 2
    assert set(report["packs"]) == {"safety", "autonomy"}
    # the two packs take opposing approval stances on deploy.production -> cross-pack ΔC
    assert report["n_cross_pack_findings"] >= 1
    assert any(set(p["packs"]) == {"safety", "autonomy"} for p in report["pairs"])


def test_compose_requires_two_packs(tmp_path: Path) -> None:
    (tmp_path / "only").mkdir()
    (tmp_path / "only" / "CLAUDE.md").write_text("# X\n- a single rule\n")
    result = CliRunner().invoke(app, ["compose", str(tmp_path / "only"), "--provider", "mock"])
    assert result.exit_code == 2
    assert "at least 2 packs" in result.output
