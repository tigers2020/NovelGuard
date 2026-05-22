"""Exact duplicate detection instrumentation counters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ExactDetectMetrics:
    """Per size-bucket (detect_exact invocation) hash I/O counters."""

    size_bucket_count: int = 0
    files_considered: int = 0
    prefix_hash_count: int = 0
    suffix_hash_count: int = 0
    full_hash_count: int = 0
    file_open_count: int = 0

    def merged(self, other: "ExactDetectMetrics") -> "ExactDetectMetrics":
        """Combine counters from multiple detect_exact calls (stage aggregates size buckets)."""
        return ExactDetectMetrics(
            size_bucket_count=self.size_bucket_count + other.size_bucket_count,
            files_considered=self.files_considered + other.files_considered,
            prefix_hash_count=self.prefix_hash_count + other.prefix_hash_count,
            suffix_hash_count=self.suffix_hash_count + other.suffix_hash_count,
            full_hash_count=self.full_hash_count + other.full_hash_count,
            file_open_count=self.file_open_count + other.file_open_count,
        )
