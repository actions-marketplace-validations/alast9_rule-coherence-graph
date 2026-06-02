---
description: Check a rule corpus for conflicts and report its coherence score (RCG)
argument-hint: "[path] (default: .)"
allowed-tools:
  - "Bash(uvx --from rule-coherence-graph rcg check *)"
  - "Bash(uvx --from rule-coherence-graph rcg score *)"
  - "Read"
---

Run the RCG rule-coherence linter over the corpus at `$ARGUMENTS` (default to the
current directory `.` if no path is given), then report the results.

Steps:

1. Run: `uvx --from rule-coherence-graph rcg check --no-graph $ARGUMENTS`
   (if `$ARGUMENTS` is empty, use `.`). `--no-graph` skips Neo4j, which the user
   most likely isn't running; without it the command aborts with a connection error.
2. Report the **coherence score** and each finding, grouped by type (syntactic,
   precedence, semantic), quoting **both rules' original text** and their
   `file:line` as evidence.
3. Treat a score **below 0.8** as a blocker: call it out clearly and suggest
   which rule to review — but leave the resolution to the user (RCG detects, it
   does not auto-fix).
