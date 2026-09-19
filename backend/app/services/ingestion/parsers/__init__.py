"""Parsers package for specialized forensic artifact types."""

from app.services.ingestion.parsers.android_log_parser import AndroidLogParser
from app.services.ingestion.parsers.bank_parser import BankParser
from app.services.ingestion.parsers.base import BaseParser
from app.services.ingestion.parsers.cdr_parser import CDRParser
from app.services.ingestion.parsers.email_parser import EmailParser

__all__ = [
    "AndroidLogParser",
    "BankParser",
    "BaseParser",
    "CDRParser",
    "EmailParser",
]
