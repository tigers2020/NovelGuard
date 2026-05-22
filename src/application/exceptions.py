"""Application-layer exceptions."""


class IndexPersistenceError(Exception):
    """Index repository persistence failed (DB layer)."""


class FileEncodingError(Exception):
    """Encoding detection or decode failed."""


class FileConvertError(Exception):
    """UTF-8 conversion or backup failed."""
