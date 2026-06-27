"""The safety gate — turns the §6 safety constraint into a mechanical, blocking check (playbook #12).

Asserts:
- no tool description (LLM-facing docstring) contains substitution-instruction language;
- the server instructions carry the decision-support framing + the grounding rule;
- the disclaimer content is intact;
- rx_find_alternatives ALWAYS attaches the disclaimer, even for an empty class.
"""

import respx
from httpx import Response

from rx_shortage_mcp.rxnav import RXCLASS_MEMBERS_URL, find_alternatives
from rx_shortage_mcp.safety import DISCLAIMER, FORBIDDEN_SUBSTITUTION_PHRASES
from rx_shortage_mcp.server import INSTRUCTIONS, mcp


async def test_no_substitution_language_in_tool_descriptions():
    tools = await mcp.list_tools()
    assert len(tools) == 5
    for t in tools:
        desc = (t.description or "").lower()
        for phrase in FORBIDDEN_SUBSTITUTION_PHRASES:
            assert phrase not in desc, f"tool '{t.name}' description contains forbidden phrase '{phrase}'"


def test_server_instructions_have_safety_and_grounding_framing():
    text = INSTRUCTIONS.lower()
    assert "decision support" in text  # framed as support, not authority
    assert "licensed professional" in text
    # grounding rule: never invent a drug from model knowledge
    assert "invent" in text or "only" in text
    for phrase in FORBIDDEN_SUBSTITUTION_PHRASES:
        assert phrase not in text, f"server instructions contain forbidden phrase '{phrase}'"


def test_disclaimer_content_intact():
    d = DISCLAIMER.lower()
    assert "not a recommendation to substitute" in d
    assert "licensed professional" in d
    assert "interchangeab" in d  # 'interchangeability'


@respx.mock
async def test_find_alternatives_always_carries_disclaimer_even_when_empty():
    respx.get(RXCLASS_MEMBERS_URL).mock(return_value=Response(200, json={"drugMemberGroup": {}}))
    res = await find_alternatives("C99ZZ")
    assert res.count == 0
    assert res.disclaimer == DISCLAIMER  # gate: disclaimer present regardless of members
