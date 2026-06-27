"""Tests for the openFDA shortage client (offline, via respx-mocked HTTP).

These lock the live-probe corrections (see docs/JOURNAL.md):
- tokenized search `generic_name:<name>` (NEVER a quoted phrase)
- NDC/package-level records aggregated by status
- NOT_FOUND (404 JSON error object) → 'no_record', not an exception
- statuses are an open set; date field is `update_date`
"""

import respx
from httpx import Response

from rx_shortage_mcp.openfda import OPENFDA_SHORTAGES_URL, check_shortage

CURRENT_PAYLOAD = {
    "meta": {"results": {"total": 3}},
    "results": [
        {
            "generic_name": "Furosemide Injection",
            "status": "Current",
            "update_date": "06/25/2026",
            "therapeutic_category": ["Cardiovascular"],
            "shortage_reason": "Demand increase for the drug",
            "dosage_form": "Injection",
        },
        {
            "generic_name": "Furosemide Tablet",
            "status": "To Be Discontinued",
            "update_date": "01/10/2026",
            "therapeutic_category": ["Cardiovascular"],
            "shortage_reason": "Other",
            "dosage_form": "Tablet",
        },
        {
            "generic_name": "Furosemide Injection",
            "status": "Current",
            "update_date": "05/01/2026",
            "therapeutic_category": ["Cardiovascular"],
            "shortage_reason": "Demand increase for the drug",
            "dosage_form": "Injection",
        },
    ],
}

RESOLVED_PAYLOAD = {
    "meta": {"results": {"total": 2}},
    "results": [
        {"generic_name": "Olddrug", "status": "Resolved", "update_date": "02/02/2025"},
        {"generic_name": "Olddrug", "status": "Resolved", "update_date": "03/03/2025"},
    ],
}

NOT_FOUND = {"error": {"code": "NOT_FOUND", "message": "No matches found!"}}


@respx.mock
async def test_current_shortage_aggregates_by_status():
    respx.get(OPENFDA_SHORTAGES_URL).mock(return_value=Response(200, json=CURRENT_PAYLOAD))
    res = await check_shortage("furosemide")
    assert res.in_shortage is True
    assert res.overall_status == "Current"
    assert res.record_count == 3
    counts = {s.status: s.count for s in res.statuses}
    assert counts == {"Current": 2, "To Be Discontinued": 1}
    assert res.last_updated == "06/25/2026"  # most recent across records
    assert res.therapeutic_categories == ["Cardiovascular"]


@respx.mock
async def test_not_found_maps_to_no_record():
    respx.get(OPENFDA_SHORTAGES_URL).mock(return_value=Response(404, json=NOT_FOUND))
    res = await check_shortage("atorvastatin")
    assert res.overall_status == "no_record"
    assert res.in_shortage is False
    assert res.record_count == 0


@respx.mock
async def test_resolved_only_is_not_active_shortage():
    respx.get(OPENFDA_SHORTAGES_URL).mock(return_value=Response(200, json=RESOLVED_PAYLOAD))
    res = await check_shortage("olddrug")
    assert res.overall_status == "Resolved"
    assert res.in_shortage is False


@respx.mock
async def test_search_is_tokenized_not_quoted():
    route = respx.get(OPENFDA_SHORTAGES_URL).mock(return_value=Response(200, json=CURRENT_PAYLOAD))
    await check_shortage("furosemide")
    url = str(route.calls[0].request.url)
    assert "generic_name" in url and "furosemide" in url
    assert "%22" not in url  # no double-quotes → tokenized, not a phrase (correction #1)


@respx.mock
async def test_api_key_added_when_env_set(monkeypatch):
    monkeypatch.setenv("OPENFDA_API_KEY", "testkey123")
    route = respx.get(OPENFDA_SHORTAGES_URL).mock(return_value=Response(200, json=CURRENT_PAYLOAD))
    await check_shortage("furosemide")
    assert "api_key=testkey123" in str(route.calls[0].request.url)
