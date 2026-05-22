"""인코딩 통일 탭."""

from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
)

from gui.views.tabs.base_tab import BaseTab


class EncodingTab(BaseTab):
    """인코딩 통일 탭."""

    def get_title(self) -> str:
        """페이지 제목 반환."""
        return "인코딩 통일"

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

    def _create_action_bar(self) -> QHBoxLayout:
        """액션 바 생성."""
        layout = QHBoxLayout()
        layout.setSpacing(16)

        analyze_btn = QPushButton("인코딩 분석")
        analyze_btn.setObjectName("btnPrimary")
        layout.addWidget(analyze_btn)

        convert_btn = QPushButton("UTF-8 변환")
        convert_btn.setObjectName("btnSuccess")
        layout.addWidget(convert_btn)

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

        progress_title = QLabel("인코딩 분석/변환 진행 중...")
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
        self._progress_info.setObjectName("progressInfo")
        layout.addWidget(self._progress_info)

        # 항상 보이도록 설정
        group.setVisible(True)

        return group

    def _create_settings_group(self) -> QGroupBox:
        """설정 그룹 생성."""
        group = QGroupBox("변환 설정")
        group.setObjectName("settingsGroup")

        layout = QVBoxLayout(group)
        layout.setSpacing(20)

        # 목표 인코딩
        encoding_layout = QVBoxLayout()
        encoding_layout.setSpacing(8)

        encoding_label = QLabel("목표 인코딩")
        encoding_label.setObjectName("formLabel")
        encoding_layout.addWidget(encoding_label)

        self._target_encoding = QComboBox()
        self._target_encoding.addItems(["UTF-8 (LF)", "UTF-8 (CRLF)", "UTF-16"])
        self._target_encoding.setCurrentIndex(0)  # UTF-8 (LF)
        encoding_layout.addWidget(self._target_encoding)

        layout.addLayout(encoding_layout)

        return group
