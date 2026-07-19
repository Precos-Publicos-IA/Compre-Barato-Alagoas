"""LLM-based SEFAZ output validation.

After SEFAZ returns results for all products, a cheap LLM evaluates whether
each product's results are sensible. If nonsense is detected, the validator:
1. Invalidates the cache for that product
2. Updates the SEFAZ terms (positive/negative) for that product
3. Triggers a re-query with corrected terms

Also handles training flags:
- Products not found in any store
- Stores with partial coverage (20-80% of products) → likely missing SEFAZ terms
"""

from __future__ import annotations

import json
import logging
import time
import unicodedata
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def _strip_accents(s: str) -> str:
    nk = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nk if not unicodedata.combining(c)).lower().strip()


@dataclass
class ValidationResult:
    """Result of validating SEFAZ output for one product."""

    product_id: int
    product_slug: str
    valid: bool
    reason: str = ""
    # If invalid, the corrected search terms to retry
    corrected_search_terms: list[str] | None = None
    # New negative terms discovered
    new_negative_terms: list[str] | None = None
    # Descriptions that were clearly wrong matches
    rejected_descriptions: list[str] | None = None


@dataclass
class TrainingFlag:
    """A data point flagged for the daily training job."""

    flag_type: str  # "product_not_found" | "incomplete_store_coverage" | "validation_failure" | "new_terms_discovered"
    product_id: int
    product_slug: str
    details: dict = field(default_factory=dict)
    created_at: str = ""
    training_conclusion: str | None = None  # filled by training job


@dataclass
class StoreCoverageAnalysis:
    """Analysis of which stores had which products."""

    store_cnpj: str
    store_name: str
    products_found: list[str]
    products_missing: list[str]
    coverage_ratio: float


# System prompt for the cheap validation LLM
_VALIDATION_SYSTEM = """\
You are a SEFAZ NFC-e (Brazilian electronic receipt) data validator for a grocery \
price comparison app in Alagoas. Your job is to check whether SEFAZ search results \
actually match the product the user is looking for.

SEFAZ data is dirty: each business defines product names differently. Common issues:
- "LEITE CONDENSADO" returned when searching for "LEITE" (milk) — wrong product
- "ARROZ P CAES" (dog food) returned when searching for "ARROZ" (rice) — wrong
- "OLEO DE COCO" returned when searching for "OLEO" (cooking oil) — wrong
- "TEMPERO PARA FEIJÃO" returned when searching for "FEIJÃO" — wrong

For each product, you receive:
1. The product the user wants (display name + category)
2. The SEFAZ search terms used
3. Sample descriptions from results
4. Known positive terms (correct matches)
5. Known negative terms (known false positives)

Respond with STRICT JSON only. For each product, output:
{
  "product_slug": "...",
  "valid": true/false,
  "reason": "brief explanation",
  "rejected_descriptions": ["desc1", "desc2"],
  "suggested_positive_terms": ["term1"],
  "suggested_negative_terms": ["term1"],
  "corrected_search_terms": ["better query"]
}

Be conservative: only flag as invalid if clearly wrong. SEFAZ descriptions are \
abbreviated and ugly — that's normal, not invalid. Focus on category mismatches \
(dog food vs human food, cleaning vs cooking, condiment vs the actual ingredient).\
"""


def build_validation_prompt(
    product_results: list[dict],
) -> str:
    """Build the LLM prompt for batch validation of SEFAZ results.

    Each entry in product_results should have:
    - product_slug, display_name, category
    - search_terms_used: list[str]
    - sample_descriptions: list[str]  (top N descriptions from results)
    - known_positive: list[str]
    - known_negative: list[str]
    """
    lines = ["Validate these SEFAZ search results:\n"]
    for i, pr in enumerate(product_results, 1):
        lines.append(f"--- Product {i}: {pr['display_name']} ---")
        lines.append(f"Category: {pr['category']}")
        lines.append(f"Search terms used: {', '.join(pr['search_terms_used'])}")
        lines.append(f"Sample descriptions from results:")
        for desc in pr.get("sample_descriptions", [])[:10]:
            lines.append(f"  - {desc}")
        if pr.get("known_positive"):
            lines.append(f"Known positive (correct): {', '.join(pr['known_positive'][:5])}")
        if pr.get("known_negative"):
            lines.append(f"Known negative (wrong): {', '.join(pr['known_negative'][:5])}")
        lines.append("")
    lines.append("Respond with a JSON array, one object per product.")
    return "\n".join(lines)


def parse_validation_response(response_text: str) -> list[dict]:
    """Parse the LLM's JSON response into structured validation results."""
    try:
        # Try to extract JSON from the response
        text = response_text.strip()
        # Handle markdown code blocks
        if "```" in text:
            start = text.find("```")
            end = text.rfind("```")
            if start != end:
                text = text[start:end]
                # Remove ```json prefix
                if text.startswith("```json"):
                    text = text[7:]
                elif text.startswith("```"):
                    text = text[3:]
                text = text.strip()

        # Try parsing as JSON array
        if text.startswith("["):
            return json.loads(text)
        # Try parsing as single object
        if text.startswith("{"):
            return [json.loads(text)]
        return []
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse validation response: %s", response_text[:200])
        return []


def deterministic_validate(
    product_slug: str,
    display_name: str,
    category: str,
    descriptions: list[str],
    known_negative: list[str],
) -> ValidationResult:
    """Rule-based validation fallback when LLM is unavailable.

    Checks if descriptions match known negative patterns.
    """
    rejected = []
    neg_norms = [_strip_accents(n) for n in known_negative]

    for desc in descriptions:
        desc_norm = _strip_accents(desc)
        for neg in neg_norms:
            neg_tokens = neg.split()
            if all(t in desc_norm for t in neg_tokens if len(t) >= 3):
                rejected.append(desc)
                break

    valid = len(rejected) < len(descriptions) * 0.5 if descriptions else True

    return ValidationResult(
        product_id=0,
        product_slug=product_slug,
        valid=valid,
        reason="deterministic_check" if valid else f"too many negative matches ({len(rejected)}/{len(descriptions)})",
        rejected_descriptions=rejected if rejected else None,
    )


def analyze_store_coverage(
    store_products: dict[str, dict],
    total_products_requested: int,
) -> list[TrainingFlag]:
    """Analyze store coverage to flag products with incomplete SEFAZ terms.

    If a store has >20% but <80% of products, the missing products likely
    have incomplete SEFAZ terms for that store's naming convention.
    """
    flags = []

    for cnpj, info in store_products.items():
        found = info.get("found", [])
        missing = info.get("missing", [])
        total = len(found) + len(missing)
        if total == 0:
            continue

        ratio = len(found) / total_products_requested
        if 0.20 < ratio < 0.80 and missing:
            flags.append(
                TrainingFlag(
                    flag_type="incomplete_store_coverage",
                    product_id=0,
                    product_slug="",
                    details={
                        "store_cnpj": cnpj,
                        "store_name": info.get("name", ""),
                        "products_found": found,
                        "products_missing": missing,
                        "coverage_ratio": round(ratio, 3),
                    },
                    created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                )
            )

    return flags
