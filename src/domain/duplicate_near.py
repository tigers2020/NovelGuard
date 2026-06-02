"""Near duplicate detection via normalized text n-gram fingerprints (PR-19)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

ALGORITHM_VERSION = "near-ngram-v1"
NEAR_DUP_THRESHOLD = 0.82
MIN_NORMALIZED_CHARS = 200
MAX_NORMALIZED_CHARS = 512 * 1024
LENGTH_RATIO_THRESHOLD = 0.60
WORD_NGRAM_SIZE = 5
CHAR_NGRAM_SIZE = 5
MAX_FINGERPRINTS_PER_FILE = 512
_FINGERPRINT_BAND_HEX_LEN = 4

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
    normalized: str
    norm_len: int
    fingerprints: frozenset[str]
    bands: frozenset[str]
    family: str
    length_bucket: int


def normalize_text_for_near_dup(text: str) -> str:
    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _fingerprint_token(gram: str) -> str:
    digest = hashlib.sha256(gram.encode("utf-8")).hexdigest()
    return digest[:16]


def fingerprint_set(normalized: str) -> frozenset[str]:
    tokens = normalized.split()
    grams: list[str] = []
    if len(tokens) >= WORD_NGRAM_SIZE:
        for index in range(len(tokens) - WORD_NGRAM_SIZE + 1):
            grams.append(" ".join(tokens[index : index + WORD_NGRAM_SIZE]))
    elif len(normalized) >= CHAR_NGRAM_SIZE:
        for index in range(len(normalized) - CHAR_NGRAM_SIZE + 1):
            grams.append(normalized[index : index + CHAR_NGRAM_SIZE])
    else:
        return frozenset()

    unique = sorted({_fingerprint_token(gram) for gram in grams})
    if len(unique) > MAX_FINGERPRINTS_PER_FILE:
        unique = unique[:MAX_FINGERPRINTS_PER_FILE]
    return frozenset(unique)


def jaccard_similarity(left: frozenset[str], right: frozenset[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


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


def _fingerprint_bands(fingerprints: frozenset[str]) -> frozenset[str]:
    return frozenset(fp[:_FINGERPRINT_BAND_HEX_LEN] for fp in fingerprints)


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
        normalized=normalized,
        norm_len=norm_len,
        fingerprints=fingerprints,
        bands=_fingerprint_bands(fingerprints),
        family=family,
        length_bucket=length_bucket(norm_len),
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


def find_near_duplicate_groups(
    files: Sequence[NearDuplicateInput],
    *,
    exact_group_by_file_id: Mapping[str, str],
    near_batch_id: str,
    threshold: float = NEAR_DUP_THRESHOLD,
) -> NearDuplicateResult:
    prepared: list[_PreparedFile] = []
    skipped = 0
    for file_input in files:
        ready = _prepare_file(file_input)
        if ready is None:
            skipped += 1
        else:
            prepared.append(ready)

    by_family_bucket: dict[str, dict[int, list[_PreparedFile]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for prepared_file in prepared:
        by_family_bucket[prepared_file.family][prepared_file.length_bucket].append(prepared_file)

    candidate_pair_count = 0
    accepted_pairs: list[NearDuplicatePair] = []

    for family in sorted(by_family_bucket.keys()):
        buckets = by_family_bucket[family]
        bucket_indices = sorted(buckets.keys())
        for left_bucket in bucket_indices:
            for right_bucket in bucket_indices:
                if abs(left_bucket - right_bucket) > 1:
                    continue
                left_items = buckets[left_bucket]
                right_items = buckets[right_bucket]
                for left in left_items:
                    for right in right_items:
                        if left.input.file_id >= right.input.file_id:
                            continue
                        if not length_ratio_ok(left.norm_len, right.norm_len):
                            continue
                        if not left.bands & right.bands:
                            continue

                        candidate_pair_count += 1
                        if _should_skip_pair(
                            left, right, exact_group_by_file_id=exact_group_by_file_id
                        ):
                            continue

                        score = jaccard_similarity(left.fingerprints, right.fingerprints)
                        if score < threshold:
                            continue

                        accepted_pairs.append(
                            NearDuplicatePair(
                                left_file_id=left.input.file_id,
                                right_file_id=right.input.file_id,
                                similarity_score=score,
                                shared_fingerprint_count=len(
                                    left.fingerprints & right.fingerprints
                                ),
                                left_fingerprint_count=len(left.fingerprints),
                                right_fingerprint_count=len(right.fingerprints),
                            )
                        )

    bucket_map = {
        (family, bucket): items
        for family, bucket_dict in by_family_bucket.items()
        for bucket, items in bucket_dict.items()
    }

    accepted_pairs.sort(key=lambda pair: (pair.left_file_id, pair.right_file_id))

    union = _UnionFind([prepared_file.input.file_id for prepared_file in prepared])
    for pair in accepted_pairs:
        union.union(pair.left_file_id, pair.right_file_id)

    components: dict[str, list[str]] = defaultdict(list)
    for prepared_file in prepared:
        components[union.find(prepared_file.input.file_id)].append(prepared_file.input.file_id)

    component_lists = [sorted(members) for members in components.values() if len(members) >= 2]
    component_lists.sort(key=lambda members: members[0])

    groups: list[NearDuplicateGroup] = []
    for cluster_index, member_ids in enumerate(component_lists):
        member_set = set(member_ids)
        cluster_pairs: list[NearDuplicatePair] = []
        max_similarity = 0.0
        for pair in accepted_pairs:
            if pair.left_file_id in member_set and pair.right_file_id in member_set:
                cluster_pairs.append(pair)
                max_similarity = max(max_similarity, pair.similarity_score)

        group_id = f"near:{near_batch_id}:{cluster_index}"
        groups.append(
            NearDuplicateGroup(
                group_id=group_id,
                member_file_ids=tuple(member_ids),
                pairs=tuple(cluster_pairs),
                max_similarity=max_similarity,
            )
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
