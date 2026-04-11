# 리팩토링 보고서: sqlite_index_repository.py

> **우선순위**: P0-5 (최우선)  
> **파일**: `src/infrastructure/db/sqlite_index_repository.py`  
> **작성일**: 2025-01-11  
> **상태**: 분석 완료, 리팩토링 대기

---

## 1. 파일 개요 및 현황

### 1.1 기본 정보
- **LOC**: 498 lines
- **클래스 수**: 1개 (`SQLiteIndexRepository`)
- **메서드 수**: 약 10개
- **의존성**: sqlite3, DTOs, FileEntry

### 1.2 현재 구조
```python
class SQLiteIndexRepository:
    - _ensure_schema()              # 스키마 생성
    - _connect()                    # 커넥션 생성
    - start_run()                   # Run 시작
    - upsert_files()                # 파일 배치 저장
    - finalize_run()                # Run 완료
    - get_latest_run_id()           # 최신 Run ID
    - get_run_summary()             # Run 요약
    - get_ext_distribution()        # 확장자 분포
    - list_files()                  # 파일 목록 조회 (복잡한 쿼리)
    - close()                       # 리소스 정리
```

---

## 2. 문제점 분석

### 2.1 인프라 레이어 비대화 (Query + Mapper + Repository 혼재)
**현재 문제**:
- `SQLiteIndexRepository`가 **쿼리 생성 + 매핑 + 트랜잭션 관리**를 모두 담당
- `list_files()` 메서드가 복잡한 쿼리 구축 로직 포함 (lines 436-461)
- FileEntry 매핑 로직이 Repository 내부에 구현 (lines 469-481)
- SQL 쿼리가 문자열로 하드코딩되어 있음

**영향**:
- 테스트 어려움: 쿼리 로직을 독립적으로 테스트 불가
- 재사용성 부족: 쿼리 로직을 다른 Repository에서 사용 불가
- 유지보수성: SQL 수정 시 Repository 전체 수정 필요
- 성능 튜닝 어려움: 쿼리 로직이 분산되어 최적화 어려움

### 2.2 쿼리/매핑/트랜잭션 경계 불명확
**현재 문제**:
- 각 메서드가 커넥션 생성/관리를 직접 수행
- 쿼리 로직과 매핑 로직이 혼재
- 트랜잭션 경계가 메서드별로 다름

**영향**:
- 단일 책임 위반: Repository가 너무 많은 책임을 가짐
- 테스트 복잡도: 쿼리/매핑/트랜잭션을 분리해서 테스트 불가

---

## 3. 리팩토링 목표

### 3.1 핵심 목표
1. **Query 분리**: SQL 쿼리를 별도 클래스/함수로 추출
2. **Mapper 분리**: FileEntry 매핑 로직을 별도 클래스로 추출
3. **Repository 얇게**: Repository는 Query/Mapper 조합만 담당
4. **트랜잭션 관리 명확화**: 트랜잭션 경계를 명확히

### 3.2 원칙
- **단일 책임**: Query/Mapper/Repository 각각 하나의 책임만
- **재사용성**: Query/Mapper를 다른 Repository에서도 사용 가능
- **테스트 가능성**: 각 컴포넌트를 독립적으로 테스트 가능

---

## 4. 구체적인 리팩토링 계획

### 4.1 새로운 파일 구조

```
src/
├── infrastructure/
│   └── db/
│       ├── sqlite_index_repository.py    # 리팩토링 (200 lines 이하)
│       ├── queries/
│       │   ├── __init__.py
│       │   ├── run_queries.py            # 새 파일
│       │   ├── file_queries.py           # 새 파일
│       │   └── query_builder.py          # 새 파일
│       └── mappers/
│           ├── __init__.py
│           └── file_entry_mapper.py      # 새 파일
```

### 4.2 클래스 설계

#### 4.2.1 Query Builder

```python
# infrastructure/db/queries/query_builder.py

from typing import Optional

class QueryBuilder:
    """SQL 쿼리 빌더."""
    
    @staticmethod
    def build_list_files_query(
        run_id: int,
        offset: int,
        limit: int,
        ext: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        order_by: str = "path"
    ) -> tuple[str, list]:
        """파일 목록 조회 쿼리 생성.
        
        Returns:
            (SQL 쿼리, 파라미터 리스트)
        """
        # WHERE 조건 구축
        conditions = ["run_id = ?"]
        params = [run_id]
        
        if ext is not None:
            conditions.append("ext = ?")
            params.append(ext)
        
        if min_size is not None:
            conditions.append("size >= ?")
            params.append(min_size)
        
        if max_size is not None:
            conditions.append("size <= ?")
            params.append(max_size)
        
        where_clause = " AND ".join(conditions)
        
        # ORDER BY 처리
        order_by_sql = SQLiteIndexRepository.ALLOWED_ORDER_BY.get(order_by, "path ASC")
        
        sql = f"""
        SELECT file_id, path, size, mtime, ext, is_hidden, is_symlink
        FROM files
        WHERE {where_clause}
        ORDER BY {order_by_sql}
        LIMIT ? OFFSET ?
        """
        
        params.extend([limit, offset])
        
        return sql, params
```

