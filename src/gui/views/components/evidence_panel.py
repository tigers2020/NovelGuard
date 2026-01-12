"""증거 패널 컴포넌트."""
import json
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from application.dto.duplicate_group_result import DuplicateGroupResult


class EvidencePanel(QWidget):
    """증거 패널 위젯."""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """증거 패널 초기화.
        
        Args:
            parent: 부모 위젯.
        """
        super().__init__(parent)
        
        self._current_result: Optional[DuplicateGroupResult] = None
        
        self._setup_ui()
    
    def _setup_ui(self) -> None:
        """UI 설정."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # 그룹 정보 헤더
        header_group = QGroupBox("그룹 정보")
        header_group.setObjectName("settingsGroup")
        header_layout = QVBoxLayout(header_group)
        header_layout.setSpacing(8)
        
        self._group_info_label = QLabel()
        self._group_info_label.setObjectName("groupInfoLabel")
        header_layout.addWidget(self._group_info_label)
        
        layout.addWidget(header_group)
        
        # Reason 텍스트
        reason_group = QGroupBox("판정 근거")
        reason_group.setObjectName("settingsGroup")
        reason_layout = QVBoxLayout(reason_group)
        
        self._reason_text = QTextEdit()
        self._reason_text.setReadOnly(True)
        self._reason_text.setMaximumHeight(100)
        self._reason_text.setStyleSheet("""
            QTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 8px;
                font-size: 12px;
            }
        """)
        reason_layout.addWidget(self._reason_text)
        
        layout.addWidget(reason_group)
        
        # Evidence JSON
        evidence_group = QGroupBox("Evidence (JSON)")
        evidence_group.setObjectName("settingsGroup")
        evidence_layout = QVBoxLayout(evidence_group)
        
        # JSON 텍스트 영역
        self._evidence_json = QPlainTextEdit()
        self._evidence_json.setReadOnly(True)
        self._evidence_json.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1a1a;
                border: 1px solid #2a2a2a;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Consolas', 'Monaco', monospace;
                font-size: 11px;
            }
        """)
        evidence_layout.addWidget(self._evidence_json)
        
        # Copy 버튼
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        copy_btn = QPushButton("Copy JSON")
        copy_btn.setObjectName("btnSecondary")
        copy_btn.clicked.connect(self._on_copy_json)
        button_layout.addWidget(copy_btn)
        
        evidence_layout.addLayout(button_layout)
        
        layout.addWidget(evidence_group)
        
        layout.addStretch()
        
        # 초기 상태: 빈 패널
        self.clear()
    
    def set_group(self, result: DuplicateGroupResult) -> None:
        """그룹 설정.
        
        Args:
            result: 중복 그룹 결과.
        """
        self._current_result = result
        
        # 그룹 정보 업데이트
        self._update_group_info(result)
        
        # Reason 업데이트
        reason_text = self._format_reason(result)
        self._reason_text.setPlainText(reason_text)
        
        # Evidence JSON 업데이트
        evidence_json = self._format_evidence_json(result.evidence)
        self._evidence_json.setPlainText(evidence_json)
    
    def clear(self) -> None:
        """패널 초기화."""
        self._current_result = None
        self._group_info_label.setText("그룹을 선택하세요")
        self._reason_text.clear()
        self._evidence_json.clear()
    
    def _update_group_info(self, result: DuplicateGroupResult) -> None:
        """그룹 정보 업데이트.
        
        Args:
            result: 중복 그룹 결과.
        """
        type_labels = {
            "exact": "완전 중복",
            "version": "버전 관계",
            "containment": "포함 관계",
            "near": "유사 중복"
        }
        type_label = type_labels.get(result.duplicate_type, result.duplicate_type)
        
        info_text = (
            f"타입: {type_label} | "
            f"그룹 ID: {result.group_id} | "
            f"파일 수: {len(result.file_ids)} | "
            f"신뢰도: {result.confidence * 100:.0f}%"
        )
        self._group_info_label.setText(info_text)
    
    def _format_reason(self, result: DuplicateGroupResult) -> str:
        """판정 근거 포맷팅.
        
        Args:
            result: 중복 그룹 결과.
            
        Returns:
            포맷된 근거 문자열.
        """
        evidence = result.evidence
        if not isinstance(evidence, dict):
            return "근거 정보 없음"
        
        type_str = result.duplicate_type
        
        if type_str == "version":
            # 버전 관계: start 동일, end 증가, size 증가
            newer_range = evidence.get("newer_range")
            older_range = evidence.get("older_range")
            if newer_range and older_range:
                return (
                    f"버전 관계: 범위가 확장됨\n"
                    f"이전: {older_range} → 최신: {newer_range}\n"
                    f"범위 시작점은 동일하며, 종료점이 증가했습니다."
                )
            return "버전 관계: 범위 확장 (세부 정보 없음)"
        
        elif type_str == "containment":
            # 포함 관계: A range ⊂ B range
            container_range = evidence.get("container_range")
            contained_range = evidence.get("contained_range")
            if container_range and contained_range:
                return (
                    f"포함 관계: 하나의 파일이 다른 파일의 범위를 포함함\n"
                    f"상위본: {container_range}\n"
                    f"하위본: {contained_range}\n"
                    f"하위본의 범위가 상위본에 포함됩니다."
                )
            return "포함 관계: 범위 포함 (세부 정보 없음)"
        
        elif type_str == "exact":
            # 완전 중복: hash match
            hash_match = evidence.get("hash_match")
            if hash_match:
                return (
                    f"완전 중복: 파일 내용이 100% 동일함\n"
                    f"해시 값이 일치합니다."
                )
            return "완전 중복: 파일 내용 동일 (현재는 메타 기반 판정)"
        
        elif type_str == "near":
            # 유사 중복: similarity %
            similarity = evidence.get("similarity_score") or result.confidence
            return (
                f"유사 중복: 파일 내용이 거의 동일함\n"
                f"유사도: {similarity * 100:.0f}%"
            )
        
        return "근거 정보 없음"
    
    def _format_evidence_json(self, evidence: dict) -> str:
        """Evidence JSON 포맷팅.
        
        Args:
            evidence: evidence 딕셔너리.
            
        Returns:
            pretty JSON 문자열.
        """
        try:
            return json.dumps(evidence, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(evidence)
    
    def _on_copy_json(self) -> None:
        """JSON 복사 버튼 핸들러."""
        if self._current_result:
            json_text = self._format_evidence_json(self._current_result.evidence)
            from PySide6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(json_text)
