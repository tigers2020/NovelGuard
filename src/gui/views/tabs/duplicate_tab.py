"""중복 파일 정리 탭."""
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class DuplicateTab(BaseTab):
    """중복 파일 정리 탭."""
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "🔍 중복 파일 정리"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 프로그레스 섹션
        self._progress_section = self._create_progress_section()
        layout.addWidget(self._progress_section)
        
        # 설정 그룹
        settings_group = self._create_settings_group()
        layout.addWidget(settings_group)
        
        # 필터 바
        filter_bar = self._create_filter_bar()
        layout.addLayout(filter_bar)
        
        # 결과 그룹
        results_group = self._create_results_group()
        layout.addWidget(results_group)
    
    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)
        
        detect_btn = QPushButton("중복 탐지 시작")
        detect_btn.setObjectName("btnPrimary")
        layout.addWidget(detect_btn)
        
        dry_run_btn = QPushButton("Dry Run")
        dry_run_btn.setObjectName("btnSecondary")
        layout.addWidget(dry_run_btn)
        
        apply_btn = QPushButton("적용하기")
        apply_btn.setObjectName("btnSuccess")
        layout.addWidget(apply_btn)
        
        layout.addStretch()
        
        return layout
    
    def _create_progress_section(self) -> QGroupBox:
        """프로그레스 섹션 생성."""
        group = QGroupBox()
        group.setTitle("")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(12)
        
        # 프로그레스 헤더
        progress_header = QHBoxLayout()
        progress_header.setContentsMargins(0, 0, 0, 0)
        
        progress_title = QLabel("중복 탐지 진행 중...")
        progress_title.setObjectName("progressTitle")
        progress_header.addWidget(progress_title)
        
        progress_header.addStretch()
        
        self._progress_percent = QLabel("0%")
        self._progress_percent.setObjectName("progressPercent")
        progress_header.addWidget(self._progress_percent)
        
        layout.addLayout(progress_header)
        
        # 프로그레스 바
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        layout.addWidget(self._progress_bar)
        
        # 프로그레스 정보
        self._progress_info = QLabel("대기 중...")
        self._progress_info.setObjectName("progressInfo")
        self._progress_info.setStyleSheet("font-size: 12px; color: #808080;")
        layout.addWidget(self._progress_info)
        
        # 항상 보이도록 설정
        group.setVisible(True)
        
        return group
    
    def _create_settings_group(self) -> QGroupBox:
        """설정 그룹 생성."""
        group = QGroupBox("중복 탐지 설정")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        layout.setSpacing(20)
        
        # 중복 유형
        type_label = QLabel("중복 유형")
        type_label.setObjectName("formLabel")
        layout.addWidget(type_label)
        
        checkbox_layout = QVBoxLayout()
        checkbox_layout.setSpacing(12)
        
        self._exact_duplicate = QCheckBox("완전 중복 (Exact)")
        self._exact_duplicate.setChecked(True)
        checkbox_layout.addWidget(self._exact_duplicate)
        
        self._near_duplicate = QCheckBox("유사 중복 (Near)")
        self._near_duplicate.setChecked(True)
        checkbox_layout.addWidget(self._near_duplicate)
        
        self._include_relation = QCheckBox("포함 관계")
        self._include_relation.setChecked(True)
        checkbox_layout.addWidget(self._include_relation)
        
        layout.addLayout(checkbox_layout)
        
        # 유사도 임계값
        threshold_layout = QVBoxLayout()
        threshold_layout.setSpacing(8)
        
        threshold_label = QLabel("유사도 임계값 (%)")
        threshold_label.setObjectName("formLabel")
        threshold_layout.addWidget(threshold_label)
        
        self._similarity_slider = QSlider()
        self._similarity_slider.setOrientation(Qt.Horizontal)
        self._similarity_slider.setRange(50, 100)
        self._similarity_slider.setValue(85)
        threshold_layout.addWidget(self._similarity_slider)
        
        self._similarity_label = QLabel("85%")
        self._similarity_label.setObjectName("progressPercent")
        threshold_layout.addWidget(self._similarity_label)
        
        self._similarity_slider.valueChanged.connect(
            lambda v: self._similarity_label.setText(f"{v}%")
        )
        
        layout.addLayout(threshold_layout)
        
        # 충돌 시 정책
        policy_layout = QVBoxLayout()
        policy_layout.setSpacing(8)
        
        policy_label = QLabel("충돌 시 정책")
        policy_label.setObjectName("formLabel")
        policy_layout.addWidget(policy_label)
        
        self._conflict_policy = QComboBox()
        self._conflict_policy.addItems([
            "건너뛰기 (Skip)",
            "접미사 추가 (Rename)",
            "덮어쓰기 (Overwrite)",
            "병합 (Merge)"
        ])
        self._conflict_policy.setCurrentIndex(1)  # 접미사 추가
        policy_layout.addWidget(self._conflict_policy)
        
        layout.addLayout(policy_layout)
        
        return group
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """필터 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # 확장자 필터
        ext_label = QLabel("확장자:")
        layout.addWidget(ext_label)
        
        ext_combo = QComboBox()
        ext_combo.addItems(["전체", ".txt", ".md"])
        layout.addWidget(ext_combo)
        
        # 크기 필터
        size_label = QLabel("크기:")
        layout.addWidget(size_label)
        
        size_combo = QComboBox()
        size_combo.addItems(["전체", "< 1KB", "> 1MB"])
        layout.addWidget(size_combo)
        
        # 중복군 필터
        group_label = QLabel("중복군:")
        layout.addWidget(group_label)
        
        group_combo = QComboBox()
        group_combo.addItems(["전체", "≥ 2개", "≥ 5개"])
        layout.addWidget(group_combo)
        
        layout.addStretch()
        
        return layout
    
    def _create_results_group(self) -> QGroupBox:
        """결과 그룹 생성."""
        group = QGroupBox("중복 파일 결과 (0개 그룹)")
        group.setObjectName("settingsGroup")
        
        layout = QVBoxLayout(group)
        
        # TODO: 결과 카드 그리드 구현
        placeholder = QLabel("중복 탐지 결과가 여기에 표시됩니다.")
        placeholder.setStyleSheet("color: #808080; font-size: 14px; padding: 20px;")
        layout.addWidget(placeholder)
        
        return group
