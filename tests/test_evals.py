"""Live evaluation: run the full chain over CASES and assert ≥90% structural success.

Marked `live` — excluded from the default offline suite. Run with:
    uv run --extra dev pytest -m live -s
"""

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from eval_cases import CASES  # noqa: E402

from rx_shortage_mcp.openfda import check_shortage  # noqa: E402
from rx_shortage_mcp.rxnav import find_alternatives, get_drug_class, normalize_drug  # noqa: E402

_VALID_STATUS = {"Current", "To Be Discontinued", "Resolved", "no_record"}


async def _score_case(user_input: str, expected_substr: str) -> list[str]:
    """Run the full chain for one drug; return a list of failure reasons (empty = pass)."""
    reasons: list[str] = []

    norm = await normalize_drug(user_input)
    if not (norm.found and norm.name and expected_substr.lower() in norm.name.lower()):
        reasons.append(f"normalize→{norm.name!r}")

    cls = await get_drug_class(norm.name or user_input)
    pure = [c for c in cls.classes if not c.is_combination]
    if not pure:
        reasons.append("no pure ATC-4 class")
    else:
        alts = await find_alternatives(pure[0].class_id)
        if alts.count < 2:
            reasons.append(f"<2 members in {pure[0].class_id}")
        if not alts.disclaimer:
            reasons.append("missing disclaimer")

    shortage = await check_shortage(user_input)
    if shortage.overall_status not in _VALID_STATUS:
        reasons.append(f"bad status {shortage.overall_status!r}")

    return reasons


@pytest.mark.live
async def test_chain_eval_suite():
    results = []
    for user_input, expected in CASES:
        reasons = await _score_case(user_input, expected)
        results.append((user_input, not reasons, reasons))
        print(f"{'PASS' if not reasons else 'FAIL'}  {user_input:16} {reasons if reasons else ''}")

    passed = sum(1 for _, ok, _ in results if ok)
    rate = passed / len(results)
    print(f"\nchain success: {passed}/{len(results)} = {rate:.0%}")
    assert rate >= 0.90, f"chain success {rate:.0%} below the 90% gate"
