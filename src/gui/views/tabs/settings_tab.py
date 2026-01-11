"""설정 탭."""
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class SettingsTab(BaseTab):
    """설정 탭."""
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "⚙️ 설정"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 스캔 설정 그룹
        scan_group = self._create_scan_settings_group()
        layout.addWidget(scan_group)
        
        # 성능 설정 그룹
        performance_group = self._create_performance_group()
        layout.addWidget(performance_group)
        
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
    
    def _create_scan_settings_group(self) -> QGroupBox:
        """스캔 설정 그룹 생성."""
        group = QGroupBox("스캔 설정")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 파일 확장자 필터
        extension_layout = QVBoxLayout()
        extension_layout.setSpacing(8)
        
        extension_label = QLabel("파일 확장자 필터")
        extension_label.setObjectName("formLabel")
        extension_layout.addWidget(extension_label)
        
        self._extension_input = QLineEdit()
        self._extension_input.setPlaceholderText(".txt, .md, .log (비어있으면 모든 텍스트 파일)")
        extension_layout.addWidget(self._extension_input)
        
        layout.addLayout(extension_layout)
        
        # 스캔 옵션
        options_label = QLabel("스캔 옵션")
        options_label.setObjectName("formLabel")
        layout.addWidget(options_label)
        
        # 체크박스 그룹
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(12)
        
        self._include_subdirs = QCheckBox("하위 폴더 포함")
        self._include_subdirs.setChecked(True)
        checkbox_layout.addWidget(self._include_subdirs)
        
        self._incremental_scan = QCheckBox("증분 스캔")
        self._incremental_scan.setChecked(True)
        checkbox_layout.addWidget(self._incremental_scan)
        
        self._include_hidden = QCheckBox("숨김 파일 포함")
        checkbox_layout.addWidget(self._include_hidden)
        
        self._include_symlinks = QCheckBox("심볼릭 링크")
        self._include_symlinks.setChecked(True)
        checkbox_layout.addWidget(self._include_symlinks)
        
        layout.addLayout(checkbox_layout)
        
        return group
    
    def _create_performance_group(self) -> QGroupBox:
        """성능 설정 그룹 생성."""
        group = QGroupBox("성능 설정")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 워커 스레드 수
        worker_layout = QVBoxLayout()
        worker_layout.setSpacing(8)
        
        worker_label = QLabel("워커 스레드 수")
        worker_label.setObjectName("formLabel")
        worker_layout.addWidget(worker_label)
        
        self._worker_threads = QComboBox()
        self._worker_threads.addItems(["자동", "8", "16"])
        self._worker_threads.setCurrentIndex(1)  # 8
        worker_layout.addWidget(self._worker_threads)
        
        layout.addLayout(worker_layout)
        
        # 캐시 크기
        cache_layout = QVBoxLayout()
        cache_layout.setSpacing(8)
        
        cache_label = QLabel("캐시 크기 (MB)")
        cache_label.setObjectName("formLabel")
        cache_layout.addWidget(cache_label)
        
        self._cache_size = QLineEdit()
        self._cache_size.setText("512")
        cache_layout.addWidget(self._cache_size)
        
        layout.addLayout(cache_layout)
        
        return group
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        save_btn = QPushButton("설정 저장")
        save_btn.setObjectName("btnPrimary")
        save_btn.clicked.connect(self._on_save_settings)
        layout.addWidget(save_btn)
        
        reset_btn = QPushButton("기본값 복원")
        reset_btn.setObjectName("btnSecondary")
        reset_btn.clicked.connect(self._on_reset_settings)
        layout.addWidget(reset_btn)
        
        layout.addStretch()
        
        return layout
    
    def _on_save_settings(self) -> None:
        """설정 저장 핸들러."""
        # TODO: 실제 설정 저장 로직 구현
        print("설정 저장")
    
    def _on_reset_settings(self) -> None:
        """기본값 복원 핸들러."""
        # 스캔 설정 기본값
        self._extension_input.clear()
        self._include_subdirs.setChecked(True)
        self._incremental_scan.setChecked(True)
        self._include_hidden.setChecked(False)
        self._include_symlinks.setChecked(True)
        
        # 성능 설정 기본값
        self._worker_threads.setCurrentIndex(1)  # 8
        self._cache_size.setText("512")
    
    def get_extension_filter(self) -> str:
        """확장자 필터 반환.
        
        Returns:
            확장자 필터 문자열 (예: ".txt, .md, .log").
        """
        return self._extension_input.text().strip()
    
    def get_include_subdirs(self) -> bool:
        """하위 폴더 포함 여부 반환.
        
        Returns:
            하위 폴더 포함 여부.
        """
        return self._include_subdirs.isChecked()
    
    def get_incremental_scan(self) -> bool:
        """증분 스캔 여부 반환.
        
        Returns:
            증분 스캔 여부.
        """
        return self._incremental_scan.isChecked()
    
    def get_include_hidden(self) -> bool:
        """숨김 파일 포함 여부 반환.
        
        Returns:
            숨김 파일 포함 여부.
        """
        return self._include_hidden.isChecked()
    
    def get_include_symlinks(self) -> bool:
        """심볼릭 링크 포함 여부 반환.
        
        Returns:
            심볼릭 링크 포함 여부.
        """
        return self._include_symlinks.isChecked()
