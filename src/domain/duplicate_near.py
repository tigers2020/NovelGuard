"""Near duplicate detection via normalized text n-gram fingerprints (PR-19)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

ALGORITHM_VERSION = "near-ngram-v2"
NEAR_DUP_THRESHOLD = 0.82
MIN_NORMALIZED_CHARS = 200
MAX_NORMALIZED_CHARS = 512 * 1024
LENGTH_RATIO_THRESHOLD = 0.60
WORD_NGRAM_SIZE = 5
CHAR_NGRAM_SIZE = 5
MAX_FINGERPRINTS_PER_FILE = 256
# Large-library caps (keep in sync with scan_pipeline_constants).
_NEAR_LARGE_MAX_BUCKET_ITEMS = 200
_NEAR_LARGE_MAX_BAND_FANOUT = 64
_NEAR_LARGE_MAX_JACCARD_CHECKS = 800_000
_NEAR_DEFAULT_MAX_BUCKET_ITEMS = 10_000
_NEAR_DEFAULT_MAX_BAND_FANOUT = 512
_NEAR_MEDIUM_LIBRARY_MIN_ELIGIBLE = 500
_NEAR_LARGE_LIBRARY_MIN_ELIGIBLE = 3_000
_NEAR_MEDIUM_MAX_BUCKET_ITEMS = 500
_NEAR_MEDIUM_MAX_BAND_FANOUT = 96
_NEAR_MEDIUM_MAX_JACCARD_CHECKS = 250_000

_EXTENSION_FAMILIES: dict[str, str] = {
    ".txt": "plain",
    ".md": "plain",
    ".markdown": "plain",
    ".html": "markup",
    ".htm": "markup",
    ".xml": "markup",
    ".json": "structured",
    ".csv": "structured",
}

_LENGTH_BUCKET_BOUNDS = (
    1024,
    4 * 1024,
    16 * 1024,
    64 * 1024,
    256 * 1024,
    MAX_NORMALIZED_CHARS + 1,
)
_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class NearDuplicateInput:
    file_id: str
    path: str
    extension: str
    content_hash: str | None
    size_bytes: int | None
    mtime_ns: int | None
    text: str | None


@dataclass(frozen=True, slots=True)
class NearDuplicatePair:
    left_file_id: str
    right_file_id: str
    similarity_score: float
    shared_fingerprint_count: int
    left_fingerprint_count: int
    right_fingerprint_count: int


@dataclass(frozen=True, slots=True)
class NearDuplicateGroup:
    group_id: str
    member_file_ids: tuple[str, ...]
    pairs: tuple[NearDuplicatePair, ...]
    max_similarity: float


@dataclass(frozen=True, slots=True)
class NearDuplicateStats:
    eligible_file_count: int
    skipped_file_count: int
    bucket_count: int
    candidate_pair_count: int
    accepted_pair_count: int
    group_count: int


@dataclass(frozen=True, slots=True)
class NearDuplicateResult:
    near_batch_id: str
    algorithm_version: str
    threshold: float
    groups: tuple[NearDuplicateGroup, ...]
    stats: NearDuplicateStats


@dataclass(frozen=True, slots=True)
class _PreparedFile:
    input: NearDuplicateInput
    norm_len: int
    fingerprints: frozenset[bytes]
    fingerprint_count: int
    family: str
    length_bucket: int


def normalize_text_for_near_dup(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.lower()
    normalized = _WHITESPACE_RE.sub(" ", normalized)
    return normalized.strip()


def _fingerprint_token(gram: str) -> bytes:
    return hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()


def _sample_indices(gram_count: int, *, max_items: int) -> range:
    if gram_count <= max_items:
        return range(gram_count)
    step = gram_count // max_items + 1
    return range(0, gram_count, step)[:max_items]


def fingerprint_set(normalized: str) -> frozenset[bytes]:
    tokens = normalized.split()
    if len(tokens) >= WORD_NGRAM_SIZE:
        gram_count = len(tokens) - WORD_NGRAM_SIZE + 1
        picked = _sample_indices(gram_count, max_items=MAX_FINGERPRINTS_PER_FILE)
        return frozenset(
            _fingerprint_token(" ".join(tokens[index : index + WORD_NGRAM_SIZE]))
            for index in picked
        )
    if len(normalized) >= CHAR_NGRAM_SIZE:
        gram_count = len(normalized) - CHAR_NGRAM_SIZE + 1
        picked = _sample_indices(gram_count, max_items=MAX_FINGERPRINTS_PER_FILE)
        return frozenset(
            _fingerprint_token(normalized[index : index + CHAR_NGRAM_SIZE]) for index in picked
        )
    return frozenset()


def jaccard_similarity(left: frozenset[bytes], right: frozenset[bytes]) -> float:
    if not left or not right:
        return 0.0
    shared = len(left & right)
    return _jaccard_from_sizes(shared, len(left), len(right))


def _jaccard_from_sizes(shared: int, size_left: int, size_right: int) -> float:
    if shared <= 0 or size_left <= 0 or size_right <= 0:
        return 0.0
    union = size_left + size_right - shared
    if union <= 0:
        return 0.0
    return shared / union


def _shared_fingerprint_count(left: frozenset[bytes], right: frozenset[bytes]) -> int:
    return len(left & right)


def extension_family(extension: str) -> str | None:
    return _EXTENSION_FAMILIES.get(extension.lower())


def length_bucket(normalized_length: int) -> int:
    for index, bound in enumerate(_LENGTH_BUCKET_BOUNDS):
        if normalized_length < bound:
            return index
    return len(_LENGTH_BUCKET_BOUNDS) - 1


def length_ratio_ok(len_a: int, len_b: int) -> bool:
    if len_a <= 0 or len_b <= 0:
        return False
    return min(len_a, len_b) / max(len_a, len_b) >= LENGTH_RATIO_THRESHOLD


def _should_skip_pair(
    left: _PreparedFile,
    right: _PreparedFile,
    *,
    exact_group_by_file_id: Mapping[str, str],
) -> bool:
    if left.input.content_hash and left.input.content_hash == right.input.content_hash:
        return True
    left_exact = exact_group_by_file_id.get(left.input.file_id)
    right_exact = exact_group_by_file_id.get(right.input.file_id)
    if left_exact and right_exact and left_exact == right_exact:
        return True
    return False


def prepare_near_duplicate_input(item: NearDuplicateInput) -> _PreparedFile | None:
    return _prepare_file(item)


def _prepare_file(item: NearDuplicateInput) -> _PreparedFile | None:
    family = extension_family(item.extension)
    if family is None or not item.text:
        return None
    normalized = normalize_text_for_near_dup(item.text)
    norm_len = len(normalized)
    if norm_len < MIN_NORMALIZED_CHARS or norm_len > MAX_NORMALIZED_CHARS:
        return None
    fingerprints = fingerprint_set(normalized)
    if not fingerprints:
        return None
    return _PreparedFile(
        input=item,
        norm_len=norm_len,
        fingerprints=fingerprints,
        fingerprint_count=len(fingerprints),
        family=family,
        length_bucket=length_bucket(norm_len),
    )


def _near_dup_limits(
    eligible_count: int,
    *,
    large_library: bool,
) -> tuple[int, int, int | None, int]:
    """Scale bucket/fanout/check caps with library size (O(n²) guard)."""
    if large_library or eligible_count >= _NEAR_LARGE_LIBRARY_MIN_ELIGIBLE:
        return (
            _NEAR_LARGE_MAX_BUCKET_ITEMS,
            _NEAR_LARGE_MAX_BAND_FANOUT,
            _NEAR_LARGE_MAX_JACCARD_CHECKS,
            0,
        )
    if eligible_count >= _NEAR_MEDIUM_LIBRARY_MIN_ELIGIBLE:
        return (
            _NEAR_MEDIUM_MAX_BUCKET_ITEMS,
            _NEAR_MEDIUM_MAX_BAND_FANOUT,
            _NEAR_MEDIUM_MAX_JACCARD_CHECKS,
            0,
        )
    return (
        _NEAR_DEFAULT_MAX_BUCKET_ITEMS,
        _NEAR_DEFAULT_MAX_BAND_FANOUT,
        None,
        1,
    )


class _UnionFind:
    def __init__(self, items: Sequence[str]) -> None:
        self._parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self._parent[item]
        if parent != item:
            self._parent[item] = self.find(parent)
        return self._parent[item]

    def union(self, left: str, right: str) -> None:
        root_left = self.find(left)
        root_right = self.find(right)
        if root_left != root_right:
            self._parent[root_right] = root_left


def _cap_bucket_items(items: Sequence[_PreparedFile], max_bucket_items: int) -> list[_PreparedFile]:
    bucket_items = list(items)
    if len(bucket_items) <= max_bucket_items:
        return bucket_items
    bucket_items.sort(key=lambda item: item.input.file_id)
    return bucket_items[:max_bucket_items]


def _fingerprint_index(
    bucket_items: Sequence[_PreparedFile], max_band_fanout: int
) -> dict[bytes, list[_PreparedFile]]:
    fp_to_items: dict[bytes, list[_PreparedFile]] = defaultdict(list)
    for item in bucket_items:
        for fp in item.fingerprints:
            fp_list = fp_to_items[fp]
            if len(fp_list) < max_band_fanout:
                fp_list.append(item)
    return fp_to_items


def _candidate_map_for_left(
    left: _PreparedFile,
    fp_to_items: dict[bytes, list[_PreparedFile]],
    max_candidates_per_file: int,
) -> dict[str, _PreparedFile]:
    left_id = left.input.file_id
    candidates: dict[str, _PreparedFile] = {}
    for fp in left.fingerprints:
        for other in fp_to_items.get(fp, ()):
            right_id = other.input.file_id
            if right_id <= left_id:
                continue
            if right_id not in candidates:
                if len(candidates) >= max_candidates_per_file:
                    break
                candidates[right_id] = other
        if len(candidates) >= max_candidates_per_file:
            break
    return candidates


def _maybe_near_pair(
    left: _PreparedFile,
    right: _PreparedFile,
    *,
    exact_group_by_file_id: Mapping[str, str],
    threshold: float,
) -> NearDuplicatePair | None:
    if not length_ratio_ok(left.norm_len, right.norm_len):
        return None
    if _should_skip_pair(left, right, exact_group_by_file_id=exact_group_by_file_id):
        return None
    left_size = left.fingerprint_count
    right_size = right.fingerprint_count
    smaller = min(left_size, right_size)
    larger = max(left_size, right_size)
    if smaller / larger < threshold:
        return None
    shared = _shared_fingerprint_count(left.fingerprints, right.fingerprints)
    score = _jaccard_from_sizes(shared, left_size, right_size)
    if score < threshold:
        return None
    return NearDuplicatePair(
        left_file_id=left.input.file_id,
        right_file_id=right.input.file_id,
        similarity_score=score,
        shared_fingerprint_count=shared,
        left_fingerprint_count=left_size,
        right_fingerprint_count=right_size,
    )


def _collect_pairs_in_items(
    items: Sequence[_PreparedFile],
    *,
    exact_group_by_file_id: Mapping[str, str],
    threshold: float,
    max_bucket_items: int,
    max_band_fanout: int,
    max_jaccard_checks: int | None,
    checks_so_far: int,
) -> tuple[list[NearDuplicatePair], int]:
    if len(items) < 2:
        return [], checks_so_far

    bucket_items = _cap_bucket_items(items, max_bucket_items)
    fp_to_items = _fingerprint_index(bucket_items, max_band_fanout)
    max_candidates_per_file = max(max_band_fanout * 3, 64)
    seen: set[tuple[str, str]] = set()
    accepted: list[NearDuplicatePair] = []
    for left in sorted(bucket_items, key=lambda item: item.input.file_id):
        left_id = left.input.file_id
        for right in _candidate_map_for_left(left, fp_to_items, max_candidates_per_file).values():
            pair_key = (left_id, right.input.file_id)
            if pair_key in seen:
                continue
            seen.add(pair_key)
            checks_so_far += 1
            if max_jaccard_checks is not None and checks_so_far > max_jaccard_checks:
                return accepted, checks_so_far
            pair = _maybe_near_pair(
                left, right, exact_group_by_file_id=exact_group_by_file_id, threshold=threshold
            )
            if pair is not None:
                accepted.append(pair)
    return accepted, checks_so_far


def find_near_duplicate_groups(
    files: Sequence[NearDuplicateInput],
    *,
    exact_group_by_file_id: Mapping[str, str],
    near_batch_id: str,
    threshold: float = NEAR_DUP_THRESHOLD,
    large_library: bool = False,
) -> NearDuplicateResult:
    prepared: list[_PreparedFile] = []
    skipped = 0
    for file_input in files:
        ready = _prepare_file(file_input)
        if ready is None:
            skipped += 1
        else:
            prepared.append(ready)
    return find_near_duplicate_groups_from_prepared(
        prepared,
        skipped=skipped,
        exact_group_by_file_id=exact_group_by_file_id,
        near_batch_id=near_batch_id,
        threshold=threshold,
        large_library=large_library,
    )


def _group_prepared_by_family_bucket(
    prepared: Sequence[_PreparedFile],
) -> dict[str, dict[int, list[_PreparedFile]]]:
    by_family_bucket: dict[str, dict[int, list[_PreparedFile]]] = defaultdict(lambda: defaultdict(list))
    for prepared_file in prepared:
        by_family_bucket[prepared_file.family][prepared_file.length_bucket].append(prepared_file)
    return by_family_bucket


def _bucket_items_for_pairing(
    buckets: dict[int, list[_PreparedFile]],
    left_bucket: int,
    right_bucket: int,
) -> list[_PreparedFile]:
    if left_bucket == right_bucket:
        return buckets[left_bucket]
    left_items = buckets[left_bucket]
    right_items = buckets[right_bucket]
    return list({item.input.file_id: item for item in (*left_items, *right_items)}.values())


def _collect_near_pairs(
    by_family_bucket: dict[str, dict[int, list[_PreparedFile]]],
    *,
    exact_group_by_file_id: Mapping[str, str],
    threshold: float,
    max_bucket_items: int,
    max_band_fanout: int,
    max_jaccard_checks: int | None,
    bucket_adjacency: int,
) -> tuple[list[NearDuplicatePair], int]:
    candidate_pair_count = 0
    accepted_pairs: list[NearDuplicatePair] = []
    checks_so_far = 0
    for family in sorted(by_family_bucket.keys()):
        buckets = by_family_bucket[family]
        bucket_indices = sorted(buckets.keys())
        for left_bucket in bucket_indices:
            for right_bucket in bucket_indices:
                if abs(left_bucket - right_bucket) > bucket_adjacency:
                    continue
                bucket_items = _bucket_items_for_pairing(buckets, left_bucket, right_bucket)
                pairs, checks_so_far = _collect_pairs_in_items(
                    bucket_items,
                    exact_group_by_file_id=exact_group_by_file_id,
                    threshold=threshold,
                    max_bucket_items=max_bucket_items,
                    max_band_fanout=max_band_fanout,
                    max_jaccard_checks=max_jaccard_checks,
                    checks_so_far=checks_so_far,
                )
                candidate_pair_count += len(pairs)
                accepted_pairs.extend(pairs)
                if max_jaccard_checks is not None and checks_so_far >= max_jaccard_checks:
                    return accepted_pairs, candidate_pair_count
    return accepted_pairs, candidate_pair_count


def _build_near_duplicate_groups(
    accepted_pairs: list[NearDuplicatePair],
    prepared: Sequence[_PreparedFile],
    *,
    near_batch_id: str,
) -> list[NearDuplicateGroup]:
    accepted_pairs.sort(key=lambda pair: (pair.left_file_id, pair.right_file_id))
    union = _UnionFind([prepared_file.input.file_id for prepared_file in prepared])
    for pair in accepted_pairs:
        union.union(pair.left_file_id, pair.right_file_id)

    components: dict[str, list[str]] = defaultdict(list)
    for prepared_file in prepared:
        components[union.find(prepared_file.input.file_id)].append(prepared_file.input.file_id)

    component_lists = [sorted(members) for members in components.values() if len(members) >= 2]
    component_lists.sort(key=lambda members: members[0])

    pairs_by_root: dict[str, list[NearDuplicatePair]] = defaultdict(list)
    for pair in accepted_pairs:
        pairs_by_root[union.find(pair.left_file_id)].append(pair)

    groups: list[NearDuplicateGroup] = []
    for cluster_index, member_ids in enumerate(component_lists):
        cluster_pairs = pairs_by_root.get(union.find(member_ids[0]), [])
        max_similarity = max((pair.similarity_score for pair in cluster_pairs), default=0.0)
        groups.append(
            NearDuplicateGroup(
                group_id=f"near:{near_batch_id}:{cluster_index}",
                member_file_ids=tuple(member_ids),
                pairs=tuple(cluster_pairs),
                max_similarity=max_similarity,
            )
        )
    return groups


def find_near_duplicate_groups_from_prepared(
    prepared: Sequence[_PreparedFile],
    *,
    skipped: int,
    exact_group_by_file_id: Mapping[str, str],
    near_batch_id: str,
    threshold: float,
    large_library: bool,
) -> NearDuplicateResult:
    by_family_bucket = _group_prepared_by_family_bucket(prepared)
    max_bucket_items, max_band_fanout, max_jaccard_checks, bucket_adjacency = _near_dup_limits(
        len(prepared),
        large_library=large_library,
    )
    accepted_pairs, candidate_pair_count = _collect_near_pairs(
        by_family_bucket,
        exact_group_by_file_id=exact_group_by_file_id,
        threshold=threshold,
        max_bucket_items=max_bucket_items,
        max_band_fanout=max_band_fanout,
        max_jaccard_checks=max_jaccard_checks,
        bucket_adjacency=bucket_adjacency,
    )
    bucket_map = {
        (family, bucket): items
        for family, bucket_dict in by_family_bucket.items()
        for bucket, items in bucket_dict.items()
    }
    groups = _build_near_duplicate_groups(
        accepted_pairs, prepared, near_batch_id=near_batch_id
    )
    stats = NearDuplicateStats(
        eligible_file_count=len(prepared),
        skipped_file_count=skipped,
        bucket_count=len(bucket_map),
        candidate_pair_count=candidate_pair_count,
        accepted_pair_count=len(accepted_pairs),
        group_count=len(groups),
    )
    return NearDuplicateResult(
        near_batch_id=near_batch_id,
        algorithm_version=ALGORITHM_VERSION,
        threshold=threshold,
        groups=tuple(groups),
        stats=stats,
    )
