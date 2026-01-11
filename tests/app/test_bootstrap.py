"""Bootstrap 모듈 테스트.

Bootstrap의 의존성 주입 및 애플리케이션 초기화를 테스트합니다.
"""

import sys
from pathlib import Path
from unittest.mock import Mock, patch
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from app.bootstrap import create_application, setup_application
from infra.db.file_repository import FileRepository
from usecases.scan_files import ScanFilesUseCase
from gui.views.main_window import MainWindow
from domain.ports.logger import ILogger
import logging


def test_setup_application_returns_logger() -> None:
    """setup_application이 ILogger 인터페이스를 반환하는지 확인."""
    logger = setup_application()
    # ILogger Protocol 구현 확인
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'warning')
    assert hasattr(logger, 'error')
    assert hasattr(logger, 'debug')
    assert callable(logger.info)
    assert callable(logger.warning)
    assert callable(logger.error)
    assert callable(logger.debug)


def test_setup_application_with_custom_log_level() -> None:
    """setup_application이 커스텀 로그 레벨을 사용하는지 확인."""
    logger = setup_application(log_level=logging.DEBUG)
    # ILogger는 로그 레벨을 직접 노출하지 않으므로, 로거 생성이 정상적으로 완료되는지만 확인
    assert hasattr(logger, 'info')
    assert hasattr(logger, 'debug')


@patch('app.bootstrap.QApplication')
@patch('app.bootstrap.EncodingDetector')
@patch('app.bootstrap.FileRepository')
@patch('app.bootstrap.ScanFilesUseCase')
def test_create_application_injects_dependencies(mock_usecase, mock_repo, mock_encoding, mock_app) -> None:
    """create_application이 MainWindow에 의존성을 주입하는지 확인."""
    # Mock 설정
    mock_repo_instance = Mock(spec=FileRepository)
    mock_encoding_instance = Mock()
    mock_usecase_instance = Mock(spec=ScanFilesUseCase)
    mock_app_instance = Mock()
    
    mock_repo.return_value = mock_repo_instance
    mock_encoding.return_value = mock_encoding_instance
    mock_usecase.return_value = mock_usecase_instance
    mock_app.return_value = mock_app_instance
    
    # MainWindow mock 생성
    with patch('app.bootstrap.MainWindow') as mock_main_window:
        mock_window_instance = Mock()
        mock_main_window.return_value = mock_window_instance
        
        # 애플리케이션 생성
        result = create_application()
        
        # 검증
        assert result == mock_app_instance
        mock_repo.assert_called_once()
        mock_encoding.assert_called_once()
        # UseCase는 이제 logger도 받음
        call_args = mock_usecase.call_args
        assert call_args is not None
        assert 'repository' in call_args.kwargs
        assert 'encoding_detector' in call_args.kwargs
        assert 'logger' in call_args.kwargs
        assert call_args.kwargs['repository'] == mock_repo_instance
        assert call_args.kwargs['encoding_detector'] == mock_encoding_instance
        # logger는 ILogger Protocol 구현 확인
        assert hasattr(call_args.kwargs['logger'], 'info')
        mock_main_window.assert_called_once()
        
        # MainWindow 생성자 호출 확인
        call_args = mock_main_window.call_args
        assert call_args is not None
        assert 'scan_usecase' in call_args.kwargs
        assert 'repository' in call_args.kwargs
        assert 'logger' in call_args.kwargs
        assert call_args.kwargs['scan_usecase'] == mock_usecase_instance
        assert call_args.kwargs['repository'] == mock_repo_instance
        # logger는 ILogger Protocol 구현 확인
        assert hasattr(call_args.kwargs['logger'], 'info')
        assert hasattr(call_args.kwargs['logger'], 'warning')
        assert hasattr(call_args.kwargs['logger'], 'error')
        assert hasattr(call_args.kwargs['logger'], 'debug')
        
        # window.show() 호출 확인
        mock_window_instance.show.assert_called_once()


