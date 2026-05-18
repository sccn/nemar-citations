@AGENTS.md

## Claude Code Specific Instructions

The shared project instructions live in `AGENTS.md`; this file imports them for Claude Code with `@AGENTS.md`.

### Plan documents
- `plan.md` (gitignored, repo root) — personal planning scratchpad. Update regularly during development.
- `scratch_notes.md` (gitignored, repo root) — technical notes and research findings.

### Tooling
- **Playwright MCP** — web automation and visual analysis (NEMAR.org design research, dashboard QA)
- **Serena MCP** — code intelligence (see `.rules/serena_mcp.md`)
- `/review-pr` — multi-agent PR review skill from the pr-review-toolkit plugin

### Plan mode
Use `/plan` before non-trivial implementations; align on the approach before changing files.

Keep cross-agent project rules in `AGENTS.md` so Codex, Copilot, Cursor, and other AGENTS.md-aware tools stay aligned. Append only Claude-specific plugin / skill / command / MCP guidance below.
