# Rx Shortage Alternative Finder (MCP)

A pharmacist gets the alert that metformin is on backorder, opens the drug class, and picks the next agent down the list. Two days later that order bounces too, because the alternative was on the FDA shortage list the whole time. That second shortage is the one nobody thinks to check, and it is the one this server catches.

Rx Shortage Alternative Finder is an MCP server that takes a drug in shortage, finds its same-class alternatives, and re-checks each one against live FDA data, so an LLM can answer "what else could work, and is any of it also short?" in a single pass.

*Status: v1, working and tested. Five read-only tools, 22 automated tests plus a live eval, validated end to end in Claude Desktop.*

## Try it

Connect the server (Quickstart is right below, about two minutes), then ask Claude:

> Furosemide is on backorder. What same-class options could we consider, and are any of those also short?

Watch it work the chain live. It normalizes the name through RxNorm, confirms the shortage in openFDA, pulls the loop-diuretic class from RxClass, then checks each sibling in turn. The payoff is the part no single database gives you: as of this writing it flags that bumetanide, the obvious switch, is also in shortage, while torsemide is not. Don't take that on faith. Swap in whatever drug is on your own backorder list and check it yourself.

## Quickstart

You need [`uv`](https://docs.astral.sh/uv/) and an MCP client, either Claude Desktop or Claude Code. No API key, no database, nothing else.

```bash
git clone https://github.com/Travis-Clement-Dev/rx-shortage-mcp.git
cd rx-shortage-mcp
uv run python -m rx_shortage_mcp
```

The first run builds the environment and pulls dependencies on its own. The server speaks MCP over stdio, so you normally launch it through a client rather than by hand.

### Connect it to Claude Desktop

Add this to `claude_desktop_config.json` (on macOS, `~/Library/Application Support/Claude/claude_desktop_config.json`), then restart Claude Desktop:

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

### An optional openFDA key

Everything runs keyless at roughly 240 requests a minute, plenty for interactive use. If you plan to hammer it, a free [openFDA key](https://open.fda.gov/apis/authentication/) raises the daily ceiling: copy `.env.example` to `.env` and set `OPENFDA_API_KEY`.

## How the chain works

Four read-only tools, called in sequence: normalize, classify, find siblings, re-check each. The orchestration lives in the model's reasoning, which is the reason this ships as an MCP server instead of a script.

1. **normalize_drug** turns a messy name, brand, or typo into an RxNorm RxCUI.
2. **get_drug_class** returns the drug's candidate ATC-4 pharmacologic classes.
3. **find_alternatives** lists the same-class siblings.
4. **check_shortage** returns the openFDA shortage status for the original and every alternative.

The fan-out in step four is the whole point. Listing same-class drugs is easy. Re-checking each one against the shortage list is the part that turns a list into a decision.

## What a full answer looks like

Ask about furosemide and the model returns a ranked, flagged shortlist:

| Same-class option (ATC C03CA) | FDA status | Presentations affected | Updated |
|---|---|---|---|
| furosemide (the one you asked about) | Current shortage | 33 | 06/25/2026 |
| bumetanide | Current shortage | 12 | 06/25/2026 |
| torsemide | No shortage reported | 0 | — |
| piretanide | No shortage reported | 0 | — |

The reflexive switch from furosemide is bumetanide, and bumetanide is short too. Torsemide is the same-class option that is not. That gap is the cascade, and surfacing it before you place the order is the entire job.

*(Live national data. Your numbers will differ as shortages change.)*

## Why this exists

FDA and ASHP tell you a drug is short. Orange Book and the vendor catalogs tell you who else makes the same molecule. Neither one tells you whether the different drug you would actually reach for is short as well. That blind spot, sitting in plain sight between three public data sources, is the reason this exists.

It is built for informatics pharmacists and clinical-data teams, the people who maintain formulary alternatives and build clinical decision support. They care how an answer was assembled as much as what it says, so every drug it names traces to a real RxNorm or RxClass identifier, and the reasoning runs in the open, one tool call at a time.

## What it will not do

This is decision support, not a substitution order, and the line matters. RxClass returns every member of a class, including drugs that are the wrong route, the wrong indication, contraindicated, or pulled from the market years ago. The server cannot tell which is which, so it does not pretend to.

Every alternatives response carries a disclaimer that says exactly that. Same pharmacologic class does not mean clinically interchangeable. Route, indication, dosing, and contraindications are never checked here, and the shortage data is national, not your local shelf. A licensed professional weighs the shortlist. The tool only makes sure the shortlist is honest about supply.

## Testing

```bash
uv run --extra dev pytest          # offline unit, safety, and protocol tests
uv run --extra dev pytest -m live  # the live eval: the full chain across 15 drugs
npx @modelcontextprotocol/inspector uv run python -m rx_shortage_mcp   # poke the tools by hand
```

The safety rule is enforced, not hoped for. A test fails the build if any tool ever frames its output as a substitution instruction or drops the disclaimer. If an import ever fails, the editable install has drifted; reset it with `rm -rf .venv uv.lock && uv sync`.

## Built on public data

RxNorm and RxClass come from the U.S. National Library of Medicine. Shortage data comes from the FDA's openFDA.

> This product uses publicly available data from the U.S. National Library of Medicine (NLM), National Institutes of Health, Department of Health and Human Services; NLM is not responsible for the product and does not endorse or recommend this or any other product.

openFDA shortage data is not intended for making decisions about medical care.

## License

[MIT](LICENSE), © 2026 Travis Clement.
