# RCG — Claude Code plugin

A thin Claude Code plugin that wraps [Rule Coherence Graph (RCG)](https://github.com/alast9/rule-coherence-graph)
so your assistant checks the rule files governing an AI agent for contradictions
**before it acts**.

It bundles three things:

- **A skill** (`rcg-check`) — teaches Claude *when* to lint rule files and *how*
  to triage the result (treat a coherence score below 0.8 as a blocker).
- **The `rcg` MCP server** — auto-connects on install, exposing `check_corpus`,
  `explain_action`, and `score_corpus` as tools.
- **A `/rcg` slash command** — `/rcg [path]` to check a corpus on demand.

The plugin carries no code of its own; it drives the published
[`rule-coherence-graph`](https://pypi.org/project/rule-coherence-graph/) package
via `uvx`, so it stays in lockstep with the tool it wraps.

## Requirements

- [uv](https://docs.astral.sh/uv/) on `PATH` (provides `uvx`). The package is
  fetched from PyPI on first use.
- No API key required — RCG falls back to an offline heuristic extractor. For
  LLM-quality extraction, set `ANTHROPIC_API_KEY` and pass `--provider anthropic`.

## Install

From the project's marketplace (the repo root hosts `.claude-plugin/marketplace.json`):

```text
/plugin marketplace add alast9/rule-coherence-graph
/plugin install rcg@rule-coherence-graph
```

Then try: `/rcg .agent/rules`, or just ask *"check my agent rules for conflicts."*

## Local development

```bash
claude --plugin-dir ./plugin          # load this plugin without a marketplace
claude plugin validate ./plugin --strict
```

> **Versioning:** `version` is set in `.claude-plugin/plugin.json`; bump it when
> you want installed users to receive updates (pushing commits alone is not
> enough once a version is pinned).
