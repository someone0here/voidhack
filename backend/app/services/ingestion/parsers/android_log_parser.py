"""Parser for Android forensic extraction logs (JSON and plaintext logcat)."""

import json
import re
from pathlib import Path
from typing import Any, BinaryIO

from app.db.models import EntityType, LinkType
from app.services.ingestion.exceptions import (
    CorruptedFileError,
    EmptyFileError,
    IngestionError,
)
from app.services.ingestion.models import LinkedEntityRef, ParsedRecord, ParserResult
from app.services.ingestion.parsers.base import (
    IMEI_PATTERN,
    IPV4_PATTERN,
    MAC_PATTERN,
    BaseParser,
    normalize_imei,
    normalize_ip,
    normalize_mac,
    normalize_phone,
)

PACKAGE_PATTERN = re.compile(r"\b(?:[a-zA-Z_][a-zA-Z0-9_]*\.)+[a-zA-Z_][a-zA-Z0-9_]*\b")


class AndroidLogParser(BaseParser):
    """Parses Android system and extraction logs in JSON or plaintext logcat format."""

    def parse(self, file_source: str | Path | bytes | BinaryIO) -> ParserResult:
        """Parse Android forensic log file into normalized records."""
        raw_text = self._load_content(file_source)
        if not raw_text.strip():
            raise EmptyFileError("Android log file is empty.")

        # Try parsing as JSON first
        try:
            json_data = json.loads(raw_text)
            return self._parse_json(json_data)
        except json.JSONDecodeError:
            # Fall back to text logcat parser
            return self._parse_text(raw_text)

    def _parse_json(self, data: Any) -> ParserResult:
        """Parse structured JSON Android extraction dumps."""
        extracted_imeis: set[str] = set()
        extracted_macs: set[str] = set()
        extracted_ips: set[str] = set()
        extracted_phones: set[str] = set()
        packages: set[str] = set()
        rows_processed = 0

        def traverse(node: Any) -> None:
            nonlocal rows_processed
            if isinstance(node, dict):
                rows_processed += 1
                for k, v in node.items():
                    k_lower = str(k).lower()
                    if "imei" in k_lower:
                        if imei := normalize_imei(v):
                            extracted_imeis.add(imei)
                    elif "mac" in k_lower:
                        if mac := normalize_mac(v):
                            extracted_macs.add(mac)
                    elif "ip" in k_lower or "host" in k_lower:
                        if ip := normalize_ip(v):
                            extracted_ips.add(ip)
                    elif "phone" in k_lower or "msisdn" in k_lower:
                        if phone := normalize_phone(v):
                            extracted_phones.add(phone)
                    elif "package" in k_lower or "app" in k_lower:
                        s = str(v).strip()
                        if PACKAGE_PATTERN.match(s):
                            packages.add(s)
                    traverse(v)
            elif isinstance(node, list):
                for item in node:
                    traverse(item)
            elif isinstance(node, str):
                if imei_match := IMEI_PATTERN.search(node):
                    if imei := normalize_imei(imei_match.group(0)):
                        extracted_imeis.add(imei)
                if mac_match := MAC_PATTERN.search(node):
                    if mac := normalize_mac(mac_match.group(0)):
                        extracted_macs.add(mac)
                if ip_match := IPV4_PATTERN.search(node):
                    if ip := normalize_ip(ip_match.group(0)):
                        extracted_ips.add(ip)

        traverse(data)

        if not (extracted_imeis or extracted_macs or extracted_ips or extracted_phones):
            raise CorruptedFileError(
                "No extractable device identifiers (IMEI, MAC, IP, Phone) "
                "found in JSON log."
            )

        return self._build_cross_linked_records(
            imeis=extracted_imeis,
            macs=extracted_macs,
            ips=extracted_ips,
            phones=extracted_phones,
            rows_processed=max(rows_processed, 1),
            rows_skipped=0,
            source_ref="android_json_extraction",
        )

    def _parse_text(self, text: str) -> ParserResult:
        """Parse raw logcat or plaintext forensic extraction dump."""
        lines = text.splitlines()
        extracted_imeis: set[str] = set()
        extracted_macs: set[str] = set()
        extracted_ips: set[str] = set()
        extracted_phones: set[str] = set()
        rows_processed = 0
        rows_skipped = 0

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            found_any = False
            for match in IMEI_PATTERN.finditer(line_str):
                if imei := normalize_imei(match.group(0)):
                    extracted_imeis.add(imei)
                    found_any = True

            for match in MAC_PATTERN.finditer(line_str):
                if mac := normalize_mac(match.group(0)):
                    extracted_macs.add(mac)
                    found_any = True

            for match in IPV4_PATTERN.finditer(line_str):
                if ip := normalize_ip(match.group(0)):
                    extracted_ips.add(ip)
                    found_any = True

            # Regex search for phone numbers in logs
            phone_match = re.search(
                r"(?:phone|msisdn|tel)[:=]\s*(\+?\d{10,15})", line_str, re.IGNORECASE
            )
            if phone_match:
                if phone := normalize_phone(phone_match.group(1)):
                    extracted_phones.add(phone)
                    found_any = True

            if found_any:
                rows_processed += 1
            else:
                rows_skipped += 1

        if not (extracted_imeis or extracted_macs or extracted_ips or extracted_phones):
            raise CorruptedFileError(
                "No extractable device identifiers (IMEI, MAC, IP, Phone) "
                "found in text log."
            )

        return self._build_cross_linked_records(
            imeis=extracted_imeis,
            macs=extracted_macs,
            ips=extracted_ips,
            phones=extracted_phones,
            rows_processed=rows_processed,
            rows_skipped=rows_skipped,
            source_ref="android_logcat_dump",
        )

    def _build_cross_linked_records(
        self,
        imeis: set[str],
        macs: set[str],
        ips: set[str],
        phones: set[str],
        rows_processed: int,
        rows_skipped: int,
        source_ref: str,
    ) -> ParserResult:
        """Construct inter-connected ParsedRecord entities with device links."""
        records: list[ParsedRecord] = []

        # 1. IMEI Records
        for imei in imeis:
            links: list[LinkedEntityRef] = []
            for mac in macs:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.MAC_ADDRESS,
                        value=mac,
                        link_type=LinkType.SHARED_MAC,
                        confidence_score=0.98,
                    )
                )
            for ip in ips:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.IP_ADDRESS,
                        value=ip,
                        link_type=LinkType.SHARED_IP_SUBNET,
                        confidence_score=0.90,
                    )
                )
            for phone in phones:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.PHONE,
                        value=phone,
                        link_type=LinkType.SHARED_IMEI,
                        confidence_score=0.95,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.DEVICE_IMEI,
                    value=imei,
                    linked_entities=links,
                    source_row_ref=source_ref,
                )
            )

        # 2. MAC Records
        for mac in macs:
            links = []
            for imei in imeis:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.DEVICE_IMEI,
                        value=imei,
                        link_type=LinkType.SHARED_IMEI,
                        confidence_score=0.98,
                    )
                )
            for ip in ips:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.IP_ADDRESS,
                        value=ip,
                        link_type=LinkType.SHARED_IP_SUBNET,
                        confidence_score=0.90,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.MAC_ADDRESS,
                    value=mac,
                    linked_entities=links,
                    source_row_ref=source_ref,
                )
            )

        # 3. IP Records
        for ip in ips:
            links = []
            for imei in imeis:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.DEVICE_IMEI,
                        value=imei,
                        link_type=LinkType.SHARED_IMEI,
                        confidence_score=0.90,
                    )
                )
            for mac in macs:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.MAC_ADDRESS,
                        value=mac,
                        link_type=LinkType.SHARED_MAC,
                        confidence_score=0.90,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.IP_ADDRESS,
                    value=ip,
                    linked_entities=links,
                    source_row_ref=source_ref,
                )
            )

        # 4. Phone Records
        for phone in phones:
            links = []
            for imei in imeis:
                links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.DEVICE_IMEI,
                        value=imei,
                        link_type=LinkType.SHARED_IMEI,
                        confidence_score=0.95,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.PHONE,
                    value=phone,
                    linked_entities=links,
                    source_row_ref=source_ref,
                )
            )

        return ParserResult(
            records=records,
            rows_processed=rows_processed,
            rows_skipped=rows_skipped,
            errors=[],
        )

    def _load_content(self, file_source: str | Path | bytes | BinaryIO) -> str:
        """Load text content safely from path, bytes, or buffer."""
        try:
            if isinstance(file_source, str | Path):
                if isinstance(file_source, str) and not file_source.strip():
                    raise EmptyFileError("Android log file is empty.")
                path = Path(file_source)
                if path.is_dir():
                    raise CorruptedFileError(
                        f"Expected a file path, got directory: {path}"
                    )
                if not path.exists():
                    raise CorruptedFileError(f"Log file not found: {path}")
                if path.stat().st_size == 0:
                    raise EmptyFileError(f"Log file is empty: {path}")
                return path.read_text(encoding="utf-8", errors="replace")

            elif isinstance(file_source, bytes):
                if not file_source.strip():
                    raise EmptyFileError("Android log file is empty.")
                return file_source.decode("utf-8", errors="replace")

            elif hasattr(file_source, "read"):
                content = file_source.read()
                if isinstance(content, bytes):
                    return content.decode("utf-8", errors="replace")
                return str(content)

            raise IngestionError(f"Unsupported file source: {type(file_source)}")

        except (EmptyFileError, CorruptedFileError, IngestionError):
            raise
        except Exception as e:
            raise CorruptedFileError(f"Failed to read Android log: {e}") from e
