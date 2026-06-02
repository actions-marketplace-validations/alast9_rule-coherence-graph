# Make your agent reach for RCG (agent-native packs)

[Connecting RCG over MCP](mcp-clients.md) gives your assistant the *hands* to run
the conflict checks. This page adds the missing half: the **trigger glue** — a few
lines in each agent's native format that tell it **when** to reach for those tools
(e.g. "before you finish editing rule files, check them") and **how** to triage the
result (e.g. "treat a coherence score below 0.8 as a blocker").

The design goal is **broad reach without five maintained code packs**: one portable
MCP server + thin, copy-paste snippets per agent. The snippets are know-how, not
forks — if a client renames a config key, the RCG tools underneath don't change.

> **Portable core.** Every snippet below assumes the `rcg` MCP server is connected.
> Set that up once per client from **[Coding assistants (MCP)](mcp-clients.md)** —
> the tools (`check_corpus`, `explain_action`, `score_corpus`) are identical
> everywhere. This page only adds the instructions that get them *used*.

---

## The one shared instruction

Every pack below is a phrasing of the same rule. Adapt the path to your corpus:

> When you create or edit agent rule files (`CLAUDE.md`, `AGENTS.md`,
> `.cursorrules`, `.agent/rules/**`, `*.rego`, `*.cedar`), before you finish, call
> the `rcg` tools to check them: run `check_corpus` (or `score_corpus`) on the
> changed corpus, report the coherence score and any findings, and treat a score
> below **0.8** as a blocker to raise with me rather than silently proceeding.

---

## Claude Code — first-class pack (plugin)

Claude Code is the one ecosystem with a native **skill + plugin** abstraction, so
RCG ships there as a proper pack rather than just a snippet: a plugin that bundles
a skill (the trigger/triage know-how above), the `rcg` MCP server (auto-connects on
install), and an `/rcg` slash command. See the README's plugin section for install.

If you'd rather not install the plugin, drop the shared instruction into your
project `CLAUDE.md` and connect the MCP server manually — same effect, more setup.

## Cursor — project rule

Cursor reads project rules from `.cursor/rules/*.md` (or a legacy `.cursorrules`).
Add a rule file, e.g. `.cursor/rules/rcg.md`:

```markdown
---
description: Check rule-file coherence with RCG before finishing rule edits
alwaysApply: true
---

When you create or edit agent rule files (CLAUDE.md, AGENTS.md, .cursorrules,
.agent/rules/**, *.rego, *.cedar), before finishing call the `rcg` MCP tools:
run `check_corpus` on the changed corpus, report the coherence score and findings,
and treat a score below 0.8 as a blocker to raise rather than silently proceeding.
```

(Connect the server first via `.cursor/mcp.json` — see the MCP guide.)

## Cline / Windsurf — custom instructions

Both expose a "custom instructions" / "rules" text box (Cline: **Settings → Custom
Instructions**; Windsurf: a `.windsurf/rules/` file or the Cascade rules panel).
Paste **[the shared instruction](#the-one-shared-instruction)** verbatim. With the
`rcg` server connected, the agent will call the tools when it touches rule files.

## Codex CLI / Gemini CLI — `AGENTS.md`

These agents read repo-level `AGENTS.md`. Add a short section:

```markdown
## Rule coherence

When editing agent rule files (AGENTS.md, CLAUDE.md, .cursorrules, .agent/rules/**),
run RCG before finishing: `uvx --from rule-coherence-graph rcg check <path>` (or the
`rcg` MCP tools where MCP is available). Report the coherence score; a score below
0.8 is a blocker. RCG: https://github.com/alast9/rule-coherence-graph
```

MCP support in these CLIs is still maturing — the `uvx … rcg check` CLI form is the
reliable fallback, and it's the same check the [GitHub Action](mcp-clients.md) runs
in CI.

---

## What this is deliberately *not*

- **Not five maintained integrations.** The only first-class, versioned artifact is
  the Claude Code plugin. Everything else is a snippet you copy once; there is no
  per-agent code for RCG to keep in sync.
- **Not a substitute for CI.** Editor-time checks catch conflicts early, but the
  authoritative gate is the [GitHub Action](mcp-clients.md) with `--min-score`.
  Belt and suspenders.
- **Not frozen.** Agent rule/instruction formats change often. The snippets above
  reflect each tool's current convention; if one moves, only the wrapper changes —
  the `rcg` tools and the CLI stay put.

> **Meta-note.** These per-agent rule/instruction files are themselves a rule corpus
> — so you can point RCG at *them*. `rcg check` over your `.cursor/rules/`,
> `AGENTS.md`, and `CLAUDE.md` together catches the case where the packs you added
> to govern different agents have started to contradict each other.
