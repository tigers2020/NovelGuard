"""중복 그룹 정규화 유틸리티.

겹치는 중복 그룹들을 Union-Find 알고리즘을 사용하여 병합합니다.
같은 파일이 여러 그룹에 속하는 경우, 연결된 컴포넌트로 병합하여
1 file_id → 1 group_id를 보장합니다.
"""
from collections import defaultdict
from typing import Any, Optional, TYPE_CHECKING

from application.dto.duplicate_group_result import DuplicateGroupResult

if TYPE_CHECKING:
    from gui.models.file_data_store import FileDataStore


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
        self._rank: dict[int, int] = {x: 0 for x in elements}
    
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


def normalize_duplicate_groups(
    groups: list[DuplicateGroupResult],
    file_data_store: Optional["FileDataStore"] = None
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
    
    # 1. Union-Find 초기화: 모든 file_id를 독립적인 집합으로 시작
    all_file_ids: set[int] = set()
    for group in groups:
        all_file_ids.update(group.file_ids)
    
    if not all_file_ids:
        return []
    
    uf = _UnionFind(all_file_ids)
    
    # 2. 각 그룹 처리: 첫 file_id를 기준으로 나머지 file_id들과 union
    for group in groups:
        if len(group.file_ids) < 2:
            continue
        
        # 첫 file_id를 기준으로 나머지와 union
        first_id = group.file_ids[0]
        for file_id in group.file_ids[1:]:
            uf.union(first_id, file_id)
    
    # 3. Connected Components 추출
    components = uf.get_components()
    
    # 4. 각 컴포넌트를 하나의 그룹으로 병합
    merged_groups: list[DuplicateGroupResult] = []
    next_group_id = max((g.group_id for g in groups), default=0) + 1
    
    # 원본 그룹에서 file_id별로 어떤 그룹에 속했는지 추적 (keeper 선택용)
    file_id_to_original_groups: dict[int, list[DuplicateGroupResult]] = defaultdict(list)
    for group in groups:
        for file_id in group.file_ids:
            file_id_to_original_groups[file_id].append(group)
    
    for root_id, component_file_ids in components.items():
        if len(component_file_ids) < 2:
            # 단일 파일은 그룹으로 만들지 않음 (정규화 대상 아님)
            continue
        
        # 이 컴포넌트에 포함된 원본 그룹들 수집
        component_original_groups: list[DuplicateGroupResult] = []
        component_file_ids_set = set(component_file_ids)
        for group in groups:
            # 그룹의 file_id들이 이 컴포넌트와 겹치면 포함
            if component_file_ids_set.intersection(set(group.file_ids)):
                component_original_groups.append(group)
        
        # Merged group 생성
        merged_group = _merge_group_components(
            component_file_ids,
            component_original_groups,
            next_group_id,
            file_data_store,
            file_id_to_original_groups
        )
        merged_groups.append(merged_group)
        next_group_id += 1
    
    return merged_groups


def _merge_group_components(
    component_file_ids: list[int],
    original_groups: list[DuplicateGroupResult],
    new_group_id: int,
    file_data_store: Optional["FileDataStore"],
    file_id_to_original_groups: dict[int, list[DuplicateGroupResult]]
) -> DuplicateGroupResult:
    """컴포넌트를 하나의 그룹으로 병합합니다.
    
    Args:
        component_file_ids: 컴포넌트에 포함된 file_id 리스트.
        original_groups: 이 컴포넌트와 겹치는 원본 그룹들.
        new_group_id: 새로운 그룹 ID.
        file_data_store: 파일 데이터 저장소.
        file_id_to_original_groups: file_id별 원본 그룹 매핑.
    
    Returns:
        병합된 DuplicateGroupResult.
    """
    # 1. duplicate_types 수집
    duplicate_types = list(set(g.duplicate_type for g in original_groups))
    
    # 2. confidence의 max 값
    max_confidence = max((g.confidence for g in original_groups), default=0.0)
    
    # 3. evidence 병합: 원본 evidence들을 리스트로 보존
    merged_evidence: dict[str, Any] = {
        "duplicate_types": duplicate_types,
        "merged_evidence": [g.evidence.copy() if g.evidence else {} for g in original_groups],
        "original_groups_count": len(original_groups)
    }
    
    # 4. Keeper 선택
    keeper_id = _select_keeper(
        component_file_ids,
        original_groups,
        file_data_store,
        file_id_to_original_groups
    )
    
    # 5. DuplicateGroupResult 생성
    merged_result = DuplicateGroupResult(
        group_id=new_group_id,
        duplicate_type="merged",
        file_ids=sorted(component_file_ids),  # 정렬하여 결정성 보장
        recommended_keeper_id=keeper_id,
        evidence=merged_evidence,
        confidence=max_confidence
    )
    
    return merged_result


def _select_keeper(
    component_file_ids: list[int],
    original_groups: list[DuplicateGroupResult],
    file_data_store: Optional["FileDataStore"],
    file_id_to_original_groups: dict[int, list[DuplicateGroupResult]]
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
        file_id_to_original_groups: file_id별 원본 그룹 매핑 (사용하지 않음, original_groups 사용).
    
    Returns:
        선택된 keeper file_id. 선택 불가능하면 None.
    """
    if not file_data_store:
        # file_data_store가 없으면 첫 번째 file_id 반환
        return component_file_ids[0] if component_file_ids else None
    
    # 1순위: 원본 그룹에서 is_canonical로 가장 많이 선택된 파일
    canonical_counts: dict[int, int] = defaultdict(int)
    for group in original_groups:
        if group.recommended_keeper_id and group.recommended_keeper_id in component_file_ids:
            canonical_counts[group.recommended_keeper_id] += 1
    
    if canonical_counts:
        max_count = max(canonical_counts.values())
        candidates = [fid for fid, count in canonical_counts.items() if count == max_count]
        if len(candidates) == 1:
            return candidates[0]
        # 여러 후보가 있으면 다음 단계로
        component_file_ids = candidates
    
    # 2순위: 가장 큰 size
    size_map: dict[int, int] = {}
    for file_id in component_file_ids:
        file_data = file_data_store.get_file(file_id)
        if file_data:
            size_map[file_id] = file_data.size
    
    if size_map:
        max_size = max(size_map.values())
        candidates = [fid for fid in component_file_ids if size_map.get(fid, 0) == max_size]
        if len(candidates) == 1:
            return candidates[0]
        # 여러 후보가 있으면 다음 단계로
        component_file_ids = candidates
    
    # 3순위: 가장 최신 mtime
    mtime_map: dict[int, Any] = {}
    for file_id in component_file_ids:
        file_data = file_data_store.get_file(file_id)
        if file_data:
            mtime_map[file_id] = file_data.mtime
    
    if mtime_map:
        max_mtime = max(mtime_map.values())
        candidates = [fid for fid in component_file_ids if mtime_map.get(fid) == max_mtime]
        if len(candidates) == 1:
            return candidates[0]
        # 여러 후보가 있으면 다음 단계로
        component_file_ids = candidates
    
    # 4순위: path 사전순 (완전 결정성 보장)
    path_map: dict[int, str] = {}
    for file_id in component_file_ids:
        file_data = file_data_store.get_file(file_id)
        if file_data:
            path_map[file_id] = str(file_data.path)
    
    if path_map:
        # path를 정렬하여 가장 작은 것 선택
        sorted_paths = sorted(path_map.items(), key=lambda x: x[1])
        return sorted_paths[0][0]
    
    # 모든 방법이 실패하면 첫 번째 file_id 반환
    return component_file_ids[0] if component_file_ids else None


def validate_normalized_groups(
    groups: list[DuplicateGroupResult],
    file_data_store: Optional["FileDataStore"] = None
) -> list[str]:
    """정규화된 그룹들을 검증합니다.
    
    Args:
        groups: 검증할 그룹 리스트.
        file_data_store: 파일 데이터 저장소 (path 유일성 검증용).
    
    Returns:
        검증 오류 메시지 리스트. 오류가 없으면 빈 리스트.
    """
    errors: list[str] = []
    
    # file_id -> group_id 매핑
    file_id_to_group_id: dict[int, int] = {}
    
    for group in groups:
        group_id = group.group_id
        
        # 검증 1: file_count는 DuplicateGroupResult에 직접 필드가 없으므로 생략
        # (JSON 직렬화 시 len(file_ids)로 계산됨)
        
        # 검증 2: files는 file_id 기준 unique (중복 file_id 없음)
        file_ids_set = set(group.file_ids)
        if len(file_ids_set) != len(group.file_ids):
            errors.append(
                f"Group {group_id}: duplicate file_ids found in file_ids list"
            )
        
        # 검증 3: 각 file_id가 최대 1개 group_id만 가짐
        for file_id in group.file_ids:
            if file_id in file_id_to_group_id:
                errors.append(
                    f"File {file_id} appears in multiple groups: "
                    f"{file_id_to_group_id[file_id]} and {group_id}"
                )
            else:
                file_id_to_group_id[file_id] = group_id
        
        # 검증 4: recommended_keeper_id가 해당 그룹의 files 목록에 존재
        if group.recommended_keeper_id is not None:
            if group.recommended_keeper_id not in group.file_ids:
                errors.append(
                    f"Group {group_id}: recommended_keeper_id ({group.recommended_keeper_id}) "
                    f"not in file_ids"
                )
        
        # 검증 5: 컴포넌트 내 file_id의 path는 모두 서로 달라야 함 (file_data_store가 있는 경우)
        if file_data_store and len(group.file_ids) > 1:
            paths: list[str] = []
            for file_id in group.file_ids:
                file_data = file_data_store.get_file(file_id)
                if file_data:
                    path_str = str(file_data.path)
                    if path_str in paths:
                        errors.append(
                            f"Group {group_id}: duplicate path found for file_id {file_id}: {path_str}"
                        )
                    paths.append(path_str)
    
    return errors
