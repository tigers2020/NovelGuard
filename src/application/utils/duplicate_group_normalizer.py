"""중복 그룹 정규화 유틸리티.

겹치는 중복 그룹들을 Union-Find 알고리즘을 사용하여 병합합니다.
같은 파일이 여러 그룹에 속하는 경우, 연결된 컴포넌트로 병합하여
1 file_id → 1 group_id를 보장합니다.
"""

from collections import defaultdict
from typing import Any, Optional

from application.dto.duplicate_group_result import DuplicateGroupResult
from application.ports.file_data_store import IFileDataStore


class _UnionFind:
    """Union-Find (Disjoint Set) 자료구조.

    경로 압축과 union-by-rank를 사용하여 효율적인 집합 연산을 제공합니다.
    """

    def __init__(self, elements: set[int]) -> None:
        """Union-Find 초기화.

        Args:
            elements: 초기 요소 집합.
        """
        self._parent: dict[int, int] = {x: x for x in elements}
        self._rank: dict[int, int] = dict.fromkeys(elements, 0)

    def find(self, x: int) -> int:
        """요소 x의 루트를 찾습니다 (경로 압축).

        Args:
            x: 찾을 요소.

        Returns:
            요소 x의 루트.
        """
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])  # 경로 압축
        return self._parent[x]

    def union(self, x: int, y: int) -> None:
        """두 요소를 같은 집합으로 병합 (union-by-rank).

        Args:
            x: 첫 번째 요소.
            y: 두 번째 요소.
        """
        root_x = self.find(x)
        root_y = self.find(y)

        if root_x == root_y:
            return  # 이미 같은 집합

        # union-by-rank: rank가 낮은 트리를 높은 트리에 연결
        if self._rank[root_x] < self._rank[root_y]:
            self._parent[root_x] = root_y
        elif self._rank[root_x] > self._rank[root_y]:
            self._parent[root_y] = root_x
        else:
            self._parent[root_y] = root_x
            self._rank[root_x] += 1

    def get_components(self) -> dict[int, list[int]]:
        """모든 연결 요소를 반환.

        Returns:
            {root_id: [component_file_ids]} 딕셔너리.
        """
        components: dict[int, list[int]] = defaultdict(list)
        for element in self._parent:
            root = self.find(element)
            components[root].append(element)
        return dict(components)


def _all_file_ids_from_groups(groups: list[DuplicateGroupResult]) -> set[int]:
    """그룹 목록에서 모든 file_id 집합을 반환합니다."""
    result: set[int] = set()
    for group in groups:
        result.update(group.file_ids)
    return result


def _build_file_id_to_original_groups(
    groups: list[DuplicateGroupResult],
) -> dict[int, list[DuplicateGroupResult]]:
    """file_id별 원본 그룹 목록을 구합니다 (keeper 선택용)."""
    mapping: dict[int, list[DuplicateGroupResult]] = defaultdict(list)
    for group in groups:
        for file_id in group.file_ids:
            mapping[file_id].append(group)
    return mapping


def _collect_component_original_groups(
    component_file_ids: list[int],
    file_id_to_original_groups: dict[int, list[DuplicateGroupResult]],
) -> list[DuplicateGroupResult]:
    """컴포넌트에 포함된 원본 그룹들을 중복 없이 수집합니다."""
    seen_group_ids: set[int] = set()
    component_original_groups: list[DuplicateGroupResult] = []
    for fid in component_file_ids:
        for g in file_id_to_original_groups[fid]:
            gid = id(g)
            if gid not in seen_group_ids:
                seen_group_ids.add(gid)
                component_original_groups.append(g)
    return component_original_groups


def normalize_duplicate_groups(
    groups: list[DuplicateGroupResult], file_data_store: Optional[IFileDataStore] = None
) -> list[DuplicateGroupResult]:
    """중복 그룹들을 정규화하여 겹침을 제거합니다.

    Union-Find 알고리즘을 사용하여 같은 파일이 여러 그룹에 속하는 경우
    연결된 컴포넌트로 병합합니다. 결과적으로 1 file_id → 1 group_id를 보장합니다.

    Args:
        groups: 정규화할 중복 그룹 리스트 (겹침 가능).
        file_data_store: 파일 데이터 저장소 (keeper 선택을 위해 필요).

    Returns:
        정규화된 중복 그룹 리스트 (겹침 없음).

    Raises:
        ValueError: file_data_store가 None이고 keeper 선택이 필요한 경우.
    """
    if not groups:
        return []
    all_file_ids = _all_file_ids_from_groups(groups)
    if not all_file_ids:
        return []

    uf = _UnionFind(all_file_ids)
    for group in groups:
        if len(group.file_ids) < 2:
            continue
        first_id = group.file_ids[0]
        for file_id in group.file_ids[1:]:
            uf.union(first_id, file_id)

    components = uf.get_components()
    file_id_to_original_groups = _build_file_id_to_original_groups(groups)
    merged_groups: list[DuplicateGroupResult] = []
    next_group_id = max((g.group_id for g in groups), default=0) + 1

    for root_id, component_file_ids in components.items():
        if len(component_file_ids) < 2:
            continue
        component_original_groups = _collect_component_original_groups(
            component_file_ids, file_id_to_original_groups
        )
        merged_group = _merge_group_components(
            component_file_ids,
            component_original_groups,
            next_group_id,
            file_data_store,
        )
        merged_groups.append(merged_group)
        next_group_id += 1

    return merged_groups


