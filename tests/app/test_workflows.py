"""워크플로우 구조 테스트.

워크플로우가 UseCase 조합만 수행하고 로직을 포함하지 않는지 AST 기반으로 검증합니다.
"""

import sys
import ast
import inspect
from pathlib import Path
from typing import Any
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app.workflows.scan_flow import ScanFlow
from app.workflows.analysis_flow import AnalysisFlow


def test_scan_flow_contains_no_branching_logic() -> None:
    """ScanFlow에 조건문/반복문이 없는지 AST 기반 검증."""
    # 클래스 전체 소스를 파싱
    class_src = inspect.getsource(ScanFlow)
    class_tree = ast.parse(class_src)
    
    # execute 메서드 찾기
    execute_method = None
    for node in ast.walk(class_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute":
            execute_method = node
            break
    
    assert execute_method is not None, "execute 메서드를 찾을 수 없습니다"
    
    # 금지된 노드 타입 목록
    forbidden_nodes = (
        ast.If, ast.For, ast.While, ast.ListComp, ast.DictComp,
        ast.SetComp, ast.GeneratorExp, ast.Lambda
    )
    
    # execute 메서드 내부에서 금지된 노드 검색
    for node in ast.walk(execute_method):
        if isinstance(node, forbidden_nodes):
            node_type = type(node).__name__
            node_src = ast.get_source_segment(class_src, node)
            raise AssertionError(
                f"ScanFlow에 금지된 {node_type} 노드 발견: "
                f"{node_src or 'N/A'}"
            )


def test_analysis_flow_contains_no_branching_logic() -> None:
    """AnalysisFlow에 조건문/반복문이 없는지 AST 기반 검증."""
    # 클래스 전체 소스를 파싱
    class_src = inspect.getsource(AnalysisFlow)
    class_tree = ast.parse(class_src)
    
    # execute 메서드 찾기
    execute_method = None
    for node in ast.walk(class_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute":
            execute_method = node
            break
    
    assert execute_method is not None, "execute 메서드를 찾을 수 없습니다"
    
    # 금지된 노드 타입 목록
    forbidden_nodes = (
        ast.If, ast.For, ast.While, ast.ListComp, ast.DictComp,
        ast.SetComp, ast.GeneratorExp, ast.Lambda
    )
    
    # execute 메서드 내부에서 금지된 노드 검색
    for node in ast.walk(execute_method):
        if isinstance(node, forbidden_nodes):
            node_type = type(node).__name__
            node_src = ast.get_source_segment(class_src, node)
            raise AssertionError(
                f"AnalysisFlow에 금지된 {node_type} 노드 발견: "
                f"{node_src or 'N/A'}"
            )


def test_scan_flow_only_calls_usecase() -> None:
    """ScanFlow가 UseCase 호출만 수행하는지 AST 기반 검증."""
    # 클래스 전체 소스를 파싱
    class_src = inspect.getsource(ScanFlow)
    class_tree = ast.parse(class_src)
    
    # execute 메서드 찾기
    execute_method = None
    for node in ast.walk(class_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute":
            execute_method = node
            break
    
    assert execute_method is not None, "execute 메서드를 찾을 수 없습니다"
    
    # 함수 정의 내부의 모든 문(statement) 검사
    for stmt in execute_method.body:
        # 허용된 패턴: Return, Assign (변수 할당), Expr (UseCase 호출), Pass
        if isinstance(stmt, (ast.Return, ast.Assign, ast.Expr, ast.Pass)):
            # 함수 호출인 경우 UseCase 호출 패턴 확인
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                # self.xxx_usecase.execute() 패턴 확인
                if not (isinstance(stmt.value.func, ast.Attribute) and
                       isinstance(stmt.value.func.value, ast.Attribute) and
                       stmt.value.func.value.attr.endswith("_usecase")):
                    node_src = ast.get_source_segment(class_src, stmt)
                    raise AssertionError(
                        f"ScanFlow에 허용되지 않은 호출: "
                        f"{node_src or 'N/A'}"
                    )
        elif isinstance(stmt, ast.FunctionDef):
            # 내부 함수 정의는 허용하지 않음
            node_src = ast.get_source_segment(class_src, stmt)
            raise AssertionError(
                f"ScanFlow에 허용되지 않은 내부 함수 정의: "
                f"{node_src or 'N/A'}"
            )


def test_analysis_flow_only_calls_usecases() -> None:
    """AnalysisFlow가 UseCase 호출만 수행하는지 AST 기반 검증."""
    # 클래스 전체 소스를 파싱
    class_src = inspect.getsource(AnalysisFlow)
    class_tree = ast.parse(class_src)
    
    # execute 메서드 찾기
    execute_method = None
    for node in ast.walk(class_tree):
        if isinstance(node, ast.FunctionDef) and node.name == "execute":
            execute_method = node
            break
    
    assert execute_method is not None, "execute 메서드를 찾을 수 없습니다"
    
    # 함수 정의 내부의 모든 문(statement) 검사
    for stmt in execute_method.body:
        # 허용된 패턴: Return, Assign, Expr, Pass
        if isinstance(stmt, (ast.Return, ast.Assign, ast.Expr, ast.Pass)):
            # 함수 호출인 경우 UseCase 호출 패턴 확인
            if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
                # self.xxx_usecase.execute() 패턴 확인
                if not (isinstance(stmt.value.func, ast.Attribute) and
                       isinstance(stmt.value.func.value, ast.Attribute) and
                       stmt.value.func.value.attr.endswith("_usecase")):
                    node_src = ast.get_source_segment(class_src, stmt)
                    raise AssertionError(
                        f"AnalysisFlow에 허용되지 않은 호출: "
                        f"{node_src or 'N/A'}"
                    )
        elif isinstance(stmt, ast.FunctionDef):
            # 내부 함수 정의는 허용하지 않음
            node_src = ast.get_source_segment(class_src, stmt)
            raise AssertionError(
                f"AnalysisFlow에 허용되지 않은 내부 함수 정의: "
                f"{node_src or 'N/A'}"
            )


def test_workflow_composition_with_mocks() -> None:
    """워크플로우가 UseCase Mock을 주입받아 조합 동작만 테스트."""
    from unittest.mock import Mock
    from usecases.scan_files import ScanFilesUseCase
    
    # Mock UseCase 생성
    mock_scan_usecase = Mock(spec=ScanFilesUseCase)
    mock_scan_usecase.execute.return_value = []
    
    # ScanFlow 생성 및 실행
    scan_flow = ScanFlow(mock_scan_usecase)
    result = scan_flow.execute(Path("/test"))
    
    # UseCase가 호출되었는지 확인
    mock_scan_usecase.execute.assert_called_once()
    assert result == []
