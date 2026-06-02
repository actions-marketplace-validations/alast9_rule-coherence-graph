---
name: rcg-check
description: >-
  Check a corpus of AI-agent rule files for contradictions before finishing.
  Use whenever the user creates or edits agent rule files — CLAUDE.md, AGENTS.md,
  .cursorrules, .cursor/rules/*, .agent/rules/**, memory.md, or policy files
  (*.rego, *.cedar) — or asks to "check rules / find rule conflicts / lint agent
  rules / check rule coherence". Runs the RCG linter and reports the coherence
  score and findings.
allowed-tools:
  - "Bash(uvx --from rule-coherence-graph rcg check *)"
  - "Bash(uvx --from rule-coherence-graph rcg score *)"
  - "Bash(uvx --from rule-coherence-graph rcg explain *)"
  - "Bash(rcg check *)"
  - "Bash(rcg score *)"
  - "Bash(rcg explain *)"
  - "Read"
---

# Check rule coherence with RCG

RCG (Rule Coherence Graph) lints the rule corpus that governs an AI coding agent
and reports the **conflicts** the agent would otherwise resolve silently. Use it
to check rule files *before* finishing a change to them.

## When to run

Reach for this whenever you have just created or edited agent rule files, or the
user asks to check/lint rules. Rule files include: `CLAUDE.md`, `AGENTS.md`,
`.cursorrules`, `.cursor/rules/*`, `.agent/rules/**`, `memory.md`, and policy
files (`*.rego`, `*.cedar`).

## How to run

Run the CLI with the Bash tool (zero-install via `uvx`; works without an API key
using the offline heuristic extractor):

```bash
uvx --from rule-coherence-graph rcg check --no-graph <path-to-corpus>
```

- Always pass **`--no-graph`** — it skips Neo4j, which most machines won't have
  running (without it the command aborts with a connection error). Drop it only
  if the user explicitly wants to persist the graph to a running Neo4j.
- `<path-to-corpus>` is the directory (or file) holding the rule files — e.g.
  `.agent/rules`, `.cursor/rules`, `CLAUDE.md`, or `.` to scan the repo root.
- For just the number: `uvx --from rule-coherence-graph rcg score --no-graph <path>`.
- To trace one action: `uvx --from rule-coherence-graph rcg explain "<action>" <path>`
  (no `--no-graph` — `explain` doesn't touch Neo4j).

> If the `rcg` MCP server is connected (this plugin bundles it), you may instead
> call its `check_corpus` / `score_corpus` / `explain_action` tools — same result.
> The CLI above is the reliable fallback and needs no server.

## How to report the result

1. State the **coherence score** (0–1; 1.0 = no detected conflicts).
2. List each finding with **both rules' original text** and their source
   `file:line` — RCG always surfaces the evidence so the user can adjudicate.
3. Group by type: **syntactic** (opposing modality / approval stance — high
   confidence), **precedence** (co-firing rules with no declared order),
   **semantic** (meaning clash; only with `--semantic`).
4. **Triage:** treat a score **below 0.8** as a blocker to raise with the user
   rather than silently proceeding. Suggest which rule to change, but let the
   **human decide** the resolution — RCG detects, it does not auto-fix.

## Notes

- **Offline by default.** No key needed; nothing leaves the machine. For
  LLM-quality extraction add `--provider anthropic` with `ANTHROPIC_API_KEY` set.
- **False positives happen.** Extraction is heuristic/LLM-based; always show the
  evidence and the confidence, never assert a conflict without the two texts.
- **CI is the real gate.** Editor-time checks catch conflicts early; the
  authoritative gate is the RCG GitHub Action with `--min-score`.
