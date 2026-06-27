# Design — Rx Shortage Alternative Finder (MCP)

> The repo's self-documenting design reference. Milestone status lives in ClickUp `86bamq55a`;
> chronological narrative + lessons live in [`JOURNAL.md`](./JOURNAL.md); per-change detail is in
> `git log`. This file is the "what & why" of the architecture.

## Status

| | |
|---|---|
| **Phase** | 0 — scaffold + health tool ✅ (mechanism verified) |
| **Next** | Phase 1 — `rx_check_shortage` |
| **Stack** | Python ≥3.10, `mcp` SDK (FastMCP), `httpx`; `uv`-managed; `src/` layout |

## Context (why this exists)

When a drug is on shortage, the obvious same-class therapeutic alternative is often **also short** —
a documented "cascading shortage" (cisplatin → carboplatin, where the alternative became *more*
scarce than the original). The data to check this is public but **no single tool stitches it
together**: FDA/ASHP report shortages, none suggest class-level alternatives at the point of need,
and none re-check whether those alternatives are themselves short. This server closes that gap in
one LLM reasoning pass.

**Honest framing:** the pain is *fragmentation + manual labor* (the data is accessible but scattered;
the cross-check is manual), **not** "pharmacists can't find this out." Value = collapsing a
multi-source manual hunt into one pass and proactively flagging the cascade.

## Architecture

The four tools are **deterministic, read-only data-fetchers**. ALL reasoning — class selection,
ranking, the cascade narrative, safety framing — lives in the **model** (Claude Desktop / Claude
Code). That separation is why this is an MCP server, not a script.

```
drug name → rx_normalize_drug → RxCUI
                                  → rx_get_drug_class → candidate ATC-4 classes
                                       → rx_find_alternatives → sibling drugs
                                            → (LLM loops) rx_check_shortage per sibling + original
                                                 → LLM synthesizes ranked, shortage-flagged shortlist
```

## Tool contracts (live-probe corrections baked in)

All tools: `readOnlyHint=true`, `idempotentHint=true`, `openWorldHint=true`; Pydantic inputs;
typed returns (→ `outputSchema`); token-efficient (capped/aggregated, no raw API JSON); each result
carries a `next_step` hint.

1. **`rx_normalize_drug(name)`** → RxCUI. Primary `Prescribe/rxcui?search=2`; fallback
   `Prescribe/approximateTerm` with a confidence threshold (return candidates if low).
2. **`rx_get_drug_class(drug_name)`** → ALL candidate ATC-4 classes. Select ATC-4 by **classId
   length == 5** (`classType` is the literal `"ATC1-4"` for every level — cannot filter on it). Flag
   `is_combination`. The model picks the class.
3. **`rx_find_alternatives(classId)`** → siblings. Members nest at
   `drugMemberGroup.drugMember[].minConcept`. Flag combination members; cap (~30). **Always carries
   the safety disclaimer.**
4. **`rx_check_shortage(drug_name)`** → openFDA status. **Tokenized** search (no quotes). Statuses
   are an open set (`Current`, `To Be Discontinued`, `Resolved`, …) — pass through. Records are
   NDC-level → **aggregate by status**. `NOT_FOUND` → `no_record` (not an error).

## Safety model (non-negotiable)

"Same pharmacologic class" ≠ "clinically interchangeable." This is **decision-support, not a
substitution authority.** Enforced: (1) `rx_find_alternatives` always attaches a disclaimer
(test-gated); (2) docstrings frame "candidate alternatives to consider," never "substitute with X";
(3) ranking by class proximity + shortage status only; (4) alternatives are grounded **only** in real
RxClass/RxNorm CUIs — never model-invented.

## Key decisions

| Decision | Why |
|---|---|
| Portfolio-first scope | Demo/video/clone-and-run for peers, not a production clinical tool. |
| Headline UX = Claude Desktop/Code | The LLM orchestrates; tools stay dumb. |
| Model decides class selection | On-brand; honest about ambiguity; avoids a brittle heuristic a probe disproved. |
| Tool names `rx_`-prefixed | Avoid collisions with other drug MCP servers (e.g. Certus). |
| Keyless-first (openFDA key optional) | Zero-signup clone-and-run. |
| `uv`-managed env (no manual `pip install -e`) | Mixing the two corrupts the editable install (see JOURNAL). |
| Launch via `uv run python -m rx_shortage_mcp` (+ `__main__.py`) | Official robust pattern; `uv run` re-syncs each launch. Console script kept for PyPI installs. |
| `TypedDict`/Pydantic typed returns | Generate `outputSchema` per MCP 2025-06-18 + Anthropic guidance. |

## Build sequence

0. Scaffold + health tool ✅  →  1. `rx_check_shortage`  →  2. `rx_normalize_drug`
→  3. `rx_get_drug_class` + `rx_find_alternatives`  →  4. orchestration docstrings + safety gate
→  5. eval suite (~15 scenarios, ≥90%) + live e2e + demo + README polish.

Each phase: verified before the next begins; committed atomically.

## Verification

`uv run --extra dev pytest` (offline; incl. `test_mcp_protocol.py` — real MCP client over stdio) ·
MCP Inspector (`npx @modelcontextprotocol/inspector uv run python -m rx_shortage_mcp`) · live e2e on
furosemide (expect bumetanide *also short*, torsemide *clean*) · cold-clone ≤10 min.
