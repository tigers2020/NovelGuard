"""
Union-Find (DSU) 자료구조

중복 그룹 형성 시 일관성을 보장하기 위한 Union-Find 자료구조입니다.
"""

from typing import Dict, List


class UnionFind:
    """Union-Find (Disjoint Set Union) 자료구조.
    
    중복 관계는 그래프입니다. A==B, B포함C → A/B/C가 한 그룹.
    Union-Find로 중복 그룹 분리/중첩을 방지합니다.
    
    Attributes:
        parent: 각 노드의 부모 노드
        rank: 각 노드의 랭크 (경로 압축 최적화용)
    """
    
    def __init__(self, n: int) -> None:
        """UnionFind 초기화.
        
        Args:
            n: 노드 개수
        """
        self.parent = list(range(n))
        self.rank = [0] * n
    
    def find(self, x: int) -> int:
        """루트 노드를 찾습니다 (경로 압축).
        
        Args:
            x: 노드 인덱스
        
        Returns:
            루트 노드 인덱스
        """
        if self.parent[x] != x:
            # 경로 압축: 부모를 루트로 직접 연결
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]
    
    def union(self, x: int, y: int) -> None:
        """두 집합을 합칩니다.
        
        Args:
            x: 첫 번째 노드 인덱스
            y: 두 번째 노드 인덱스
        """
        root_x = self.find(x)
        root_y = self.find(y)
        
        if root_x == root_y:
            return  # 이미 같은 집합
        
        # 랭크 기반 병합 (균형 트리 유지)
        if self.rank[root_x] < self.rank[root_y]:
            self.parent[root_x] = root_y
        elif self.rank[root_x] > self.rank[root_y]:
            self.parent[root_y] = root_x
        else:
            self.parent[root_y] = root_x
            self.rank[root_x] += 1
    
    def get_groups(self) -> Dict[int, List[int]]:
        """그룹별 인덱스 리스트를 반환합니다.
        
        Returns:
            {루트_인덱스: [그룹_인덱스_리스트]} 딕셔너리
        """
        groups: Dict[int, List[int]] = {}
        for i in range(len(self.parent)):
            root = self.find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(i)
        return groups
    
    def get_group_count(self) -> int:
        """그룹 개수를 반환합니다.
        
        Returns:
            그룹 개수
        """
        roots = set()
        for i in range(len(self.parent)):
            roots.add(self.find(i))
        return len(roots)

