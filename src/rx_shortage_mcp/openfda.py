"""openFDA Drug Shortages client + aggregation.

Behavior is pinned against live API responses (see docs/JOURNAL.md):
- TOKENIZED search ``generic_name:<name>`` — never a quoted phrase (a quoted
  phrase returns NOT_FOUND for essentially everything).
- Statuses are an OPEN set (``Current`` / ``To Be Discontinued`` / ``Resolved`` / …);
  the date field is ``update_date`` (MM/DD/YYYY).
- Records are NDC/package-level (one drug → many rows) → aggregate by status.
- NOT_FOUND comes back as a 404 + JSON ``error`` object → ``no_record``, not an exception.
"""

from __future__ import annotations

import os
from collections import Counter
from datetime import datetime
from typing import Any

import httpx
from pydantic import BaseModel, Field

OPENFDA_SHORTAGES_URL = "https://api.fda.gov/drug/shortages.json"
_TIMEOUT = 15.0
# openFDA caps `limit` at 1000/request. Fetch all NDC-level records for a drug so the breadth
# count AND the per-status counts are TRUE totals, not capped (no real drug has >1000 records).
_DEFAULT_LIMIT = 1000

# An "active" shortage is Current or To Be Discontinued. Severity orders the summary.
_SEVERITY = {"Current": 3, "To Be Discontinued": 2, "Resolved": 1}
_ACTIVE = frozenset({"Current", "To Be Discontinued"})


class OpenFDAError(RuntimeError):
    """Raised on an openFDA API error other than NOT_FOUND."""


class StatusCount(BaseModel):
    status: str = Field(description="openFDA shortage status, e.g. 'Current', 'Resolved', 'To Be Discontinued'.")
    count: int = Field(description="Number of NDC/package-level records with this status.")


class ShortageResult(BaseModel):
    """Aggregated shortage summary for one drug (token-efficient — not raw records)."""

    drug: str = Field(description="The drug name that was queried.")
    in_shortage: bool = Field(description="True if any record is actively short (Current or To Be Discontinued).")
    overall_status: str = Field(description="Most severe status across records, or 'no_record' if none found.")
    statuses: list[StatusCount] = Field(description="Distinct statuses with their record counts.")
    record_count: int = Field(description="True total of NDC/package-level shortage records (openFDA meta total).")
    capped: bool = Field(description="True only if more records exist than were fetched (very rare; total > 1000).")
    last_updated: str | None = Field(description="Most recent record update date (MM/DD/YYYY), or null.")
    therapeutic_categories: list[str] = Field(description="Distinct therapeutic categories across the records.")
    reasons: list[str] = Field(description="Distinct shortage reasons across the records.")
    next_step: str = Field(description="Suggested next action for the agent orchestrating the chain.")


def _as_list(value: Any) -> list[str]:
    """openFDA fields like therapeutic_category may be a list or a scalar."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value if v]
    return [str(value)]


def _parse_date(value: str | None) -> datetime:
    try:
        return datetime.strptime(value or "", "%m/%d/%Y")
    except (ValueError, TypeError):
        return datetime.min


async def _fetch_records(drug_name: str, *, limit: int = _DEFAULT_LIMIT) -> tuple[list[dict], int]:
    params: dict[str, Any] = {"search": f"generic_name:{drug_name}", "limit": limit}
    api_key = os.environ.get("OPENFDA_API_KEY")
    if api_key:
        params["api_key"] = api_key

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.get(OPENFDA_SHORTAGES_URL, params=params)

    data = resp.json()
    if isinstance(data, dict) and "error" in data:
        code = data["error"].get("code")
        if code == "NOT_FOUND":
            return [], 0
        raise OpenFDAError(data["error"].get("message", f"openFDA error: {code}"))
    if resp.status_code >= 400:
        raise OpenFDAError(f"openFDA HTTP {resp.status_code}")
    results = data.get("results", [])
    total = data.get("meta", {}).get("results", {}).get("total", len(results))
    return results, total


def _summarize(drug_name: str, records: list[dict], total: int) -> ShortageResult:
    if not records:
        return ShortageResult(
            drug=drug_name,
            in_shortage=False,
            overall_status="no_record",
            statuses=[],
            record_count=0,
            capped=False,
            last_updated=None,
            therapeutic_categories=[],
            reasons=[],
            next_step=(
                "No shortage record found for this name. It may not be in shortage, or openFDA may "
                "list it under a different generic name. If evaluating it as an alternative, treat it "
                "as 'not currently listed in shortage' (and still confirm against local stock)."
            ),
        )

    counts = Counter(r.get("status", "Unknown") for r in records)
    statuses = [StatusCount(status=s, count=c) for s, c in counts.most_common()]
    overall_status = max(counts, key=lambda s: _SEVERITY.get(s, 0))
    in_shortage = any(s in _ACTIVE for s in counts)

    dated = [r.get("update_date") for r in records if r.get("update_date")]
    last_updated = max(dated, key=_parse_date) if dated else None

    categories = sorted({c for r in records for c in _as_list(r.get("therapeutic_category"))})
    reasons = sorted({r.get("shortage_reason") for r in records if r.get("shortage_reason")})

    if in_shortage:
        next_step = (
            "This drug is in shortage. To surface candidate alternatives, call rx_get_drug_class, "
            "then rx_find_alternatives, then rx_check_shortage on each candidate to flag any that are "
            "ALSO short (the cascade check)."
        )
    else:
        next_step = (
            "Records exist but none are active (e.g., Resolved). Treat as not currently short; "
            "still confirm against local stock."
        )

    return ShortageResult(
        drug=drug_name,
        in_shortage=in_shortage,
        overall_status=overall_status,
        statuses=statuses,
        record_count=total,
        capped=total > len(records),
        last_updated=last_updated,
        therapeutic_categories=categories,
        reasons=reasons,
        next_step=next_step,
    )


async def check_shortage(drug_name: str) -> ShortageResult:
    """Look up and aggregate the openFDA shortage status for ``drug_name``."""
    records, total = await _fetch_records(drug_name)
    return _summarize(drug_name, records, total)
