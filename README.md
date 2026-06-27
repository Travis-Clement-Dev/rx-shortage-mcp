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

> 🚧 **Status:** active build. Phase 0 (scaffold + health check) complete. Tools land across phases 1–5.

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

Restart Claude Desktop, then ask: *"Atorvastatin is on backorder — what could I consider instead,
and are any of those also short?"*

### Optional: openFDA API key

The server runs **fully keyless** (~240 req/min, ~1000 req/day per IP). A free
[openFDA key](https://open.fda.gov/apis/authentication/) only raises the daily ceiling. To use one,
copy `.env.example` to `.env` and set `OPENFDA_API_KEY`.

## Testing

```bash
uv run pytest                 # unit tests (offline, deterministic)
uv run pytest -m "not live"   # skip tests that hit live APIs
npx @modelcontextprotocol/inspector uv run python -m rx_shortage_mcp   # interactive tool testing
```

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