#### 4.2.2 FileEntry Mapper

```python
# infrastructure/db/mappers/file_entry_mapper.py

from datetime import datetime
from pathlib import Path
from domain.entities.file_entry import FileEntry

class FileEntryMapper:
    """FileEntry 매핑 유틸리티."""
    
    @staticmethod
    def from_row(row: tuple) -> FileEntry:
        """DB row를 FileEntry로 변환.
        
        Args:
            row: (file_id, path_str, size, mtime_str, ext, is_hidden, is_symlink)
        
        Returns:
            FileEntry 객체.
        """
        file_id, path_str, size, mtime_str, ext, is_hidden, is_symlink = row
        
        return FileEntry(
            path=Path(path_str),
            size=size,
            mtime=datetime.fromisoformat(mtime_str),
            extension=ext,
            file_id=file_id,
            is_hidden=bool(is_hidden),
            is_symlink=bool(is_symlink),
        )
    
    @staticmethod
    def to_row(entry: FileEntry, run_id: int) -> tuple:
        """FileEntry를 DB row로 변환.
        
        Args:
            entry: FileEntry 객체.
            run_id: Run ID.
        
        Returns:
            (run_id, path, size, mtime, ext, is_hidden, is_symlink) 튜플.
        """
        return (
            run_id,
            str(entry.path.as_posix()),
            entry.size,
            entry.mtime.isoformat(),
            entry.extension,
            1 if entry.is_hidden else 0,
            1 if entry.is_symlink else 0,
        )
```

#### 4.2.3 리팩토링된 `SQLiteIndexRepository`

```python
# infrastructure/db/sqlite_index_repository.py (리팩토링 후)

from infrastructure.db.queries.query_builder import QueryBuilder
from infrastructure.db.mappers.file_entry_mapper import FileEntryMapper

class SQLiteIndexRepository:
    """SQLite 기반 인덱스 저장소 - IIndexRepository 구현."""
    
    def list_files(
        self,
        run_id: int,
        offset: int = 0,
        limit: int = 200,
        ext: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        order_by: str = "path"
    ) -> list[FileEntry]:
        """파일 목록 조회 (페이지네이션)."""
        conn = self._connect()
        try:
            # Query Builder로 쿼리 생성
            sql, params = QueryBuilder.build_list_files_query(
                run_id, offset, limit, ext, min_size, max_size, order_by
            )
            
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Mapper로 변환
            entries = [FileEntryMapper.from_row(row) for row in rows]
            
            debug_step(
                self._log_sink,
                "list_files_complete",
                {
                    "run_id": run_id,
                    "entries_count": len(entries),
                }
            )
            
            return entries
        finally:
            conn.close()
```

---

## 5. 단계별 작업 계획

### Phase 1: Query Builder 분리
- [ ] `QueryBuilder` 클래스 생성
- [ ] `build_list_files_query()` 메서드 추출
- [ ] 단위 테스트 작성

### Phase 2: Mapper 분리
- [ ] `FileEntryMapper` 클래스 생성
- [ ] `from_row()`, `to_row()` 메서드 추출
- [ ] 단위 테스트 작성

### Phase 3: Repository 리팩토링
- [ ] `SQLiteIndexRepository`를 Query/Mapper 사용하도록 수정
- [ ] 기존 쿼리 로직 제거

### Phase 4: 통합 테스트
- [ ] 기존 통합 테스트 실행하여 동작 확인
- [ ] 성능 테스트 (기존 대비 성능 유지 확인)

---

## 6. 예상 효과

### 6.1 코드 품질
- **재사용성**: Query/Mapper를 다른 Repository에서도 사용 가능
- **테스트 가능성**: 각 컴포넌트를 독립적으로 테스트 가능
- **가독성**: Repository가 얇아져 가독성 향상

### 6.2 유지보수성
- **분리**: 쿼리/매핑/트랜잭션 분리로 유지보수 용이
- **확장성**: 새로운 쿼리 추가 시 Query Builder만 수정
- **성능 튜닝**: 쿼리 로직이 집중되어 최적화 용이

---

## 7. 체크리스트

### 7.1 코드 작성
- [ ] `QueryBuilder` 작성
- [ ] `FileEntryMapper` 작성
- [ ] `SQLiteIndexRepository` 리팩토링

### 7.2 테스트
- [ ] Query Builder 단위 테스트
- [ ] Mapper 단위 테스트
- [ ] 기존 통합 테스트 통과 확인

### 7.3 문서화
- [ ] 클래스 docstring 작성
- [ ] 메서드 docstring 작성

---

**작성자**: NovelGuard 개발팀  
**검토 상태**: 대기 중  
**다음 단계**: Phase 1 시작
