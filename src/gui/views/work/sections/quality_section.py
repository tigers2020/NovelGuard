"""Quality checks placeholder (integrity, encoding, small files)."""

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class QualitySection(QWidget):
    """Disabled quality tools until use cases are wired."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        notice = QLabel(
            "무결성·인코딩·작은 파일 정리는 준비 중입니다. "
            "아래 버튼은 UI 뼈대이며 동작하지 않습니다."
        )
        notice.setObjectName("placeholder")
        notice.setWordWrap(True)
        layout.addWidget(notice)

        bar = QHBoxLayout()
        for label in ("무결성 검사", "인코딩 분석", "UTF-8 변환"):
            btn = QPushButton(label)
            btn.setObjectName("btnSecondary")
            btn.setEnabled(False)
            btn.setToolTip("미구현")
            bar.addWidget(btn)
        bar.addStretch()
        layout.addLayout(bar)

        small = QLabel("작은 파일 정리: 준비 중")
        small.setObjectName("formHint")
        layout.addWidget(small)