def _merge_group_components(
    component_file_ids: list[int],
    original_groups: list[DuplicateGroupResult],
    new_group_id: int,
    file_data_store: Optional[IFileDataStore],
) -> DuplicateGroupResult:
    """컴포넌트를 하나의 그룹으로 병합합니다.

    Args:
        component_file_ids: 컴포넌트에 포함된 file_id 리스트.
        original_groups: 이 컴포넌트와 겹치는 원본 그룹들.
        new_group_id: 새로운 그룹 ID.
        file_data_store: 파일 데이터 저장소.

    Returns:
        병합된 DuplicateGroupResult.
    """
    # 1. duplicate_types 수집
    duplicate_types = list({g.duplicate_type for g in original_groups})

    # 2. confidence의 max 값
    max_confidence = max((g.confidence for g in original_groups), default=0.0)

    # 3. evidence 병합: 원본 evidence들을 리스트로 보존
    merged_evidence: dict[str, Any] = {
        "duplicate_types": duplicate_types,
        "merged_evidence": [g.evidence.copy() if g.evidence else {} for g in original_groups],
        "original_groups_count": len(original_groups),
    }

    # 4. Keeper 선택
    keeper_id = _select_keeper(
        component_file_ids,
        original_groups,
        file_data_store,
    )

    # 5. DuplicateGroupResult 생성
    merged_result = DuplicateGroupResult(
        group_id=new_group_id,
        duplicate_type="merged",
        file_ids=sorted(component_file_ids),  # 정렬하여 결정성 보장
        recommended_keeper_id=keeper_id,
        evidence=merged_evidence,
        confidence=max_confidence,
    )

    return merged_result


def _narrow_by_canonical(
    component_file_ids: list[int],
    original_groups: list[DuplicateGroupResult],
) -> tuple[list[int], Optional[int]]:
    """원본 그룹의 recommended_keeper_id 투표로 후보를 좁힙니다. 단일 후보면 (_, keeper_id)."""
    canonical_counts: dict[int, int] = defaultdict(int)
    for group in original_groups:
        if group.recommended_keeper_id and group.recommended_keeper_id in component_file_ids:
            canonical_counts[group.recommended_keeper_id] += 1
    if not canonical_counts:
        return component_file_ids, None
    max_count = max(canonical_counts.values())
    candidates = [fid for fid, count in canonical_counts.items() if count == max_count]
    if len(candidates) == 1:
        return candidates, candidates[0]
    return candidates, None


def _narrow_by_size(
    component_file_ids: list[int],
    file_data_by_id: dict[int, Any],
) -> tuple[list[int], Optional[int]]:
    """가장 큰 size 기준으로 후보를 좁힙니다."""
    size_map = {fid: data.size for fid, data in file_data_by_id.items()}
    if not size_map:
        return component_file_ids, None
    max_size = max(size_map.values())
    candidates = [fid for fid in component_file_ids if size_map.get(fid, 0) == max_size]
    if len(candidates) == 1:
        return candidates, candidates[0]
    return candidates, None


def _narrow_by_mtime(
    component_file_ids: list[int],
    file_data_by_id: dict[int, Any],
) -> tuple[list[int], Optional[int]]:
    """가장 최신 mtime 기준으로 후보를 좁힙니다."""
    mtime_map = {
        fid: file_data_by_id[fid].mtime for fid in component_file_ids if fid in file_data_by_id
    }
    if not mtime_map:
        return component_file_ids, None
    max_mtime = max(mtime_map.values())
    candidates = [fid for fid in component_file_ids if mtime_map.get(fid) == max_mtime]
    if len(candidates) == 1:
        return candidates, candidates[0]
    return candidates, None


