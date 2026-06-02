# Release notes

## v0.6.0 — Pack composition (ΔC), precision & batch

Adds **composition analysis** — measuring conflict that exists only when rule
*packs* are combined — plus precision, parser-coverage, and throughput work that
make population-scale analysis (the ARCI program) viable.

### Added
- **`rcg compose <packs…>` + `rcg.compose` module.** Point it at two or more packs
  (or one directory whose sub-directories are packs); it runs one union ingest and
  reports each pack's internal coherence and every pack pair's composition penalty:
  `ΔC = Σ type_weight(f)` over cross-pack findings, and
  `composition_index = ΔC / (n_rules(A)+n_rules(B))`. `--json[ --findings]` emits a
  machine-readable report; `--min-index` gates CI.
- **Pack attribution.** `Source.pack` carries the pack a rule came from. Discovery
  sets it from the top path segment (one directory per pack); `compose` sets it
  authoritatively. `pack` is **not** part of `Rule.id`, so existing caches stay valid.
- **JSON output.** `rcg check --json` and `rcg score --json` emit stable structured
  reports (new `rcg.reports.json_report`) so downstream tools needn't scrape markdown.
- **Parallel extraction.** `extract_all` now extracts uncached rules concurrently
  (thread pool; cache hits resolved first, input order preserved → deterministic).
  Tune with `--concurrency N` or `RCG_EXTRACT_CONCURRENCY` (default 8).

### Changed
- **action_class precision.** The extraction prompt now pushes specific
  `<domain>.<verb>` action classes and explicitly discourages the
  `agent.execute_action` catch-all for ordinary code/style/content rules — a coarse
  class manufactured false conflicts between unrelated rules. Prompt version bumped
  to `2026-06-01.v3` (re-extracts on next run; cache for older versions is untouched).
- **Precedence guard.** The precedence pass no longer flags pairs that share only the
  unclassified `agent.execute_action` catch-all class: a shared catch-all is not
  evidence two rules govern the same action. This removes the dominant source of
  O(n²) spurious ambiguities seen at composition scale. Genuine contradictions
  between such rules are left to the semantic (judge) pass.

### Fixed
- **Bullet-less rule files now parse.** `MdcParser` / markdown extraction gained a
  fallback (used only when a file has no top-level bullets) that recovers rules from
  prose paragraphs and from quoted items in `name = [ "…", "…" ]` list literals.
  Previously such `.mdc`/`.cursorrules` files extracted **zero** rules. Triple-quoted
  illustrative blocks (e.g. a folder-structure dump) are skipped.

### Notes
- For trustworthy ΔC, run `compose` with `--semantic` so the LLM judge confirms
  contradictions; syntactic+precedence alone over-report when action classes are coarse.
- All 232 unit/integration tests pass; ruff + mypy clean.
