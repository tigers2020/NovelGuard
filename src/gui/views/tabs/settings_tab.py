"""설정 탭."""
from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from app.settings.constants import (
    Constants,
    SETTINGS_KEY_CACHE_SIZE_MB,
    SETTINGS_KEY_CONFLICT_POLICY,
    SETTINGS_KEY_EXACT_DUPLICATE,
    SETTINGS_KEY_EXTENSION_FILTER,
    SETTINGS_KEY_INCLUDE_HIDDEN,
    SETTINGS_KEY_INCLUDE_RELATION,
    SETTINGS_KEY_INCLUDE_SUBDIRS,
    SETTINGS_KEY_INCLUDE_SYMLINKS,
    SETTINGS_KEY_INCREMENTAL_SCAN,
    SETTINGS_KEY_NEAR_DUPLICATE,
    SETTINGS_KEY_SIMILARITY_PERCENT,
    SETTINGS_KEY_WORKER_THREADS,
)
from gui.views.tabs.base_tab import BaseTab


class SettingsTab(BaseTab):
    """설정 탭."""
    
    def __init__(self, parent=None) -> None:
        """설정 탭 초기화.
        
        Args:
            parent: 부모 위젯.
        """
        # QSettings 초기화 (super().__init__() 전에 해야 함)
        self._settings = QSettings()
        super().__init__(parent)
    
    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "⚙️ 설정"
    
    def _setup_content(self, layout: QVBoxLayout) -> None:
        """컨텐츠 설정."""
        # 스캔 설정 그룹
        scan_group = self._create_scan_settings_group()
        layout.addWidget(scan_group)
        
        # 중복 탐지 설정 그룹
        duplicate_group = self._create_duplicate_settings_group()
        layout.addWidget(duplicate_group)
        
        # 성능 설정 그룹
        performance_group = self._create_performance_group()
        layout.addWidget(performance_group)
        
        # 액션 바
        action_bar = self._create_action_bar()
        layout.addLayout(action_bar)
        
        # 설정 로드 (UI 위젯 생성 후)
        self._load_settings()
    
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
    
    def _create_duplicate_settings_group(self) -> QGroupBox:
        """중복 탐지 설정 그룹 생성."""
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
        self._similarity_slider.setRange(Constants.SIMILARITY_MIN_PERCENT, Constants.SIMILARITY_MAX_PERCENT)
        self._similarity_slider.setValue(Constants.DEFAULT_SIMILARITY_PERCENT)
        threshold_layout.addWidget(self._similarity_slider)
        
        self._similarity_label = QLabel(f"{Constants.DEFAULT_SIMILARITY_PERCENT}%")
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
        self._conflict_policy.setCurrentIndex(Constants.DEFAULT_CONFLICT_POLICY_INDEX)  # 접미사 추가
        policy_layout.addWidget(self._conflict_policy)
        
        layout.addLayout(policy_layout)
        
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
        # 워커 스레드 수는 인덱스 1이 기본값 (8 스레드)
        self._worker_threads.setCurrentIndex(1)  # Constants.DEFAULT_WORKER_THREADS와 매핑됨
        worker_layout.addWidget(self._worker_threads)
        
        layout.addLayout(worker_layout)
        
        # 캐시 크기
        cache_layout = QVBoxLayout()
        cache_layout.setSpacing(8)
        
        cache_label = QLabel("캐시 크기 (MB)")
        cache_label.setObjectName("formLabel")
        cache_layout.addWidget(cache_label)
        
        self._cache_size = QLineEdit()
        self._cache_size.setText(str(Constants.DEFAULT_CACHE_SIZE_MB))
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
        try:
            # 스캔 설정 저장
            self._settings.setValue(SETTINGS_KEY_EXTENSION_FILTER, self._extension_input.text().strip())
            self._settings.setValue(SETTINGS_KEY_INCLUDE_SUBDIRS, self._include_subdirs.isChecked())
            self._settings.setValue(SETTINGS_KEY_INCREMENTAL_SCAN, self._incremental_scan.isChecked())
            self._settings.setValue(SETTINGS_KEY_INCLUDE_HIDDEN, self._include_hidden.isChecked())
            self._settings.setValue(SETTINGS_KEY_INCLUDE_SYMLINKS, self._include_symlinks.isChecked())
            
            # 중복 탐지 설정 저장
            self._settings.setValue(SETTINGS_KEY_EXACT_DUPLICATE, self._exact_duplicate.isChecked())
            self._settings.setValue(SETTINGS_KEY_NEAR_DUPLICATE, self._near_duplicate.isChecked())
            self._settings.setValue(SETTINGS_KEY_INCLUDE_RELATION, self._include_relation.isChecked())
            self._settings.setValue(SETTINGS_KEY_SIMILARITY_PERCENT, self._similarity_slider.value())
            self._settings.setValue(SETTINGS_KEY_CONFLICT_POLICY, self._conflict_policy.currentIndex())
            
            # 성능 설정 저장
            self._settings.setValue(SETTINGS_KEY_WORKER_THREADS, self._worker_threads.currentIndex())
            
            # 캐시 크기 검증 및 저장
            try:
                cache_size = int(self._cache_size.text().strip())
                if cache_size < 1:
                    cache_size = Constants.DEFAULT_CACHE_SIZE_MB
                self._settings.setValue(SETTINGS_KEY_CACHE_SIZE_MB, cache_size)
            except ValueError:
                # 유효하지 않은 값이면 기본값 사용
                self._settings.setValue(SETTINGS_KEY_CACHE_SIZE_MB, Constants.DEFAULT_CACHE_SIZE_MB)
                self._cache_size.setText(str(Constants.DEFAULT_CACHE_SIZE_MB))
            
            # 설정 동기화
            self._settings.sync()
            
            # 성공 메시지 표시
            QMessageBox.information(self, "설정 저장", "설정이 성공적으로 저장되었습니다.")
        
        except Exception as e:
            # 오류 메시지 표시
            QMessageBox.warning(self, "설정 저장 오류", f"설정 저장 중 오류가 발생했습니다:\n{str(e)}")
    
    def _load_settings(self) -> None:
        """QSettings에서 설정을 로드하고 UI에 적용.
        
        _setup_content 이후에 호출되어야 합니다.
        """
        """로드된 설정을 UI에 적용.
        
        _setup_content 이후에 호출되어야 합니다.
        """
        # 스캔 설정 로드
        extension_filter = self._settings.value(SETTINGS_KEY_EXTENSION_FILTER, "", type=str)
        if extension_filter:
            self._extension_input.setText(extension_filter)
        
        self._include_subdirs.setChecked(
            self._settings.value(SETTINGS_KEY_INCLUDE_SUBDIRS, True, type=bool)
        )
        self._incremental_scan.setChecked(
            self._settings.value(SETTINGS_KEY_INCREMENTAL_SCAN, True, type=bool)
        )
        self._include_hidden.setChecked(
            self._settings.value(SETTINGS_KEY_INCLUDE_HIDDEN, False, type=bool)
        )
        self._include_symlinks.setChecked(
            self._settings.value(SETTINGS_KEY_INCLUDE_SYMLINKS, True, type=bool)
        )
        
        # 중복 탐지 설정 로드
        self._exact_duplicate.setChecked(
            self._settings.value(SETTINGS_KEY_EXACT_DUPLICATE, True, type=bool)
        )
        self._near_duplicate.setChecked(
            self._settings.value(SETTINGS_KEY_NEAR_DUPLICATE, True, type=bool)
        )
        self._include_relation.setChecked(
            self._settings.value(SETTINGS_KEY_INCLUDE_RELATION, True, type=bool)
        )
        
        similarity_percent = self._settings.value(
            SETTINGS_KEY_SIMILARITY_PERCENT, Constants.DEFAULT_SIMILARITY_PERCENT, type=int
        )
        if Constants.SIMILARITY_MIN_PERCENT <= similarity_percent <= Constants.SIMILARITY_MAX_PERCENT:
            self._similarity_slider.setValue(similarity_percent)
            self._similarity_label.setText(f"{similarity_percent}%")
        
        conflict_policy_index = self._settings.value(
            SETTINGS_KEY_CONFLICT_POLICY, Constants.DEFAULT_CONFLICT_POLICY_INDEX, type=int
        )
        if 0 <= conflict_policy_index < self._conflict_policy.count():
            self._conflict_policy.setCurrentIndex(conflict_policy_index)
        
        # 성능 설정 로드
        worker_threads_index = self._settings.value(SETTINGS_KEY_WORKER_THREADS, 1, type=int)
        if 0 <= worker_threads_index < self._worker_threads.count():
            self._worker_threads.setCurrentIndex(worker_threads_index)
        
        cache_size_mb = self._settings.value(
            SETTINGS_KEY_CACHE_SIZE_MB, Constants.DEFAULT_CACHE_SIZE_MB, type=int
        )
        if cache_size_mb >= 1:
            self._cache_size.setText(str(cache_size_mb))
    
    def _on_reset_settings(self) -> None:
        """기본값 복원 핸들러."""
        # 스캔 설정 기본값
        self._extension_input.clear()
        self._include_subdirs.setChecked(True)
        self._incremental_scan.setChecked(True)
        self._include_hidden.setChecked(False)
        self._include_symlinks.setChecked(True)
        
        # 중복 탐지 설정 기본값
        self._exact_duplicate.setChecked(True)
        self._near_duplicate.setChecked(True)
        self._include_relation.setChecked(True)
        self._similarity_slider.setValue(85)
        self._similarity_label.setText("85%")
        self._conflict_policy.setCurrentIndex(Constants.DEFAULT_CONFLICT_POLICY_INDEX)  # 접미사 추가
        
        # 성능 설정 기본값
        # 워커 스레드 수는 인덱스 1이 기본값 (8 스레드)
        self._worker_threads.setCurrentIndex(1)  # Constants.DEFAULT_WORKER_THREADS와 매핑됨
        self._cache_size.setText(str(Constants.DEFAULT_CACHE_SIZE_MB))
    
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
    
    def get_exact_duplicate(self) -> bool:
        """완전 중복 탐지 여부 반환.
        
        Returns:
            완전 중복 탐지 여부.
        """
        return self._exact_duplicate.isChecked()
    
    def get_near_duplicate(self) -> bool:
        """유사 중복 탐지 여부 반환.
        
        Returns:
            유사 중복 탐지 여부.
        """
        return self._near_duplicate.isChecked()
    
    def get_include_relation(self) -> bool:
        """포함 관계 탐지 여부 반환.
        
        Returns:
            포함 관계 탐지 여부.
        """
        return self._include_relation.isChecked()
    
    def get_similarity_threshold(self) -> int:
        """유사도 임계값 반환.
        
        Returns:
            유사도 임계값 (50-100).
        """
        return self._similarity_slider.value()
    
    def get_conflict_policy(self) -> str:
        """충돌 시 정책 반환.
        
        Returns:
            충돌 시 정책 문자열.
        """
        return self._conflict_policy.currentText()
