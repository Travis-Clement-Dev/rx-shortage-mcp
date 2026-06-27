# Engineering Journal

Chronological narrative + cumulative lessons. Milestone status → ClickUp `86bamq55a`.
Design reference → [`DESIGN.md`](./DESIGN.md). Per-change detail → `git log`.

---

## Cumulative lessons (durable)

### APIs (pinned against live responses, not docs)
- **openFDA shortages search must be TOKENIZED** — `generic_name:furosemide`, NOT
  `generic_name:"furosemide"`. A quoted phrase returns `NOT_FOUND` for essentially everything.
- **openFDA statuses are an open set** — saw `Current`, `To Be Discontinued`; `Resolved` exists too.
  Don't hardcode a 2-value enum. Date field is `update_date` (MM/DD/YYYY), not `lastUpdated`.
- **openFDA records are NDC/package-level** — one drug → many rows (furosemide = 33). Aggregate by
  status. `NOT_FOUND` comes back as a JSON `error` object → treat as `no_record`, not an exception.
- **A drug maps to MULTIPLE ATC-4 classes** (atorvastatin → C10AA pure, C10BA/C10BX combinations).
  `classType` is the literal string `"ATC1-4"` for all levels → select ATC-4 by **classId length 5**.
- **RxClass members nest at** `drugMemberGroup.drugMember[].minConcept.{rxcui,name}`. Class members
  can include withdrawn drugs (e.g. cerivastatin) → surface, don't silently filter; rely on disclaimer.

### Runtime (playbook #11)
- **STDIO MCP servers must log to stderr** — never `print()` to stdout (corrupts JSON-RPC).
- **`uv`: let `uv run`/`uv sync` own the venv.** Do NOT also run `uv pip install -e .` — the two
  editable strategies collide and break `import` even though the `.pth` looks correct. Fix: `rm -rf
  .venv uv.lock && uv run …` (the clean clone-and-run path).
- **Bare `dict` returns produce no `outputSchema`.** Use `TypedDict`/Pydantic return types to get
  structured output (confirmed on `rx_health`).

---

## Sessions

### Session 1 — 2026-06-27 — Scoping, research, Phase 0 scaffold

**Done:**
- Scoped the project: portfolio-first, Claude-Desktop UX, model-decides class selection (full
  charter + decision log in ClickUp `86bamq55a`; plan approved via plan mode).
- Verified feasibility against **live** APIs — full chain proven on furosemide (→ bumetanide also
  Current shortage, torsemide clean). Corrected 5 draft assumptions (see lessons above).
- Deep market research (5 angles) — validated the cascade pain point; refined novelty (space is NOT
  empty: Certus + Orange-Book MCPs exist; whitespace = shortage→RxClass class-alts→cross-check).
- Verified Anthropic's current MCP/agent-tool guidance → adopted `outputSchema`, token-efficient
  responses, `next_step` hints, tool annotations, eval-driven quality.
- **Phase 0:** scaffolded `src/` repo, packaging (`uv`, entry point, py3.12), README, MIT license,
  and the `rx_health` tool. Smoke-tested: server loads, tool registers, annotations + `outputSchema`
  correct, runtime call works.

**Gotcha hit & resolved:** mixed `uv pip install -e .` with `uv run` → broke the editable import.
Clean rebuild fixed it; captured as a durable lesson.

**Open / next:**
- Phase 0 gate still needs **Travis to confirm it loads in Claude Desktop** (config in README) — I
  can't restart his Claude Desktop. MCP Inspector check can be run locally.
- Next: Phase 1 — `rx_check_shortage` (`openfda.py` client + tool + fixtures + tests).
