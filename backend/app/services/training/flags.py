"""Training flag store — persists data points flagged for training.

Flags are written during search (hot path) and consumed by the daily training
job. They are stored in a JSON file (not in Python source) so the training job
can read, process, and clear them.

Flag types:
- product_not_found: A product was not found in any store
- incomplete_store_coverage: A store had 20-80% of products (likely missing terms)
- validation_failure: LLM flagged SEFAZ results as invalid
- new_terms_discovered: Training job discovered new positive/negative terms
- product_request: User requested a product not in the catalog
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

logger = logging.getLogger(__name__)

_FLAGS_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "training_flags.json"


@dataclass
class TrainingFlag:
    """A data point flagged for training."""

    flag_type: str
    product_id: int | None = None
    product_slug: str = ""
    details: dict = field(default_factory=dict)
    created_at: str = ""
    training_conclusion: str | None = None  # filled by training job

    def to_dict(self) -> dict:
        return {
            "flag_type": self.flag_type,
            "product_id": self.product_id,
            "product_slug": self.product_slug,
            "details": self.details,
            "created_at": self.created_at,
            "training_conclusion": self.training_conclusion,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TrainingFlag":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


class TrainingFlagStore:
    """Thread-safe store for training flags, backed by JSON on disk."""

    def __init__(self, path: Path | str | None = None):
        self._path = Path(path) if path else _FLAGS_PATH
        self._lock = threading.Lock()
        self._flags: list[TrainingFlag] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            with open(self._path, encoding="utf-8") as f:
                data = json.load(f)
            self._flags = [TrainingFlag.from_dict(d) for d in data.get("flags", [])]
        except Exception:
            logger.exception("Failed to load training flags")

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "flags": [f.to_dict() for f in self._flags],
        }
        tmp = self._path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.rename(self._path)

    def add_flag(
        self,
        flag_type: str,
        product_id: int | None = None,
        product_slug: str = "",
        details: dict | None = None,
    ) -> TrainingFlag:
        """Add a training flag (called from the search hot path)."""
        flag = TrainingFlag(
            flag_type=flag_type,
            product_id=product_id,
            product_slug=product_slug,
            details=details or {},
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        with self._lock:
            self._flags.append(flag)
            self._save()
        return flag

    def flag_product_not_found(
        self,
        product_id: int,
        product_slug: str,
        search_terms_used: list[str],
        location: tuple[float, float] | None = None,
    ) -> TrainingFlag:
        """Flag a product that wasn't found in any store."""
        return self.add_flag(
            "product_not_found",
            product_id=product_id,
            product_slug=product_slug,
            details={
                "search_terms_used": search_terms_used,
                "location": list(location) if location else None,
            },
        )

    def flag_incomplete_coverage(
        self,
        store_cnpj: str,
        store_name: str,
        products_found: list[str],
        products_missing: list[str],
        coverage_ratio: float,
    ) -> TrainingFlag:
        """Flag a store with 20-80% coverage (likely missing SEFAZ terms)."""
        return self.add_flag(
            "incomplete_store_coverage",
            details={
                "store_cnpj": store_cnpj,
                "store_name": store_name,
                "products_found": products_found,
                "products_missing": products_missing,
                "coverage_ratio": coverage_ratio,
            },
        )

    def flag_validation_failure(
        self,
        product_id: int,
        product_slug: str,
        search_term: str,
        rejected_descriptions: list[str],
        reason: str,
    ) -> TrainingFlag:
        """Flag a validation failure for a product's SEFAZ results."""
        return self.add_flag(
            "validation_failure",
            product_id=product_id,
            product_slug=product_slug,
            details={
                "search_term": search_term,
                "rejected_descriptions": rejected_descriptions,
                "reason": reason,
            },
        )

    def pending_flags(self) -> list[TrainingFlag]:
        """Get all flags not yet processed by the training job."""
        with self._lock:
            return [f for f in self._flags if f.training_conclusion is None]

    def all_flags(self) -> list[TrainingFlag]:
        with self._lock:
            return list(self._flags)

    def resolve_flag(self, index: int, conclusion: str) -> None:
        """Mark a flag as processed with the training conclusion."""
        with self._lock:
            if 0 <= index < len(self._flags):
                self._flags[index].training_conclusion = conclusion
                self._save()

    def resolve_all_pending(self, conclusions: dict[int, str]) -> None:
        """Bulk-resolve flags by index."""
        with self._lock:
            for idx, conclusion in conclusions.items():
                if 0 <= idx < len(self._flags):
                    self._flags[idx].training_conclusion = conclusion
            self._save()

    def clear_resolved(self) -> int:
        """Remove flags that have been resolved (housekeeping)."""
        with self._lock:
            before = len(self._flags)
            self._flags = [f for f in self._flags if f.training_conclusion is None]
            self._save()
            return before - len(self._flags)


# Process-wide singleton (mirrors catalog.manager.get_catalog).
_flag_store: TrainingFlagStore | None = None


def get_flag_store(path: Path | str | None = None) -> TrainingFlagStore:
    global _flag_store
    if _flag_store is None:
        _flag_store = TrainingFlagStore(path=path or None)
    return _flag_store
