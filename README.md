# Rx Shortage Alternative Finder (MCP)

> An MCP server that lets an LLM answer a pharmacist's question:
> **"Drug X is on backorder — what could be considered instead, and are any of those *also* short?"**

When a drug goes into shortage, the obvious therapeutic alternative is often **also short** — a
documented "cascading shortage" (e.g. cisplatin → carboplatin, where the alternative became *more*
scarce than the original). The data to check this is public, but **no single tool stitches it
together**. This server does, in one LLM reasoning pass.

> ⚠️ **Decision-support, not a substitution authority.** "Same pharmacologic class" ≠ "clinically
> interchangeable." This tool surfaces *candidates for a licensed professional to evaluate*. It does
> **not** check route, indication, contraindications, or therapeutic equivalence. See [Safety](#safety).

> ✅ **Status:** v1 — all four tools live, orchestrated, and safety-gated; verified live in Claude
> Desktop. 15/15 on the chain-success eval.

---

## Who it's for & what makes it different

Built for **informatics pharmacists** and clinical-data teams who operationalize shortage
response — people who care about *how the data is stitched together*, not just the answer. Every
suggestion is grounded in real RxNorm/RxClass identifiers (no model-invented drugs) and framed as
**clinical decision support with transparent reasoning** — a human stays in the loop; the server
makes no substitution decision.

**The gap it fills:** FDA/ASHP tell you a drug is short. Equivalence tools (Orange Book, vendor
catalogs) tell you who else makes the *same molecule*. Neither tells you whether the *different drug
you'd actually reach for* — a same-class alternative — is **also** in shortage. This stitches FDA
shortage status + RxNorm/RxClass class alternatives + a per-alternative re-check into one LLM pass.

---

## What it does

```
drug name ──▶ rx_normalize_drug ──▶ RxCUI + clean name
                                        │
                                        ▼
                              rx_get_drug_class ──▶ candidate ATC-4 classes
                                        │
                                        ▼
                            rx_find_alternatives ──▶ sibling drugs in the class
                                        │
                   ┌────────────────────┴───────────────────┐
                   ▼  (LLM loops over each sibling + original)
             rx_check_shortage ──▶ Current / Resolved / no record
                   │
                   ▼
        ranked candidates, each flagged if ALSO short   (the LLM synthesizes)
```

The fan-out loop is **the model's reasoning**, not a single tool call — that's why this is an MCP
server, not a script.

## The four tools

| Tool | Purpose | Source |
|------|---------|--------|
| `rx_normalize_drug` | Messy name / brand / typo → RxCUI + ingredient | RxNorm (Prescribe) |
| `rx_get_drug_class` | Drug → candidate ATC-4 pharmacologic classes | RxClass |
| `rx_find_alternatives` | Class → sibling drugs (carries safety disclaimer) | RxClass |
| `rx_check_shortage` | Drug → current shortage status | openFDA Drug Shortages |

All four are **read-only**. No API key required (see below).

## Example

Ask your MCP client: *"Furosemide is on backorder — what could be considered instead, and are any of
those also short?"* The model chains the four tools and synthesizes a ranked, shortage-flagged
shortlist:

| Same-class option (ATC C03CA) | FDA status | Presentations affected | Updated |
|---|---|---|---|
| furosemide (original) | Current shortage | 33 | 06/25/2026 |
| bumetanide | Current shortage | 12 | 06/25/2026 |
| torsemide | No shortage reported | 0 | — |
| piretanide | No shortage reported | 0 | — |

**The cascade insight:** both first-line loop diuretics — furosemide *and* its usual substitute
bumetanide — are in current FDA shortage; torsemide is the same-class option with no shortage
reported. *Candidates for a licensed professional to evaluate — not a substitution instruction;
status ≠ availability, and class membership ≠ clinical interchangeability.*

*(Live national data — your results will reflect current shortage status, which changes over time.)*

> 🎥 Demo video: _coming soon._

## Requirements

- [`uv`](https://docs.astral.sh/uv/) (recommended) — handles Python + deps automatically
- Python ≥ 3.10 (uv fetches 3.12 for you if absent)
- An MCP client — **Claude Desktop** or **Claude Code**

## Install & run

```bash
git clone https://github.com/Travis-Clement-Dev/rx-shortage-mcp.git
cd rx-shortage-mcp
uv run python -m rx_shortage_mcp   # first run auto-creates the venv + installs deps
```

The server speaks MCP over stdio; you normally launch it *through* an MCP client rather than by hand.

### Claude Desktop

Add to `claude_desktop_config.json`
(macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "rx-shortage": {
      "command": "uv",
      "args": ["--directory", "/ABSOLUTE/PATH/TO/rx-shortage-mcp", "run", "python", "-m", "rx_shortage_mcp"]
    }
  }
}
```

Restart Claude Desktop, then ask: *"Furosemide is on backorder — what could I consider instead,
and are any of those also short?"*

### Optional: openFDA API key

The server runs **fully keyless** (~240 req/min, ~1000 req/day per IP). A free
[openFDA key](https://open.fda.gov/apis/authentication/) only raises the daily ceiling. To use one,
copy `.env.example` to `.env` and set `OPENFDA_API_KEY`.

## Testing

```bash
uv run --extra dev pytest        # offline unit + safety-gate + MCP-protocol tests (deterministic)
uv run --extra dev pytest -m live # live eval: full chain over 15 drugs, asserts >=90% chain success
npx @modelcontextprotocol/inspector uv run python -m rx_shortage_mcp   # interactive tool testing
```

The safety gate (`tests/test_safety_gate.py`) fails the build if any tool ever frames output as a
substitution instruction or drops the disclaimer.

> **Troubleshooting:** if `import rx_shortage_mcp` ever fails, the editable install drifted —
> reset with `rm -rf .venv uv.lock && uv sync`. Let `uv` own the venv; don't mix in `uv pip install -e .`.

## Safety

`rx_find_alternatives` returns **every** member of a pharmacologic class — some will be the wrong
route, wrong indication, contraindicated, or withdrawn from market. The server **cannot** encode
clinical judgment. Every alternatives response carries a disclaimer; output is framed as "candidate
alternatives to consider," never "substitute with X." A licensed professional must evaluate every
candidate. National-level shortage data only — no local/regional stock.

## Attribution

This product uses publicly available data from the U.S. National Library of Medicine (NLM), National
Institutes of Health, Department of Health and Human Services; NLM is not responsible for the product
and does not endorse or recommend this or any other product.

Shortage data from the U.S. Food & Drug Administration (openFDA). openFDA data is **not** for making
decisions regarding medical care.

## License

[MIT](LICENSE) © 2026 Travis Clement