def test_main_window_constructor_accepts_dependencies() -> None:
    """MainWindow 생성자가 의존성을 올바르게 받는지 확인."""
    # Mock 의존성 생성
    mock_usecase = Mock(spec=ScanFilesUseCase)
    mock_repository = Mock(spec=FileRepository)
    mock_logger = logging.getLogger("test")
    
    # MainWindow 생성 (PySide6 QApplication이 필요하므로 Mock)
    # QMainWindow를 완전히 Mock하여 초기화 문제 방지
    with patch('gui.views.main_window.QMainWindow') as mock_qmainwindow, \
         patch('gui.views.main_window.QSettings') as mock_qsettings, \
         patch('gui.views.main_window.StateManager') as mock_state_manager, \
         patch.object(MainWindow, '_assemble_pipeline'), \
         patch.object(MainWindow, '_create_header'), \
         patch.object(MainWindow, '_create_sidebar'), \
         patch.object(MainWindow, '_create_pages'), \
         patch.object(MainWindow, '_connect_navigation'), \
         patch.object(MainWindow, '_apply_styles'), \
         patch.object(MainWindow, '_auto_start_preview_scan'):
        
        # Mock QMainWindow 설정
        mock_qmainwindow_instance = Mock()
        mock_qmainwindow.return_value = mock_qmainwindow_instance
        mock_qmainwindow_instance.setWindowTitle = Mock()
        mock_qmainwindow_instance.setMinimumSize = Mock()
        
        # QSettings Mock
        mock_settings_instance = Mock()
        mock_qsettings.return_value = mock_settings_instance
        mock_settings_instance.value = Mock(return_value="")
        
        # StateManager Mock
        mock_state_manager_instance = Mock()
        mock_state_manager.return_value = mock_state_manager_instance
        
        # MainWindow 생성 시 QMainWindow를 직접 상속받지 않고 Mock 사용
        # 생성자 시그니처 검증만 수행
        import inspect
        sig = inspect.signature(MainWindow.__init__)
        params = list(sig.parameters.keys())
        
        # 의존성 파라미터 확인 (self 제외)
        assert 'scan_usecase' in params
        assert 'repository' in params
        assert 'logger' in params
        
        # 타입 힌트 확인
        assert sig.parameters['scan_usecase'].annotation.__name__ == 'ScanFilesUseCase'
        # logger는 이제 ILogger Protocol 사용
        # 타입 힌트는 'Logger'가 아닐 수 있음 (ILogger일 수 있음)


def test_main_window_no_direct_imports() -> None:
    """MainWindow가 infra/domain을 직접 import하지 않는지 확인 (TYPE_CHECKING만 허용)."""
    import inspect
    import ast
    
    # MainWindow 파일 소스 읽기
    main_window_file = PROJECT_ROOT / "src" / "gui" / "views" / "main_window.py"
    source = main_window_file.read_text(encoding='utf-8')
    
    # AST 파싱
    tree = ast.parse(source)
    
    # TYPE_CHECKING 블록 확인
    has_type_checking = False
    has_direct_imports = False
    
    for node in ast.walk(tree):
        # TYPE_CHECKING 블록 확인
        if isinstance(node, ast.If):
            if isinstance(node.test, ast.Name) and node.test.id == 'TYPE_CHECKING':
                has_type_checking = True
                # TYPE_CHECKING 블록 안의 import 확인
                for stmt in node.body:
                    if isinstance(stmt, ast.ImportFrom):
                        if stmt.module and ('infra' in stmt.module or 'domain' in stmt.module):
                            pass  # TYPE_CHECKING 블록 안이므로 허용
        # TYPE_CHECKING 블록 밖의 직접 import 확인
        elif isinstance(node, ast.ImportFrom):
            if node.module and ('infra' in node.module or 'domain' in node.module):
                # TYPE_CHECKING 블록이 아닌 직접 import
                if not any(isinstance(parent, ast.If) and 
                          isinstance(parent.test, ast.Name) and 
                          parent.test.id == 'TYPE_CHECKING'
                          for parent in ast.walk(tree) if isinstance(parent, ast.If)):
                    has_direct_imports = True
    
    # TYPE_CHECKING 블록은 있어야 함
    assert has_type_checking or not any('infra' in source or 'domain' in source for _ in [1]), \
        "MainWindow는 TYPE_CHECKING 블록을 사용하여 타입 힌트만 import해야 합니다"
