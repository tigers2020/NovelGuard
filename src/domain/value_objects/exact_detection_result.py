"""Exact duplicate detection outcome + metrics."""

from dataclasses import dataclass

from domain.value_objects.duplicate_relation import ExactDuplicateRelation
from domain.value_objects.exact_detect_metrics import ExactDetectMetrics


@dataclass(frozen=True)
class ExactDetectionResult:
    """Exact duplicate relations and instrumentation (metrics do not affect grouping)."""

    relations: list[ExactDuplicateRelation]
    metrics: ExactDetectMetrics
