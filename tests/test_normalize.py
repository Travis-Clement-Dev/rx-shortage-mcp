"""Tests for rx_normalize_drug / the RxNorm normalize client (offline via respx).

Locks: primary uses search=2; brand + generic exact matches resolve a clean name;
empty primary falls back to approximateTerm and surfaces candidates; total miss → none.
"""

import respx
from httpx import Response

from rx_shortage_mcp.rxnav import (
    PRESCRIBE_APPROX_URL,
    PRESCRIBE_RXCUI_URL,
    normalize_drug,
    property_url,
)


def _idgroup(ids):
    return {"idGroup": {"rxnormId": ids}} if ids else {"idGroup": {}}


def _prop(name):
    return {"propConceptGroup": {"propConcept": [{"propName": "RxNorm Name", "propValue": name}]}}


@respx.mock
async def test_exact_generic_match():
    respx.get(PRESCRIBE_RXCUI_URL).mock(return_value=Response(200, json=_idgroup(["83367"])))
    respx.get(property_url("83367")).mock(return_value=Response(200, json=_prop("atorvastatin")))
    r = await normalize_drug("atorvastatin")
    assert r.found is True
    assert r.match_type == "exact"
    assert r.rxcui == "83367"
    assert r.name == "atorvastatin"
    assert r.candidates == []


@respx.mock
async def test_exact_brand_match():
    respx.get(PRESCRIBE_RXCUI_URL).mock(return_value=Response(200, json=_idgroup(["153165"])))
    respx.get(property_url("153165")).mock(return_value=Response(200, json=_prop("Lipitor")))
    r = await normalize_drug("Lipitor")
    assert r.rxcui == "153165"
    assert r.name == "Lipitor"
    assert r.match_type == "exact"


@respx.mock
async def test_approximate_fallback_surfaces_candidates():
    respx.get(PRESCRIBE_RXCUI_URL).mock(return_value=Response(200, json=_idgroup([])))
    approx = {
        "approximateGroup": {
            "candidate": [
                {"rxcui": "83367", "name": "atorvastatin", "score": "8.55", "rank": "1"},
                {"rxcui": "1158285", "name": "atorvastatin Pill", "score": "8.48", "rank": "2"},
            ]
        }
    }
    respx.get(PRESCRIBE_APPROX_URL).mock(return_value=Response(200, json=approx))
    r = await normalize_drug("atorvastatn")
    assert r.match_type == "approximate"
    assert r.rxcui == "83367"  # top candidate
    assert len(r.candidates) == 2
    assert r.candidates[0].name == "atorvastatin"
    assert "confirm" in r.next_step.lower()


@respx.mock
async def test_no_match():
    respx.get(PRESCRIBE_RXCUI_URL).mock(return_value=Response(200, json=_idgroup([])))
    respx.get(PRESCRIBE_APPROX_URL).mock(return_value=Response(200, json={"approximateGroup": {}}))
    r = await normalize_drug("zzzznotadrug")
    assert r.found is False
    assert r.match_type == "none"
    assert r.rxcui is None


@respx.mock
async def test_primary_uses_search_2():
    route = respx.get(PRESCRIBE_RXCUI_URL).mock(return_value=Response(200, json=_idgroup(["83367"])))
    respx.get(property_url("83367")).mock(return_value=Response(200, json=_prop("atorvastatin")))
    await normalize_drug("atorvastatin")
    assert "search=2" in str(route.calls[0].request.url)
