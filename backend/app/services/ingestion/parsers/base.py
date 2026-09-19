"""Base parser class and normalization utilities for evidentiary artifacts."""

import ipaddress
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import BinaryIO

import pandas as pd
from dateutil import parser as dateutil_parser

from app.services.ingestion.models import ParserResult

logger = logging.getLogger("ingestion.parsers")

# Common regex patterns
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
IPV4_PATTERN = re.compile(
    r"\b(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}\b"
)
MAC_PATTERN = re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b")
IMEI_PATTERN = re.compile(r"\b\d{14,16}\b")


def clean_str(val: object) -> str:
    """Safely convert any value to stripped string, treating NaNs and nulls as empty."""
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s


def normalize_phone(raw: object) -> str | None:
    """Normalize phone numbers to international format where possible."""
    s = clean_str(raw)
    if not s:
        return None

    # Remove brackets, hyphens, spaces, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", s)

    # Handle international prefixes
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif not cleaned.startswith("+"):
        if len(cleaned) == 12 and cleaned.startswith("91"):
            cleaned = "+" + cleaned
        elif len(cleaned) == 10 and cleaned[0] in "6789":
            cleaned = "+91" + cleaned
        elif len(cleaned) == 10:
            # Generic 10 digit number
            cleaned = "+1" + cleaned if cleaned[0] in "23456789" else cleaned

    # Must contain between 7 and 15 digits
    digits_only = re.sub(r"\D", "", cleaned)
    if 7 <= len(digits_only) <= 15:
        return cleaned if cleaned.startswith("+") else f"+{cleaned}"
    return None


def normalize_email(raw: object) -> str | None:
    """Extract and normalize email address to lowercase."""
    s = clean_str(raw)
    if not s:
        return None
    match = EMAIL_PATTERN.search(s)
    if match:
        return match.group(0).lower()
    return None


def normalize_imei(raw: object) -> str | None:
    """Normalize 14-16 digit device IMEI/IMEISV."""
    s = clean_str(raw)
    if not s:
        return None
    digits = re.sub(r"\D", "", s)
    if 14 <= len(digits) <= 16:
        return digits
    return None


def normalize_mac(raw: object) -> str | None:
    """Normalize MAC address to colon-delimited uppercase format."""
    s = clean_str(raw)
    if not s:
        return None
    match = MAC_PATTERN.search(s)
    if match:
        mac_str = match.group(0)
        octets = re.split(r"[:-]", mac_str)
        return ":".join(octet.upper() for octet in octets)
    return None


def normalize_ip(raw: object) -> str | None:
    """Validate and normalize IPv4/IPv6 address."""
    s = clean_str(raw)
    if not s:
        return None
    try:
        ip = ipaddress.ip_address(s)
        return str(ip)
    except ValueError:
        match = IPV4_PATTERN.search(s)
        if match:
            return match.group(0)
        return None


def normalize_account(raw: object) -> str | None:
    """Normalize bank account number or UPI handle."""
    s = clean_str(raw)
    if not s:
        return None
    # If UPI VPA handle (e.g. user@bank)
    if "@" in s:
        return s.lower()
    # If bank account number
    cleaned = re.sub(r"[\s\-]", "", s).upper()
    if len(cleaned) >= 4:
        return cleaned
    return None


def parse_datetime_flexible(raw: object) -> datetime | None:
    """Defensively parse datetimes across diverse formats (ISO, slash, timestamps)."""
    if raw is None or pd.isna(raw):
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None)

    s = clean_str(raw)
    if not s:
        return None

    # Check for unix epoch timestamp
    if s.isdigit():
        try:
            ts = int(s)
            if ts > 1000000000000:  # milliseconds
                ts = ts / 1000.0
            return datetime.utcfromtimestamp(ts)
        except (ValueError, OverflowError, OSError):
            pass

    # Try pandas first
    try:
        parsed = pd.to_datetime(s, format="mixed", errors="coerce")
        if pd.notna(parsed):
            return parsed.to_pydatetime().replace(tzinfo=None)
    except Exception:
        pass

    # Fallback to dateutil parser
    try:
        dt = dateutil_parser.parse(s, fuzzy=True)
        return dt.replace(tzinfo=None)
    except Exception:
        return None


class BaseParser(ABC):
    """Abstract base class for evidentiary artifact parsers."""

    @abstractmethod
    def parse(self, file_source: str | Path | bytes | BinaryIO) -> ParserResult:
        """Parse source evidence artifact into intermediate records.

        Args:
            file_source: Path to file or in-memory binary/text buffer.

        Returns:
            ParserResult containing normalized records and row statistics.

        Raises:
            IngestionError: When file cannot be processed or is severely invalid.
        """
        pass
