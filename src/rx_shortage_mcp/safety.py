"""Safety constants — the single source of truth for decision-support framing.

`rx_find_alternatives` MUST attach DISCLAIMER to every response. The Phase 4
safety-gate test enforces that this string is present and that tool docstrings
never frame output as a substitution instruction.
"""

# Kept as one constant so the disclaimer can never drift between tools.
DISCLAIMER = (
    "These are candidate drugs in the same pharmacologic class, provided for evaluation by a "
    "licensed professional — NOT a recommendation to substitute. Class membership does not imply "
    "clinical interchangeability: route, indication, contraindications, dosing equivalence, and "
    "therapeutic equivalence are NOT checked here, and some members may be withdrawn, combination "
    "products, or otherwise inappropriate. Shortage data is national-level only and does not reflect "
    "local stock. Confirm every choice against current clinical references and local availability."
)

# Phrases that must never appear in tool output/descriptions (checked by the safety gate).
FORBIDDEN_SUBSTITUTION_PHRASES = ("substitute with", "replace with", "use instead of")
