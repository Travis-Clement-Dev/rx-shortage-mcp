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
- **`uv`: let `uv run`/`uv sync` own the venv.** Do NOT also run `uv pip install -e .` or lean on
  `--no-sync` — that corrupts the editable install: `src/` drops off `sys.path`, the console script
  vanishes from `.venv/bin`, and `import`/`python -m` both fail. **Recovery: `rm -rf .venv uv.lock
  && uv sync`.** A clean sync restores everything (import ✅, console script ✅, `src` on path ✅).
  Claude Desktop's `uv run` re-syncs on every launch, so it self-heals.
- **Launch via `python -m rx_shortage_mcp`** (needs `__main__.py`) — the official pattern (cf.
  `mcp-server-git`). The `[project.scripts]` console script is kept for proper/PyPI installs.
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

**RCA episode (systematic-debugging skill):** the MCP-over-stdio launch failed ("Failed to spawn
rx-shortage-mcp" / "No module named rx_shortage_mcp"). Investigated boundaries instead of guessing:
console script missing → entry_points.txt present → both direct + uv-run import failing → `src` not
on `sys.path`. **Root cause: self-inflicted editable-install corruption** from mixing `uv pip
install -e .`/`--no-sync` with uv's managed workflow. A clean `uv sync` fixed all of it; `src/`
layout was never the problem. Added `__main__.py` + a permanent `tests/test_mcp_protocol.py`
(spawns the server, drives it via a real MCP client) — **passing**.

**Phase 0 status:** ✅ code-complete + verified (protocol test green). Remaining gate: **Travis to
confirm it loads in his Claude Desktop** (config in README) — I can't restart his app.

**Next:** Phase 1 — `rx_check_shortage` (`openfda.py` client + tool + fixtures + tests).

### Session 2 — 2026-06-27 — Phase 1: `rx_check_shortage`

**Done (TDD: red → green):**
- `openfda.py` — tokenized `generic_name` search; NOT_FOUND→`no_record`; NDC-level records
  aggregated by status (severity-ordered); optional `OPENFDA_API_KEY`; Pydantic `ShortageResult`
  (token-efficient summary, not raw records) → `outputSchema`.
- `rx_check_shortage` tool wired in (Annotated input → flat inputSchema; read-only/idempotent/openWorld).
- `tests/test_shortage.py` — 5 tests locking the corrections (tokenized search, aggregation,
  NOT_FOUND, resolved-not-active, api_key). Full suite: **6 passed**.

**Live evidence:** furosemide → in_shortage=True, Current, 33 records (30 Current + 3 To Be
Discontinued), updated 06/25/2026. atorvastatin → no_record. Confirms tokenized search + 200/404
handling against the real API.

**Next:** Phase 2 — `rx_normalize_drug` (RxNorm Prescribe + approximateTerm fallback).

### Session 3 — 2026-06-27 — Phase 2: `rx_normalize_drug`

**Probes first (verify-don't-assert):** confirmed brand resolution (`Lipitor`→153165) and the
name-lookup path (`/rxcui/<cui>/property.json?propName=RxNorm Name`). Found approximate scores are a
small opaque scale (~8.5 for a 1-char typo) → **don't hard-threshold**; surface candidates for
confirmation instead (safer, honest).

**Done (TDD red→green):**
- `rxnav.py` `normalize_drug`: primary `Prescribe/rxcui.json?search=2` → name via property endpoint;
  empty → `approximateTerm` candidates. Pydantic `NormalizeResult` (match_type exact/approximate/none,
  ranked candidates, next_step) → `outputSchema`.
- `rx_normalize_drug` tool wired in; docstring instructs the model to CONFIRM approximate matches.
- `tests/test_normalize.py` — 5 tests (exact generic, exact brand, approximate fallback, no-match,
  search=2). Full suite: **11 passed**.

**Live evidence:** Lipitor→exact (brand); HCTZ→`hydrochlorothiazide` (abbreviation expansion!);
`atorvastatn`→approximate w/ candidates; gibberish→none.

**Next:** Phase 3 — `rx_get_drug_class` + `rx_find_alternatives` (RxClass).
