"""Tests for rx_get_drug_class (offline via respx).

Locks correction #4: a drug maps to MULTIPLE ATC-4 classes; select ATC-4 by classId
length == 5 (classType is the literal 'ATC1-4' for every level); flag combination
classes; pure (single-ingredient) classes sort first.
"""

import respx
from httpx import Response

from rx_shortage_mcp.rxnav import RXCLASS_BYDRUG_URL, get_drug_class


def _cls(class_id, class_name):
    return {"rxclassMinConceptItem": {"classId": class_id, "className": class_name, "classType": "ATC1-4"}}


FUROSEMIDE = {
    "rxclassDrugInfoList": {
        "rxclassDrugInfo": [
            _cls("C03CA", "Sulfonamides, plain"),
            _cls("C03CB", "Sulfonamides and potassium in combination"),
            _cls("C03CA", "Sulfonamides, plain"),  # duplicate (real data repeats per relation)
            _cls("C03", "HIGH-CEILING DIURETICS"),  # ATC-3 (len 3) → must be filtered out
        ]
    }
}


@respx.mock
async def test_returns_all_atc4_with_flags_pure_first():
    respx.get(RXCLASS_BYDRUG_URL).mock(return_value=Response(200, json=FUROSEMIDE))
    res = await get_drug_class("furosemide")
    assert res.count == 2  # C03CA + C03CB, deduped; C03 (ATC-3) excluded
    # Pure class sorts first
    assert res.classes[0].class_id == "C03CA"
    assert res.classes[0].is_combination is False
    combo = [c for c in res.classes if c.class_id == "C03CB"][0]
    assert combo.is_combination is True


@respx.mock
async def test_no_atc4_class_returns_empty():
    respx.get(RXCLASS_BYDRUG_URL).mock(
        return_value=Response(200, json={"rxclassDrugInfoList": {"rxclassDrugInfo": []}})
    )
    res = await get_drug_class("mysterydrug")
    assert res.count == 0
    assert res.classes == []
    assert "combination" in res.next_step.lower() or "no" in res.next_step.lower()


@respx.mock
async def test_uses_atc_relasource():
    route = respx.get(RXCLASS_BYDRUG_URL).mock(return_value=Response(200, json=FUROSEMIDE))
    await get_drug_class("furosemide")
    assert "relaSource=ATC" in str(route.calls[0].request.url)
