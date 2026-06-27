"""RxNorm / RxClass client (NLM RxNav).

Phase 2 implements normalize (RxNorm Prescribe). Phase 3 will add the RxClass
class + member lookups to this module.

Behavior pinned against live API responses (see docs/JOURNAL.md):
- Normalize primary: ``Prescribe/rxcui.json?name=<n>&search=2`` (exact-then-normalized;
  handles salt forms, abbreviations, brands) → ``idGroup.rxnormId[]`` (bare RxCUIs).
- Resolve a clean name for an RxCUI via ``/rxcui/<cui>/property.json?propName=RxNorm Name``.
- Fallback when primary is empty: ``Prescribe/approximateTerm.json`` →
  ``approximateGroup.candidate[]``. Scores are a small opaque scale (NOT 0-100), so we
  surface candidates for confirmation rather than hard-thresholding.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field

RXNAV_BASE = "https://rxnav.nlm.nih.gov/REST"
PRESCRIBE_RXCUI_URL = f"{RXNAV_BASE}/Prescribe/rxcui.json"
PRESCRIBE_APPROX_URL = f"{RXNAV_BASE}/Prescribe/approximateTerm.json"
_TIMEOUT = 15.0
_MAX_CANDIDATES = 5


class RxNavError(RuntimeError):
    """Raised on an RxNav transport/HTTP error."""


def property_url(rxcui: str) -> str:
    """URL to fetch concept properties (used for the RxNorm Name lookup)."""
    return f"{RXNAV_BASE}/rxcui/{rxcui}/property.json"


class NormalizeCandidate(BaseModel):
    rxcui: str = Field(description="RxNorm concept unique identifier.")
    name: str = Field(description="Candidate concept name.")
    score: float = Field(description="Raw RxNav approximate-match score (higher = closer; not a 0-100 confidence).")
    rank: int = Field(description="RxNav candidate rank (1 = best guess).")


class NormalizeResult(BaseModel):
    found: bool = Field(description="True if any match (exact or approximate) was found.")
    rxcui: str | None = Field(description="Best-match RxCUI, or null if no match.")
    name: str | None = Field(description="Resolved RxNorm name of the best match, or null.")
    match_type: str = Field(description="'exact' (confident), 'approximate' (confirm with user), or 'none'.")
    candidates: list[NormalizeCandidate] = Field(
        description="Ranked candidates for an approximate match (empty for exact). Present these for confirmation."
    )
    next_step: str = Field(description="Suggested next action for the agent.")


async def _get_json(client: httpx.AsyncClient, url: str, params: dict[str, Any]) -> dict:
    try:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:  # noqa: BLE001 - re-raise as a typed error with context
        raise RxNavError(f"RxNav request failed: {url} ({type(e).__name__})") from e


async def _rxnorm_name(client: httpx.AsyncClient, rxcui: str) -> str | None:
    data = await _get_json(client, property_url(rxcui), {"propName": "RxNorm Name"})
    concepts = data.get("propConceptGroup", {}).get("propConcept", [])
    return concepts[0]["propValue"] if concepts else None


async def normalize_drug(name: str) -> NormalizeResult:
    """Resolve a messy drug name/brand/typo to an RxCUI (+ clean name)."""
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # Primary: exact-then-normalized.
        primary = await _get_json(client, PRESCRIBE_RXCUI_URL, {"name": name, "search": 2})
        rxnorm_ids = primary.get("idGroup", {}).get("rxnormId", [])
        if rxnorm_ids:
            rxcui = rxnorm_ids[0]
            resolved = await _rxnorm_name(client, rxcui) or name
            return NormalizeResult(
                found=True,
                rxcui=rxcui,
                name=resolved,
                match_type="exact",
                candidates=[],
                next_step=f"Normalized to '{resolved}' (RxCUI {rxcui}). Call rx_get_drug_class with this name "
                f"to find its pharmacologic class.",
            )

        # Fallback: approximate match.
        approx = await _get_json(client, PRESCRIBE_APPROX_URL, {"term": name, "maxEntries": _MAX_CANDIDATES})
        raw = approx.get("approximateGroup", {}).get("candidate", []) or []

    candidates: list[NormalizeCandidate] = []
    seen: set[str] = set()
    for c in raw:
        cui = c.get("rxcui")
        if not cui or cui in seen:
            continue
        seen.add(cui)
        candidates.append(
            NormalizeCandidate(
                rxcui=cui,
                name=c.get("name", ""),
                score=float(c.get("score", 0) or 0),
                rank=int(c.get("rank", 0) or 0),
            )
        )

    if not candidates:
        return NormalizeResult(
            found=False,
            rxcui=None,
            name=None,
            match_type="none",
            candidates=[],
            next_step="No RxNorm match. Ask the user to check spelling or provide the generic ingredient name.",
        )

    top = candidates[0]
    return NormalizeResult(
        found=True,
        rxcui=top.rxcui,
        name=top.name,
        match_type="approximate",
        candidates=candidates,
        next_step="Approximate match only — these are best guesses. Confirm the intended drug with the user "
        "before proceeding, then call rx_get_drug_class with the confirmed name.",
    )
