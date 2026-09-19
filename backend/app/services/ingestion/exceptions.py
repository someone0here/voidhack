"""Exceptions for forensic artifact ingestion and parsing."""


class IngestionError(Exception):
    """Base exception raised for unrecoverable errors during artifact ingestion."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class UnsupportedFormatError(IngestionError):
    """Raised when an artifact has an unrecognized or unsupported format."""

    pass


class CorruptedFileError(IngestionError):
    """Raised when an artifact file is corrupted, unreadable, or truncated."""

    pass


class EmptyFileError(IngestionError):
    """Raised when an ingested artifact file contains no data."""

    pass


class MissingColumnError(IngestionError):
    """Raised when critical required columns are absent from tabular evidence."""

    pass