def _pick_by_path(
    component_file_ids: list[int],
    file_data_by_id: dict[int, Any],
) -> Optional[int]:
    """path 사전순으로 첫 번째 file_id를 반환합니다."""
    path_map = {
        fid: str(file_data_by_id[fid].path) for fid in component_file_ids if fid in file_data_by_id
    }
    if not path_map:
        return None
    sorted_paths = sorted(path_map.items(), key=lambda x: x[1])
    return sorted_paths[0][0]


def _select_keeper(
    component_file_ids: list[int],
    original_groups: list[DuplicateGroupResult],
    file_data_store: Optional[IFileDataStore],
) -> Optional[int]:
    """컴포넌트에서 keeper (대표 파일)를 선택합니다.

    Tie-break 규칙:
    1. 원본 그룹들에서 is_canonical로 가장 많이 선택된 파일
    2. 가장 큰 size
    3. 가장 최신 mtime
    4. path 사전순 (완전 결정성 보장)

    Args:
        component_file_ids: 컴포넌트에 포함된 file_id 리스트.
        original_groups: 원본 그룹들 (컴포넌트와 겹치는 그룹들).
        file_data_store: 파일 데이터 저장소.

    Returns:
        선택된 keeper file_id. 선택 불가능하면 None.
    """
    if not component_file_ids:
        return None
    if not file_data_store:
        return component_file_ids[0]

    candidates, single = _narrow_by_canonical(component_file_ids, original_groups)
    if single is not None:
        return single

    file_data_by_id = {fid: data for fid in candidates if (data := file_data_store.get_file(fid))}
    candidates, single = _narrow_by_size(candidates, file_data_by_id)
    if single is not None:
        return single
    candidates, single = _narrow_by_mtime(candidates, file_data_by_id)
    if single is not None:
        return single
    picked = _pick_by_path(candidates, file_data_by_id)
    return picked if picked is not None else candidates[0]


def _errors_duplicate_file_ids_in_group(group: DuplicateGroupResult) -> list[str]:
    """그룹 내 중복 file_id 검증 오류를 반환합니다."""
    if len({*group.file_ids}) == len(group.file_ids):
        return []
    return [f"Group {group.group_id}: duplicate file_ids found in file_ids list"]


def _errors_file_id_in_multiple_groups(
    group: DuplicateGroupResult,
    file_id_to_group_id: dict[int, int],
) -> list[str]:
    """file_id가 여러 그룹에 속하는지 검사하고, file_id_to_group_id를 갱신합니다. 오류 목록 반환."""
    errors: list[str] = []
    group_id = group.group_id
    for file_id in group.file_ids:
        if file_id in file_id_to_group_id:
            errors.append(
                f"File {file_id} appears in multiple groups: "
                f"{file_id_to_group_id[file_id]} and {group_id}"
            )
        else:
            file_id_to_group_id[file_id] = group_id
    return errors


def _errors_keeper_not_in_group(group: DuplicateGroupResult) -> list[str]:
    """recommended_keeper_id가 그룹 file_ids에 있는지 검증 오류를 반환합니다."""
    if group.recommended_keeper_id is None:
        return []
    if group.recommended_keeper_id in group.file_ids:
        return []
    return [
        f"Group {group.group_id}: recommended_keeper_id ({group.recommended_keeper_id}) "
        "not in file_ids"
    ]


def _errors_duplicate_paths_in_group(
    group: DuplicateGroupResult,
    file_data_store: IFileDataStore,
) -> list[str]:
    """그룹 내 동일 path 중복 검증 오류를 반환합니다."""
    if len(group.file_ids) < 2:
        return []
    paths_seen: set[str] = set()
    errors: list[str] = []
    for file_id in group.file_ids:
        file_data = file_data_store.get_file(file_id)
        if not file_data:
            continue
        path_str = str(file_data.path)
        if path_str in paths_seen:
            errors.append(
                f"Group {group.group_id}: duplicate path found for file_id {file_id}: {path_str}"
            )
        paths_seen.add(path_str)
    return errors


def validate_normalized_groups(
    groups: list[DuplicateGroupResult], file_data_store: Optional[IFileDataStore] = None
) -> list[str]:
    """정규화된 그룹들을 검증합니다.

    Args:
        groups: 검증할 그룹 리스트.
        file_data_store: 파일 데이터 저장소 (path 유일성 검증용).

    Returns:
        검증 오류 메시지 리스트. 오류가 없으면 빈 리스트.
    """
    errors: list[str] = []
    file_id_to_group_id: dict[int, int] = {}

    for group in groups:
        errors.extend(_errors_duplicate_file_ids_in_group(group))
        errors.extend(_errors_file_id_in_multiple_groups(group, file_id_to_group_id))
        errors.extend(_errors_keeper_not_in_group(group))
        if file_data_store:
            errors.extend(_errors_duplicate_paths_in_group(group, file_data_store))

    return errors
