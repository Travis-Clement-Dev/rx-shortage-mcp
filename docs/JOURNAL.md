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
  Current shortage, torsemide not listed). Corrected 5 draft assumptions (see lessons above).
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

### Integration checkpoint — 2026-06-27 — live MCP smoke test in Claude Desktop

Added the server to Claude Desktop/Code and called all 3 tools through the **real MCP connection**
(not pytest): `rx_health` ✅; `rx_check_shortage("furosemide")` → Current, 33 records (30 Current +
3 To Be Discontinued), 5 distinct reasons ✅; `rx_normalize_drug("HCTZ")` → hydrochlorothiazide
(exact) ✅. Structured output parsed cleanly; `next_step` hints already provide soft orchestration
before the Phase 4 docstrings exist. **Phase 0's "loads in Claude Desktop" gate is now CLOSED.**

### Session 4 — 2026-06-27 — Phase 3: `rx_get_drug_class` + `rx_find_alternatives`

**Probes first:** confirmed `byDrugName` accepts a BRAND (`Lipitor`→C10AA — no pre-resolution needed);
furosemide's ATC-4 set is `C03CA "Sulfonamides, plain"` (pure loop diuretics) vs `C03CB "...in
combination"`; `is_combination = "combination" in className` separates them cleanly. C03CA members =
bumetanide, piretanide, torsemide, furosemide.

**Done (TDD red→green):**
- `safety.py` — single-source `DISCLAIMER` + `FORBIDDEN_SUBSTITUTION_PHRASES` (for the Phase 4 gate).
- `rxnav.py` `get_drug_class`: returns ALL ATC-4 classes (classId len 5), `is_combination` flagged,
  single-ingredient first — the model picks (correction #4, surfaced not hidden).
- `rxnav.py` `find_alternatives`: members from `drugMember[].minConcept` (correction #5), combination
  members flagged, capped at 30, **disclaimer always attached**.
- Both tools wired in; 6 new tests. Full suite: **17 passed**, 5 tools registered w/ outputSchema.

**Live evidence:** furosemide → [C03CA pure, C03CB combo] → C03CA members [bumetanide, piretanide,
torsemide, furosemide]. The complete data chain (normalize→class→alternatives→shortage) now exists.

**Next:** Phase 4 — orchestration docstrings tying the chain together + the test-enforced safety gate.

### Session 5 — 2026-06-27 — Phase 4: orchestration + safety gate

**Done (TDD red→green):**
- Server-level `INSTRUCTIONS` (passed to `FastMCP(instructions=...)`) — the canonical place for the
  full workflow (normalize→shortage→class→alternatives→cascade re-check→synthesize) + the safety &
  grounding framing (decision-support only; never invent a drug; surface the disclaimer). Layered
  above the per-tool `next_step` hints.
- `tests/test_safety_gate.py` — mechanical gate: no substitution-instruction phrases in any tool
  description OR the instructions; disclaimer content intact; `find_alternatives` always carries the
  disclaimer (even for an empty class). Full suite: **21 passed**.

**Why server instructions (not just docstrings):** instructions are surfaced once to the client and
guide the whole session; docstrings guide individual tool use. Both layers reinforce the chain.

**Next:** Phase 5 — eval suite (~15 scenarios, ≥90%) + live full-chain cascade test + demo video +
README polish. (Requires a Claude Desktop restart to load all 5 tools + instructions for the live run.)

### Session 6 — 2026-06-27 — Phase 5a: eval suite (the retest) + decisions

**Decisions recorded** (ClickUp decision log + comment): target audience = **informatics pharmacists**
(data/CDS-focused); FDA-aligned terminology standard (no "clean"); v1 visual = Option A data-rich
(LLM-rendered, server stays data-only); never assert market status; **repo made PUBLIC**
(github.com/Travis-Clement-Dev/rx-shortage-mcp, passed pre-push scan).

**Done:**
- `tests/eval_cases.py` (15 diverse drugs incl. brand + abbreviation) + `tests/test_evals.py` — runs
  the full chain per case, scores STRUCTURAL success (normalize + pure ATC-4 class w/ ≥2 members +
  disclaimer + valid shortage status). Expectations are stable, not drifting live status.
- pyproject `addopts = -m 'not live'` → default suite stays offline/deterministic; eval runs with
  `-m live`.
- **Live eval result: 15/15 = 100%** (≥90% gate cleared). Default suite: 21 passed, 1 deselected.

**Next:** Phase 5b — data-rich status visual (Option A); 5c — README polish (CDS framing, NLM
attribution, diagram); then finalize + demo.

### Session 6 (cont.) — Phase 5b–c → v1 FEATURE-COMPLETE

- **5b:** produced the data-rich status visual (Option A) — FDA status (color) × breadth (presentations
  affected); LLM-rendered from live tool data, server stays data-only. FDA-aligned labels; dropped
  "clean" and the unverified market-status claim.
- **5c:** polished README — informatics-audience + CDS framing, the differentiator vs Orange-Book /
  vendor tools, a concrete furosemide cascade Example + data table, surfaced the eval + safety gate,
  real-shortage example query.
- **v1 feature-complete:** 5 tools + orchestration + test-enforced safety gate; 21 offline tests +
  live eval 15/15; public repo (17 commits). **Remaining:** Travis records the demo video → mark complete.

### Session 7 — 2026-06-27 — Blind test #1 + record_count fix

**Blind test #1** (methylphenidate, run in a fresh chat; criteria pre-registered in ClickUp): **PASS
(6/6, 0 red flags).** Proactive, uncued cascade + safety framing held; the model reasoned
"active-ingredient shortage ⇒ class-wide" and flagged the modafinil "same class ≠ interchangeable"
trap on live data; cross-class non-stimulants were named only as a disclosed, *unverified* limitation
(grounding discipline held under pressure).

**Finding → fix (playbook #23 — test as the user hits it):** the blind test exposed that
`record_count` was floored at our `limit=50` (amphetamine family all returned exactly 50). A real
correctness bug our offline fixtures (all <50 records) structurally could not catch. Fix: `limit=1000`
(openFDA max) to fetch all NDC records, surface openFDA `meta.results.total` as `record_count`, add a
`capped` flag. Verified live: lisdexamfetamine **108** (was 50), amphetamine/dextroamphetamine 73;
per-status counts now true. Regression test added; 22 offline tests + eval 15/15.
