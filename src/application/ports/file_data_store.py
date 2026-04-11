"""파일 데이터 저장소 포트."""

from pathlib import Path
from typing import Optional, Protocol, Union

from application.dto.file_data import FileData


class IFileDataStore(Protocol):
    """application 레이어가 의존하는 파일 데이터 저장소 인터페이스.

    gui의 FileDataStore(QObject)가 이 프로토콜을 구조적으로 만족한다.
    """

    def get_file(self, file_id: int) -> Optional[FileData]: ...

    def get_all_files(self) -> list[FileData]: ...

    def get_file_id_by_path(self, path: Union[str, Path]) -> Optional[int]: ...

    def get_file_count(self) -> int: ...
