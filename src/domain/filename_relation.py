"""Filename-based relation candidate detection (PR-20)."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from pathlib import PurePosixPath

from domain.models import FileRecord

ALGORITHM_VERSION = "relation-filename-v1"
MIN_STEM_CHARS = 4
MIN_GROUP_MEMBERS = 2
MAX_CHAPTER_GAP = 50
MIN_NON_GENERIC_TOKEN_LEN = 4
MIN_PARENT_PATH_TOKEN_LEN = 3

RELATION_KINDS_V1 = frozenset(
    {
        "same_title_series",
        "chapter_sequence",
        "version_variant",
    }
)

GENERIC_STEM_DENYLIST = frozenset(
    {
        "chapter",
        "chap",
        "ch",
        "episode",
        "ep",
        "part",
        "volume",
        "vol",
        "book",
        "text",
        "novel",
        "raw",
        "번역",
        "완결",
    }
)

_RELATION_KIND_PRIORITY = {
    "chapter_sequence": 0,
    "same_title_series": 1,
    "version_variant": 2,
}

_CONFIDENCE_BY_LABEL = {
    "high": 0.9,
    "medium": 0.7,
    "low": 0.4,
}

_CHAPTER_NUMERIC_RE = re.compile(
    r"\b(?:chapter|chap|ch|episode|ep|part|vol|volume)\s*(\d+)\b",
    re.IGNORECASE,
)
_VERSION_MARKER_RE = re.compile(
    r"\b(v\d+|rev(?:ised)?|complete|완결|번역|raw)\b",
    re.IGNORECASE,
)
_BARE_INTEGER_RE = re.compile(r"\b(\d+)\b")
_BRACKET_TAG_RE = re.compile(r"\[[^\]]*\]")
_SEPARATOR_RE = re.compile(r"[_\-\.\+,\s]+")


@dataclass(frozen=True, slots=True)
class FilenameRelationParse:
    original_name: str
    relative_path: str
    parent_path_tokens: tuple[str, ...]
    normalized_stem: str
    numeric_tokens: tuple[int, ...]
    version_markers: tuple[str, ...]
    non_generic_tokens: tuple[str, ...]

    @property
    def is_generic_only_stem(self) -> bool:
        tokens = _stem_tokens(self.normalized_stem)
        return bool(tokens) and all(token in GENERIC_STEM_DENYLIST for token in tokens)


@dataclass(frozen=True, slots=True)
class RelationGroup:
    group_id: str
    member_file_ids: tuple[str, ...]
    relation_kind: str
    confidence: float
    confidence_label: str
    normalized_stem: str
    normalized_names: tuple[str, ...]
    matched_tokens: tuple[str, ...]
    differing_tokens: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RelationDetectionStats:
    eligible_file_count: int
    skipped_file_count: int
    bucket_count: int
    group_count: int


@dataclass(frozen=True, slots=True)
class RelationDetectionResult:
    groups: tuple[RelationGroup, ...]
    stats: RelationDetectionStats


@dataclass(frozen=True, slots=True)
class _PreparedFile:
    record: FileRecord
    parse: FilenameRelationParse
    title_stem_key: str
    parent_dir: str


def normalize_filename_for_relation(name: str, *, relative_path: str) -> FilenameRelationParse:
    basename = name.strip()
    if "." in basename:
        basename = basename.rsplit(".", 1)[0]
    basename = _BRACKET_TAG_RE.sub(" ", basename)
    normalized = unicodedata.normalize("NFKC", basename)
    normalized = _SEPARATOR_RE.sub(" ", normalized).strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)

    numeric_tokens: list[int] = []
    version_markers: list[str] = []
    working = f" {normalized} "

    for match in _CHAPTER_NUMERIC_RE.finditer(working):
        numeric_tokens.append(int(match.group(1)))

    working = _CHAPTER_NUMERIC_RE.sub(_chapter_label_replacement, working)

    for match in _VERSION_MARKER_RE.finditer(working):
        marker = match.group(1).lower()
        if marker.startswith("v") and marker[1:].isdigit():
            version_markers.append(marker)
        else:
            version_markers.append(marker)
        working = working.replace(match.group(0), " ", 1)

    for match in _BARE_INTEGER_RE.finditer(working):
        numeric_tokens.append(int(match.group(1)))
        working = working.replace(match.group(0), " ", 1)

    stem = re.sub(r"\s+", " ", working).strip()
    stem_tokens = _stem_tokens(stem)
    non_generic = tuple(
        token for token in stem_tokens if token not in GENERIC_STEM_DENYLIST and len(token) >= 2
    )
    parent_tokens = _parent_path_tokens(relative_path)

    return FilenameRelationParse(
        original_name=name,
        relative_path=relative_path,
        parent_path_tokens=parent_tokens,
        normalized_stem=stem,
        numeric_tokens=tuple(numeric_tokens),
        version_markers=tuple(version_markers),
        non_generic_tokens=non_generic,
    )


def title_stem_key(normalized_stem: str) -> str | None:
    if len(normalized_stem) < MIN_STEM_CHARS:
        return None
    digest = hashlib.sha256(normalized_stem.encode("utf-8")).hexdigest()
    return digest[:16]


def detect_filename_relations(
    files: Sequence[FileRecord],
    *,
    exact_membership_by_file_id: Mapping[str, str],
    near_membership_by_file_id: Mapping[str, str],
    relation_batch_id: str,
    algorithm_version: str = ALGORITHM_VERSION,
) -> RelationDetectionResult:
    _ = algorithm_version
    prepared: list[_PreparedFile] = []
    skipped = 0
    for record in files:
        if not record.name.strip():
            skipped += 1
            continue
        parse = normalize_filename_for_relation(record.name, relative_path=record.relative_path)
        key = title_stem_key(parse.normalized_stem)
        if key is None:
            skipped += 1
            continue
        parent_dir = str(PurePosixPath(record.relative_path).parent)
        if parent_dir == ".":
            parent_dir = ""
        prepared.append(
            _PreparedFile(
                record=record,
                parse=parse,
                title_stem_key=key,
                parent_dir=parent_dir,
            )
        )

    buckets: dict[str, list[_PreparedFile]] = {}
    for item in prepared:
        buckets.setdefault(item.title_stem_key, []).append(item)

    raw_groups: list[tuple[tuple[str, str, str, str], RelationGroup]] = []
    for bucket_items in buckets.values():
        eligible = _filter_generic_strengthened(bucket_items)
        if len(eligible) < MIN_GROUP_MEMBERS:
            continue
        kind = _classify_bucket(eligible)
        if kind is None or kind not in RELATION_KINDS_V1:
            continue
        member_ids = tuple(sorted(item.record.id for item in eligible))
        if _should_suppress_group(
            member_ids, exact_membership_by_file_id, near_membership_by_file_id
        ):
            continue
        stem = eligible[0].parse.normalized_stem
        confidence_label = _confidence_label(kind, eligible)
        normalized_names = tuple(
            item.record.name for item in sorted(eligible, key=lambda x: x.record.id)
        )
        matched, differing = _evidence_tokens(eligible)
        cluster_key = (kind, stem, min(member_ids), _member_digest(member_ids))
        raw_groups.append(
            (
                cluster_key,
                RelationGroup(
                    group_id="",  # filled after sort
                    member_file_ids=member_ids,
                    relation_kind=kind,
                    confidence=_CONFIDENCE_BY_LABEL[confidence_label],
                    confidence_label=confidence_label,
                    normalized_stem=stem,
                    normalized_names=normalized_names,
                    matched_tokens=matched,
                    differing_tokens=differing,
                ),
            )
        )

    raw_groups.sort(key=lambda item: item[0])
    groups: list[RelationGroup] = []
    for index, (_, group) in enumerate(raw_groups):
        group_id = f"relation:{relation_batch_id}:{index}"
        groups.append(
            RelationGroup(
                group_id=group_id,
                member_file_ids=group.member_file_ids,
                relation_kind=group.relation_kind,
                confidence=group.confidence,
                confidence_label=group.confidence_label,
                normalized_stem=group.normalized_stem,
                normalized_names=group.normalized_names,
                matched_tokens=group.matched_tokens,
                differing_tokens=group.differing_tokens,
            )
        )

    stats = RelationDetectionStats(
        eligible_file_count=len(prepared),
        skipped_file_count=skipped,
        bucket_count=len(buckets),
        group_count=len(groups),
    )
    return RelationDetectionResult(groups=tuple(groups), stats=stats)


def _chapter_label_replacement(match: re.Match[str]) -> str:
    token = match.group(0).strip().lower()
    for label in ("chapter", "chap", "episode", "volume", "part"):
        if token.startswith(label):
            return f" {label} "
    if token.startswith("ch") and token[2:].isdigit():
        return " ch "
    if token.startswith("ep") and token[2:].isdigit():
        return " ep "
    if token.startswith("vol") and token[3:].isdigit():
        return " vol "
    return " "


def _stem_tokens(stem: str) -> tuple[str, ...]:
    return tuple(token for token in stem.split() if token)


def _parent_path_tokens(relative_path: str) -> tuple[str, ...]:
    parent = PurePosixPath(relative_path).parent
    if str(parent) == ".":
        return ()
    return tuple(part.lower() for part in parent.parts if part)


def _filter_generic_strengthened(items: list[_PreparedFile]) -> list[_PreparedFile]:
    if not items:
        return []
    if not all(item.parse.is_generic_only_stem for item in items):
        return items
    if _same_parent_directory(items):
        return items
    if _shared_non_generic_token(items):
        return items
    if _parent_path_overlap(items):
        return items
    return []


def _same_parent_directory(items: Sequence[_PreparedFile]) -> bool:
    dirs = {item.parent_dir for item in items}
    return len(dirs) == 1 and any(item.parent_dir for item in items)


def _shared_non_generic_token(items: Sequence[_PreparedFile]) -> bool:
    counts: dict[str, int] = {}
    for item in items:
        for token in item.parse.non_generic_tokens:
            if len(token) >= MIN_NON_GENERIC_TOKEN_LEN:
                counts[token] = counts.get(token, 0) + 1
                if counts[token] >= MIN_GROUP_MEMBERS:
                    return True
    return False


def _parent_path_overlap(items: Sequence[_PreparedFile]) -> bool:
    if len(items) < MIN_GROUP_MEMBERS:
        return False
    significant = [
        {
            token
            for token in item.parse.parent_path_tokens
            if len(token) >= MIN_PARENT_PATH_TOKEN_LEN and token not in GENERIC_STEM_DENYLIST
        }
        for item in items
    ]
    shared = set.intersection(*significant) if significant else set()
    return len(shared) >= 2


def _classify_bucket(items: Sequence[_PreparedFile]) -> str | None:
    numerics = [item.parse.numeric_tokens for item in items if item.parse.numeric_tokens]
    versions = {marker for item in items for marker in item.parse.version_markers}

    if len(items) >= MIN_GROUP_MEMBERS and numerics and _is_chapter_sequence(numerics):
        return "chapter_sequence"

    numeric_sets = {tokens for tokens in numerics if tokens}
    if len(items) >= MIN_GROUP_MEMBERS and len(numeric_sets) >= 2:
        return "same_title_series"
    if len(items) >= MIN_GROUP_MEMBERS and len(numerics) >= 2:
        return "same_title_series"

    if len(items) >= MIN_GROUP_MEMBERS and len(versions) >= 2:
        return "version_variant"

    version_only_stems = all(
        _stem_differs_only_by_version(item.parse.normalized_stem, items[0].parse.normalized_stem)
        or item.parse.version_markers
        for item in items
    )
    if len(items) >= MIN_GROUP_MEMBERS and len(versions) >= 1 and version_only_stems:
        return "version_variant"

    return None


def _is_chapter_sequence(numeric_lists: Sequence[tuple[int, ...]]) -> bool:
    first_numbers = sorted({nums[0] for nums in numeric_lists if nums})
    if len(first_numbers) < MIN_GROUP_MEMBERS:
        return False
    for left, right in pairwise(first_numbers):
        if right - left > MAX_CHAPTER_GAP:
            return False
    return True


def _stem_differs_only_by_version(left: str, right: str) -> bool:
    left_tokens = set(_stem_tokens(left)) - GENERIC_STEM_DENYLIST
    right_tokens = set(_stem_tokens(right)) - GENERIC_STEM_DENYLIST
    return left_tokens == right_tokens


def _confidence_label(kind: str, items: Sequence[_PreparedFile]) -> str:
    if kind == "version_variant":
        return "high"
    numerics = [item.parse.numeric_tokens for item in items if item.parse.numeric_tokens]
    if kind == "chapter_sequence":
        return "high"
    if kind == "same_title_series" and _is_chapter_sequence(numerics):
        return "high"
    return "medium"


def _evidence_tokens(items: Sequence[_PreparedFile]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    stems = {item.parse.normalized_stem for item in items}
    matched = tuple(sorted(set.intersection(*(set(_stem_tokens(stem)) for stem in stems))))
    differing: set[str] = set()
    for item in items:
        differing.update(str(n) for n in item.parse.numeric_tokens)
        differing.update(item.parse.version_markers)
    return matched, tuple(sorted(differing))


def _member_digest(member_ids: tuple[str, ...]) -> str:
    payload = "|".join(sorted(member_ids))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


def _should_suppress_group(
    member_ids: tuple[str, ...],
    exact_membership: Mapping[str, str],
    near_membership: Mapping[str, str],
) -> bool:
    if len(member_ids) < MIN_GROUP_MEMBERS:
        return True
    exact_groups = {
        exact_membership.get(file_id) for file_id in member_ids if file_id in exact_membership
    }
    if len(exact_groups) == 1 and None not in exact_groups and len(exact_groups) > 0:
        if all(file_id in exact_membership for file_id in member_ids):
            return True
    near_groups = {
        near_membership.get(file_id) for file_id in member_ids if file_id in near_membership
    }
    if len(near_groups) == 1 and None not in near_groups and len(near_groups) > 0:
        if all(file_id in near_membership for file_id in member_ids):
            return True
    return False
