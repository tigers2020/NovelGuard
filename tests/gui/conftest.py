"""GUI 테스트 공통 픽스처."""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp() -> QApplication:
    """QObject/Signal 사용 시 필요한 QApplication 단일 인스턴스."""
    inst = QApplication.instance()
    if inst is None:
        inst = QApplication([])
    return inst
