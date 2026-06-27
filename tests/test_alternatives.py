"""Tests for rx_find_alternatives (offline via respx).

Locks correction #5 (members nest at drugMember[].minConcept), combination-member
flagging, output capping, and the ALWAYS-PRESENT safety disclaimer (the gate).
"""

import respx
from httpx import Response

from rx_shortage_mcp.rxnav import RXCLASS_MEMBERS_URL, find_alternatives
from rx_shortage_mcp.safety import DISCLAIMER


def _members(*names):
    return {
        "drugMemberGroup": {
            "drugMember": [{"minConcept": {"rxcui": str(1000 + i), "name": n}} for i, n in enumerate(names)]
        }
    }


@respx.mock
async def test_parses_members_and_attaches_disclaimer():
    respx.get(RXCLASS_MEMBERS_URL).mock(
        return_value=Response(200, json=_members("bumetanide", "torsemide", "furosemide"))
    )
    res = await find_alternatives("C03CA")
    names = [m.name for m in res.members]
    assert names == ["bumetanide", "torsemide", "furosemide"]
    assert res.count == 3
    assert res.capped is False
    assert res.disclaimer == DISCLAIMER  # safety gate: always present


@respx.mock
async def test_flags_combination_members():
    respx.get(RXCLASS_MEMBERS_URL).mock(
        return_value=Response(200, json=_members("furosemide / potassium", "bumetanide"))
    )
    res = await find_alternatives("C03CB")
    combo = [m for m in res.members if m.name == "furosemide / potassium"][0]
    plain = [m for m in res.members if m.name == "bumetanide"][0]
    assert combo.is_combination is True
    assert plain.is_combination is False


@respx.mock
async def test_caps_large_classes():
    many = _members(*[f"drug{i}" for i in range(40)])
    respx.get(RXCLASS_MEMBERS_URL).mock(return_value=Response(200, json=many))
    res = await find_alternatives("C10AA")
    assert res.capped is True
    assert res.count == 30  # capped to the max
    assert res.disclaimer == DISCLAIMER
