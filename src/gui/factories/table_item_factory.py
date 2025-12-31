"""
테이블 아이템 팩토리 모듈

QTableWidgetItem을 생성하는 기능을 제공합니다.
"""

from PySide6.QtWidgets import QTableWidgetItem
from PySide6.QtCore import Qt

from models.file_record import FileRecord
from utils.formatters import format_file_size


class TableItemFactory:
    """테이블 아이템 팩토리 클래스.
    
    FileRecord로부터 QTableWidgetItem을 생성합니다.
    각 컬럼에 맞는 아이템을 생성하고 데이터를 바인딩합니다.
    
    Attributes:
        (없음)
    """
    
    def create_name_item(self, file_record: FileRecord) -> QTableWidgetItem:
        """파일명 아이템을 생성합니다.
        
        Args:
            file_record: FileRecord 객체
        
        Returns:
            파일명 QTableWidgetItem (path를 userData로 저장)
        """
        name_item = QTableWidgetItem(file_record.name)
        name_item.setToolTip(str(file_record.path))
        name_item.setData(Qt.ItemDataRole.UserRole, str(file_record.path))  # path 저장
        return name_item
    
    def create_size_item(self, file_record: FileRecord) -> QTableWidgetItem:
        """파일 크기 아이템을 생성합니다.
        
        Args:
            file_record: FileRecord 객체
        
        Returns:
            파일 크기 QTableWidgetItem (포맷팅됨, 우측 정렬)
            정렬을 위해 UserRole에 실제 바이트 크기를 저장합니다.
        """
        size_str = format_file_size(file_record.size)
        size_item = QTableWidgetItem(size_str)
        size_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        # 정렬을 위해 실제 바이트 크기를 UserRole에 저장
        # QTableWidget은 UserRole 값을 사용하여 정렬합니다
        size_item.setData(Qt.ItemDataRole.UserRole, file_record.size)
        return size_item
    
    def create_encoding_item(self, file_record: FileRecord) -> QTableWidgetItem:
        """인코딩 아이템을 생성합니다.
        
        Args:
            file_record: FileRecord 객체
        
        Returns:
            인코딩 QTableWidgetItem
        """
        return QTableWidgetItem(file_record.encoding)
    
    def create_duplicate_item(self, default_text: str = "-") -> QTableWidgetItem:
        """중복 여부 아이템을 생성합니다.
        
        Args:
            default_text: 기본 텍스트 (기본값: "-")
        
        Returns:
            중복 여부 QTableWidgetItem
        """
        return QTableWidgetItem(default_text)
    
    def create_integrity_item(self, default_text: str = "-") -> QTableWidgetItem:
        """무결성 상태 아이템을 생성합니다.
        
        Args:
            default_text: 기본 텍스트 (기본값: "-")
        
        Returns:
            무결성 상태 QTableWidgetItem
        """
        return QTableWidgetItem(default_text)
    
    def create_row_items(self, file_record: FileRecord) -> list[QTableWidgetItem]:
        """한 행의 모든 아이템을 생성합니다.
        
        Args:
            file_record: FileRecord 객체
        
        Returns:
            [파일명, 크기, 인코딩, 중복여부, 무결성상태] 아이템 리스트
        """
        return [
            self.create_name_item(file_record),
            self.create_size_item(file_record),
            self.create_encoding_item(file_record),
            self.create_duplicate_item(),
            self.create_integrity_item()
        ]

