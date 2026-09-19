"""Cryptographic hashing utilities for evidentiary artifacts."""

import hashlib
from pathlib import Path
from typing import BinaryIO

DEFAULT_CHUNK_SIZE = 65536  # 64 KB chunks


def compute_sha256(
    file_source: str | Path | bytes | BinaryIO,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
) -> str:
    """Compute deterministic SHA-256 hash of file bytes using chunked streaming.

    To ensure forensic readiness and low memory overhead when handling large
    evidentiary dumps (e.g., multi-gigabyte telecom CDRs or full mobile disk
    extractions), this function reads data in fixed-size chunks rather than loading
    the full payload into RAM.

    For seekable binary stream buffers (such as SpooledTemporaryFile or BytesIO),
    the initial read position is recorded and rewound to byte 0 prior to return,
    allowing downstream parsers to consume the stream without exhaustion.

    Args:
        file_source: File path (str/Path), raw bytes, or readable binary stream.
        chunk_size: Byte size of chunks read into memory per iteration (default 64KB).

    Returns:
        Lowercase hexadecimal SHA-256 digest string (64 characters).

    Raises:
        FileNotFoundError: If a file path is provided but does not exist on disk.
        ValueError: If chunk_size is less than 1 or if file_source type is unsupported.
    """
    if chunk_size < 1:
        raise ValueError(f"chunk_size must be positive, got {chunk_size}")

    hasher = hashlib.sha256()

    if isinstance(file_source, bytes):
        for offset in range(0, len(file_source), chunk_size):
            hasher.update(file_source[offset : offset + chunk_size])
        return hasher.hexdigest()

    if isinstance(file_source, str | Path):
        file_path = Path(file_source)
        if not file_path.is_file():
            raise FileNotFoundError(f"Evidence file not found on disk: {file_path}")
        with open(file_path, "rb") as f:
            while chunk := f.read(chunk_size):
                hasher.update(chunk)
        return hasher.hexdigest()

    if hasattr(file_source, "read"):
        initial_pos: int | None = None
        if hasattr(file_source, "seek") and hasattr(file_source, "tell"):
            try:
                initial_pos = file_source.tell()
                file_source.seek(0)
            except Exception:
                initial_pos = None

        try:
            while chunk := file_source.read(chunk_size):
                if isinstance(chunk, str):
                    chunk = chunk.encode("utf-8")
                hasher.update(chunk)
        finally:
            if initial_pos is not None and hasattr(file_source, "seek"):
                try:
                    file_source.seek(0)
                except Exception:
                    pass

        return hasher.hexdigest()

    raise ValueError(f"Unsupported file_source type: {type(file_source).__name__}")
