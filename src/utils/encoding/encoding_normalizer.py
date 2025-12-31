"""
인코딩 이름 정규화 모듈

인코딩 이름을 표준화하는 기능을 제공합니다.
"""

from utils.constants import DEFAULT_ENCODING

# 인코딩 이름 정규화 매핑
_ENCODING_NORMALIZATION = {
    "utf8": "utf-8",
    "utf-8": "utf-8",
    "euc-kr": "euc-kr",
    "cp949": "cp949",
    "latin1": "iso-8859-1",
    "iso-8859-1": "iso-8859-1",
}


class EncodingNormalizer:
    """인코딩 이름 정규화 클래스.
    
    인코딩 이름을 표준화합니다.
    utf8/utf-8 등 다양한 표기를 통일합니다.
    """
    
    def normalize(self, name: str) -> str:
        """인코딩 이름을 표준화합니다.
        
        utf8/utf-8 등 다양한 표기를 통일합니다.
        
        Args:
            name: 원본 인코딩 이름
        
        Returns:
            표준화된 인코딩 이름
        
        Example:
            >>> normalizer = EncodingNormalizer()
            >>> normalizer.normalize("utf8")
            "utf-8"
            >>> normalizer.normalize("UTF-8")
            "utf-8"
        """
        if not name:
            return DEFAULT_ENCODING
        
        name_lower = name.lower().strip()
        return _ENCODING_NORMALIZATION.get(name_lower, name_lower)

