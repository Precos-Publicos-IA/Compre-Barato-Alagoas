"""Daily training job: LLM-driven catalog auto-improvement.

Runs once per day (or on demand). Processes all training flags, uses a capable
LLM to reason about SEFAZ data patterns, and updates the product catalog.

Token-efficient strategies:
1. Batch related flags together (same product, same flag type)
2. Send only relevant catalog entries, not the full catalog
3. Use structured prompts that minimize wasted tokens
4. Process in priority order (most-flagged products first)
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field

from ..catalog.manager import CatalogManager, ProductEntry, _strip_accents
from ..llm.guardrails import sanitize_for_llm
from .flags import TrainingFlagStore, TrainingFlag

logger = logging.getLogger(__name__)


def parse_training_response(text: str | None) -> dict:
    """Parse the capable model's JSON reply into a normalised dict of lists.

    Tolerates markdown code fences and stray prose around the JSON object.
    Returns ``{}`` on any failure so a garbled reply never crashes training.
    """
    if not text:
        return {}
    t = text.strip()
    if "```" in t:
        start = t.find("```")
        end = t.rfind("```")
        if start != end:
            t = t[start + 3 : end]
            if t.startswith("json"):
                t = t[4:]
            t = t.strip()
    # Grab the first {...} block if there is leading/trailing prose.
    if not t.startswith("{"):
        lo, hi = t.find("{"), t.rfind("}")
        if lo != -1 and hi > lo:
            t = t[lo : hi + 1]
    try:
        data = json.loads(t)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse training response: %s", text[:200])
        return {}
    return data if isinstance(data, dict) else {}


# System prompt for the training LLM (more capable model)
_TRAINING_SYSTEM = """\
You are the training engine for a Brazilian grocery price comparison app (Alagoas).

The app searches SEFAZ NFC-e (electronic receipt) data. Each business names products \
differently, so "leite" (milk) might appear as "LT UHT INTEGRAL 1L", "LEITE BETANIA \
INTEG.", "BOM LEITE INTEGRAL 1 LITRO", etc. The app maintains a product catalog where \
each product has:
- search_queries: what to send to the SEFAZ API
- sefaz_terms_positive: NFC-e descriptions that ARE this product
- sefaz_terms_negative: descriptions that are NOT this product but match queries
- brands: known brand names
- sizes: known package sizes

Your job: analyze training flags (failed searches, partial coverage, validation \
errors) and improve the catalog. You can:
1. Add/update search_queries for better SEFAZ coverage
2. Add positive/negative SEFAZ terms based on observed patterns
3. Add newly discovered brands and sizes
4. Approve or reject user-requested new products
5. Recommend new SEFAZ queries to test

IMPORTANT: Be conservative. Only add terms you're confident about. Better to miss \
one variant than to add a false positive (e.g., don't add "LEITE CONDENSADO" as a \
positive term for plain "leite").

