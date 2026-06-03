"""Thresholds for streaming scan pipeline (spec 028)."""

SCAN_PERSIST_BATCH_SIZE = 400
SCAN_DEEP_ANALYSIS_BACKGROUND_THRESHOLD = 3000
SCAN_PROGRESS_THROTTLE_FILES = 48
# Below 2 MiB (is_large_file): skip full-file read when hash not required.
SCAN_PROBE_SAMPLE_ENCODING_MIN_BYTES = 256 * 1024
# Encoding-only probe: head/tail sample instead of full read (hash not needed).
SCAN_PROBE_ENCODING_ONLY_SAMPLE_MIN_BYTES = 8 * 1024
# Stem-hash only for small duplicate-name clusters (avoids hashing thousands in one title bucket).
SCAN_STEM_HASH_MIN_GROUP_SIZE = 2
SCAN_STEM_HASH_MAX_GROUP_SIZE = 32
# Large-library near/relation: bounded comparisons + head-only reads.
SCAN_NEAR_FAST_LIBRARY_THRESHOLD = 500
SCAN_NEAR_MAX_BUCKET_ITEMS = 200
SCAN_NEAR_MAX_BAND_FANOUT = 64
SCAN_NEAR_MAX_JACCARD_CHECKS = 800_000