Respond with STRICT JSON only.\
"""


@dataclass
class TrainingBatch:
    """A batch of related flags for one product."""

    product_id: int | None
    product_slug: str
    flags: list[tuple[int, TrainingFlag]]  # (index, flag)


@dataclass
class TrainingAction:
    """An action the training job will take on the catalog."""

    action_type: str  # "update_search_queries" | "add_positive_terms" | "add_negative_terms" | "add_brands" | "add_sizes" | "add_product" | "test_query"
    product_id: int | None = None
    product_slug: str = ""
    data: dict = field(default_factory=dict)
    reason: str = ""


@dataclass
class TrainingResult:
    """Result of one training run."""

    processed_flags: int = 0
    actions_taken: list[TrainingAction] = field(default_factory=list)
    new_products_added: int = 0
    products_updated: int = 0
    queries_tested: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class DailyTrainingJob:
    """Orchestrates the daily training cycle.

    Pipeline:
    1. Load pending training flags
    2. Group by product
    3. For each product batch, build a focused prompt
    4. Send to capable LLM for analysis
    5. Parse response into catalog updates
    6. Apply updates and resolve flags
    7. Process new product requests
    """

    def __init__(
        self,
        catalog: CatalogManager,
        flag_store: TrainingFlagStore,
        llm_client=None,       # LLMClient for making training calls
        sefaz_client=None,      # SefazClient for testing new queries
    ):
        self.catalog = catalog
        self.flags = flag_store
        self.llm = llm_client
        self.sefaz = sefaz_client

    async def run(self, *, sefaz_test_lat: float = -9.6633, sefaz_test_lon: float = -35.7089) -> TrainingResult:
        """Execute the full daily training pipeline."""
        t0 = time.time()
        result = TrainingResult()

        # 1. Load and batch flags
        pending = self.flags.pending_flags()
        has_product_requests = bool(self.catalog.pending_requests())

        if not pending and not has_product_requests:
            logger.info("No pending training flags or product requests")
            result.duration_seconds = time.time() - t0
            return result

        batches = self._batch_flags(pending) if pending else []
        logger.info("Training: %d pending flags in %d batches", len(pending), len(batches))

        # 2. Submit ALL batches to the capable model in a single Message Batches
        # request (token/cost efficient). Falls back to per-batch deterministic
        # rules when no LLM is configured or the batch call fails.
        llm_actions = await self._run_llm_batches(batches)

        # 3. Apply results per batch, recording a per-batch conclusion so every
        # flag line can be matched to what training concluded (audit requirement).
        conclusions: dict[int, str] = {}
        for i, batch in enumerate(batches):
            summary_parts: list[str] = []
            try:
                cid = f"batch-{i}"
                if llm_actions is not None and cid in llm_actions:
                    actions = llm_actions[cid]
                    source = "llm"
                else:
                    actions = self._deterministic_process_batch(batch)
                    source = "rules"
                for action in actions:
                    self._apply_action(action)
                    result.actions_taken.append(action)
                    if action.action_type == "add_product":
                        result.new_products_added += 1
                    elif action.action_type in (
                        "update_search_queries",
                        "add_positive_terms",
                        "add_negative_terms",
                        "add_brands",
                        "add_sizes",
                    ):
                        result.products_updated += 1
                        summary_parts.append(
                            f"{action.action_type}:{list(action.data.values())[0] if action.data else ''}"
                        )
                    elif action.action_type == "test_query":
                        outcome = await self._run_test_query(
                            batch.product_id, action.data.get("query", ""),
                            sefaz_test_lat, sefaz_test_lon,
                        )
                        result.queries_tested += 1
                        summary_parts.append(outcome)
                result.processed_flags += len(batch.flags)
                conclusion = (
                    f"[{source}] " + ("; ".join(summary_parts) if summary_parts else "no catalog change")
                )
            except Exception as e:
                logger.exception("Training batch failed for %s", batch.product_slug)
                result.errors.append(f"{batch.product_slug}: {e}")
                conclusion = f"error: {e}"
            # Match every flag in this batch to the conclusion (one line each).
            for idx, flag in batch.flags:
                conclusions[idx] = conclusion
                logger.info("[train] flag=%s product=%s -> %s",
                            flag.flag_type, batch.product_slug, conclusion)

        # 4. Process new product requests
        await self._process_product_requests(result)

        # 5. Save catalog
        self.catalog.save()

        # 6. Resolve flags with their individual conclusions.
        self.flags.resolve_all_pending(conclusions)

        result.duration_seconds = time.time() - t0
        logger.info(
            "Training complete: %d flags processed, %d actions, %d products updated, %.1fs",
            result.processed_flags,
            len(result.actions_taken),
            result.products_updated,
            result.duration_seconds,
        )
        return result

    def _batch_flags(self, flags: list[TrainingFlag]) -> list[TrainingBatch]:
        """Group flags by product for efficient LLM processing."""
        # Get the original indices in the full flag list for resolution
        all_flags = self.flags.all_flags()
        flag_indices = {}
        for i, f in enumerate(all_flags):
            if f.training_conclusion is None:
                flag_indices[id(f)] = i

        by_product: dict[str, list[tuple[int, TrainingFlag]]] = defaultdict(list)
        standalone: list[tuple[int, TrainingFlag]] = []

        pending = self.flags.pending_flags()
        for flag in pending:
            idx = flag_indices.get(id(flag), -1)
            slug = flag.product_slug or "unknown"
            if flag.product_id is not None:
                by_product[slug].append((idx, flag))
            else:
                standalone.append((idx, flag))

        batches = []
        for slug, items in by_product.items():
            pid = items[0][1].product_id
            batches.append(TrainingBatch(
                product_id=pid,
                product_slug=slug,
                flags=items,
            ))

        # Standalone flags (no product_id, like incomplete coverage)
        if standalone:
            batches.append(TrainingBatch(
                product_id=None,
                product_slug="general",
                flags=standalone,
            ))

        # Priority: most-flagged products first
        batches.sort(key=lambda b: -len(b.flags))
        return batches

    async def _run_llm_batches(
        self,
        batches: list[TrainingBatch],
    ) -> dict[str, list[TrainingAction]] | None:
        """Send every batch to the capable model in ONE Batches API submission.

        Returns ``{custom_id -> [TrainingAction]}`` for the batches the model
        answered, or ``None`` when no batch-capable LLM is configured or the
        submission failed (caller then uses the deterministic fallback).
        """
        if (
            self.llm is None
            or not hasattr(self.llm, "training_analysis_batch")
            or not batches
        ):
            return None

        items: list[tuple[str, str]] = []
        for i, batch in enumerate(batches):
            product = self.catalog.get(batch.product_id) if batch.product_id else None
            items.append((f"batch-{i}", self._build_training_prompt(batch, product)))

        try:
            raw = await self.llm.training_analysis_batch(items)
        except Exception:
            logger.exception("Training batch submission failed; using rules")
            return None
        if raw is None:
            return None

        out: dict[str, list[TrainingAction]] = {}
        for i, batch in enumerate(batches):
            cid = f"batch-{i}"
            parsed = parse_training_response(raw.get(cid))
            out[cid] = self._actions_from_llm(batch, parsed)
        return out

    def _actions_from_llm(
        self,
        batch: TrainingBatch,
        parsed: dict,
    ) -> list[TrainingAction]:
        """Turn the model's parsed JSON suggestions into catalog actions.

        The model is trusted less than the catalog: we only accept the specific
        additive fields it is allowed to touch, and ignore anything else.
        """
        actions: list[TrainingAction] = []
        pid = batch.product_id
        slug = batch.product_slug

        def _clean_list(key: str) -> list[str]:
            vals = parsed.get(key) or []
            if not isinstance(vals, list):
                return []
            return [str(v).strip() for v in vals if str(v).strip()]

        field_map = [
            ("search_queries_to_add", "update_search_queries", "add_queries"),
            ("positive_terms_to_add", "add_positive_terms", "terms"),
            ("negative_terms_to_add", "add_negative_terms", "terms"),
            ("brands_to_add", "add_brands", "brands"),
            ("sizes_to_add", "add_sizes", "sizes"),
        ]
        reasoning = str(parsed.get("reasoning", ""))[:300]
        for src_key, action_type, data_key in field_map:
            vals = _clean_list(src_key)
            if vals and pid is not None:
                actions.append(TrainingAction(
                    action_type=action_type,
                    product_id=pid,
                    product_slug=slug,
                    data={data_key: vals},
                    reason=reasoning or f"LLM training: {src_key}",
                ))

        for q in _clean_list("queries_to_test"):
            actions.append(TrainingAction(
                action_type="test_query",
                product_id=pid,
                product_slug=slug,
                data={"query": q},
                reason=reasoning or "LLM suggested SEFAZ query to test",
            ))
        return actions

    # Fallback probe locations across Alagoas: if a query returns nothing where
    # the user is, the product may simply not be sold nearby — so we retry in the
    # main population centres before concluding the query itself is bad.
    _FALLBACK_LOCATIONS = [
        (-9.6633, -35.7089),   # Maceió
        (-9.7519, -36.6614),   # Arapiraca
        (-9.4058, -36.6289),   # Palmeira dos Índios
    ]

    async def _run_test_query(
        self,
        product_id: int | None,
        query: str,
        test_lat: float,
        test_lon: float,
    ) -> str:
        """Run a candidate SEFAZ query; adopt it into search_queries if it works.

        Returns a short human-readable outcome for the training log. Tries the
        primary location first, then Alagoas fallbacks, so a query isn't rejected
        just because the product is absent in one region.
        """
        query = (query or "").strip()
        if not query or self.sefaz is None or product_id is None:
            return f"test_query '{query}': skipped (no sefaz client)"
        product = self.catalog.get(product_id)
        if product is None:
            return f"test_query '{query}': skipped (unknown product)"

        locations = [(test_lat, test_lon), *self._FALLBACK_LOCATIONS]
        for lat, lon in locations:
            try:
                resp = await self.sefaz.search_product(
                    descricao=query, latitude=lat, longitude=lon,
                    radius_km=15, days=10,
                )
            except Exception:
                logger.warning("test_query SEFAZ call failed for '%s'", query, exc_info=True)
                continue
            n = len(getattr(resp, "conteudo", []) or [])
            if n > 0:
                if query not in product.search_queries:
                    product.search_queries.append(query)
                    self.catalog.update_product(product_id, {})
                return f"test_query '{query}': {n} hits @({lat:.2f},{lon:.2f}) -> adopted"
        return f"test_query '{query}': no results in any region -> not adopted"

    def _build_training_prompt(
        self,
        batch: TrainingBatch,
        product: ProductEntry | None,
    ) -> str:
        """Build a focused prompt for one product's training batch."""
        lines = []
        if product:
            lines.append(f"Product: {product.display_name} (slug: {product.slug})")
            lines.append(f"Category: {product.category}")
            lines.append(f"Current search_queries: {product.search_queries}")
            lines.append(f"Current positive terms ({len(product.sefaz_terms_positive)}):")
            for t in product.sefaz_terms_positive[:5]:
                lines.append(f"  + {t}")
            lines.append(f"Current negative terms ({len(product.sefaz_terms_negative)}):")
            for t in product.sefaz_terms_negative[:5]:
                lines.append(f"  - {t}")
            lines.append(f"Brands: {product.brands}")
            lines.append(f"Sizes: {product.sizes}")
        lines.append(f"\nTraining flags ({len(batch.flags)}):")
        for idx, flag in batch.flags[:20]:  # Cap to save tokens
            # flag.details carries SEFAZ- and user-derived text; sanitise it so a
            # crafted product description can't inject instructions into the prompt.
            detail = sanitize_for_llm(
                json.dumps(flag.details, ensure_ascii=False), max_len=300
            )
            lines.append(f"  [{flag.flag_type}] {detail}")

        lines.append("\nAnalyze and suggest improvements. Respond with JSON:")
        lines.append("""{
  "search_queries_to_add": ["term1"],
  "positive_terms_to_add": ["desc1"],
  "negative_terms_to_add": ["desc1"],
  "brands_to_add": ["brand1"],
  "sizes_to_add": ["size1"],
  "queries_to_test": ["query_to_try_on_sefaz"],
  "reasoning": "brief explanation"
}""")
        return "\n".join(lines)

    def _deterministic_process_batch(
        self,
        batch: TrainingBatch,
    ) -> list[TrainingAction]:
        """Rule-based fallback when LLM is unavailable."""
        actions = []
        product = self.catalog.get(batch.product_id) if batch.product_id else None

        for idx, flag in batch.flags:
            if flag.flag_type == "product_not_found":
                # If the product wasn't found, the search queries might be too narrow
                if product and flag.details.get("search_terms_used"):
                    terms = flag.details["search_terms_used"]
                    # Suggest using just the base product name
                    base = _strip_accents(product.display_name)
                    if base not in terms:
                        actions.append(TrainingAction(
                            action_type="update_search_queries",
                            product_id=batch.product_id,
                            product_slug=batch.product_slug,
                            data={"add_queries": [base]},
                            reason=f"Product not found with terms {terms}; adding base name",
                        ))

            elif flag.flag_type == "validation_failure":
                # Add rejected descriptions as negative terms
                rejected = flag.details.get("rejected_descriptions", [])
                if rejected and product:
                    actions.append(TrainingAction(
                        action_type="add_negative_terms",
                        product_id=batch.product_id,
                        product_slug=batch.product_slug,
                        data={"terms": rejected[:5]},
                        reason=f"Validation failure: {flag.details.get('reason', '')}",
                    ))

            elif flag.flag_type == "incomplete_store_coverage":
                # Log the coverage gap for the training record
                logger.info(
                    "Store %s has %.0f%% coverage: found=%s, missing=%s",
                    flag.details.get("store_name", "?"),
                    flag.details.get("coverage_ratio", 0) * 100,
                    flag.details.get("products_found", []),
                    flag.details.get("products_missing", []),
                )

        return actions

    def _apply_action(self, action: TrainingAction) -> None:
        """Apply a training action to the catalog."""
        if action.product_id is None:
            return
        product = self.catalog.get(action.product_id)
        if not product:
            return

        if action.action_type == "update_search_queries":
            new_queries = action.data.get("add_queries", [])
            for q in new_queries:
                if q not in product.search_queries:
                    product.search_queries.append(q)

        elif action.action_type == "add_positive_terms":
            new_terms = action.data.get("terms", [])
            for t in new_terms:
                if t not in product.sefaz_terms_positive:
                    product.sefaz_terms_positive.append(t)

        elif action.action_type == "add_negative_terms":
            new_terms = action.data.get("terms", [])
            for t in new_terms:
                if t not in product.sefaz_terms_negative:
                    product.sefaz_terms_negative.append(t)

        elif action.action_type == "add_brands":
            new_brands = action.data.get("brands", [])
            for b in new_brands:
                if b not in product.brands:
                    product.brands.append(b)

        elif action.action_type == "add_sizes":
            new_sizes = action.data.get("sizes", [])
            for s in new_sizes:
                if s not in product.sizes:
                    product.sizes.append(s)

        self.catalog.update_product(action.product_id, {})  # rebuild index
        logger.info("Applied %s to %s: %s", action.action_type, action.product_slug, action.reason)

    async def _process_product_requests(self, result: TrainingResult) -> None:
        """Process pending product requests: check duplicates, add valid ones."""
        # Build a list of (global_index, request) for pending items so we can
        # resolve them correctly in the catalog's full _requests list.
        all_reqs = self.catalog._requests  # direct access for correct indexing
        pending_with_idx = [
            (i, req) for i, req in enumerate(all_reqs) if req.status == "pending"
        ]
        for global_idx, req in pending_with_idx:
            # Requested names are free user text: sanitise before it is used to
            # build a slug/display name or (in production) sent to the LLM.
            safe_name = sanitize_for_llm(req.name, max_len=60)
            if not safe_name:
                self.catalog.update_request(
                    global_idx, "rejected",
                    notes="Empty after sanitisation",
                )
                continue
            name_norm = _strip_accents(safe_name)

            # Check for duplicates in catalog
            matches = self.catalog.search(safe_name, limit=3)
            is_dup = any(
                _strip_accents(m.display_name) == name_norm or m.slug == name_norm.replace(" ", "_")
                for m in matches
            )

            if is_dup:
                match = matches[0]
                self.catalog.update_request(
                    global_idx, "duplicate",
                    notes=f"Duplicate of existing product: {match.display_name} (id={match.id})",
                    resolved_id=match.id,
                )
                continue

            # A brand-new product enters DISABLED. It has no SEFAZ terms yet, so
            # searching it would only produce noise, and we never want raw user
            # text to go live unreviewed. The capable model (or a human admin)
            # enables it once it has real positive/negative terms.
            new_id = self.catalog.next_id()
            slug = name_norm.replace(" ", "_")
            entry = ProductEntry(
                id=new_id,
                slug=slug,
                display_name=safe_name.capitalize(),
                category="uncategorized",
                search_queries=[name_norm],
                sefaz_terms_positive=[],
                sefaz_terms_negative=[],
                brands=[],
                sizes=[],
                enabled=False,
            )
            self.catalog.add_product(entry)
            self.catalog.update_request(
                global_idx, "approved",
                notes=f"Added as new (disabled, pending terms) product id={new_id}",
                resolved_id=new_id,
            )
            result.new_products_added += 1
            logger.info("Added new product from request: %s (id=%d, disabled)", safe_name, new_id)
