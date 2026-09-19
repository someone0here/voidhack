"""Parser for telecom Call Detail Records (CDR) and IP Detail Records (IPDR)."""

import io
from pathlib import Path
from typing import BinaryIO

import pandas as pd

from app.db.models import EntityType, LinkType
from app.services.ingestion.exceptions import (
    CorruptedFileError,
    EmptyFileError,
    IngestionError,
    MissingColumnError,
)
from app.services.ingestion.models import LinkedEntityRef, ParsedRecord, ParserResult
from app.services.ingestion.parsers.base import (
    BaseParser,
    clean_str,
    logger,
    normalize_imei,
    normalize_ip,
    normalize_phone,
    parse_datetime_flexible,
)

# Column alias mappings (lowercased)
CALLER_ALIASES = {
    "caller",
    "calling_number",
    "source_number",
    "caller_msisdn",
    "caller_phone",
    "ani",
    "from_number",
    "originating_number",
    "a_party",
    "calling_no",
}
CALLEE_ALIASES = {
    "callee",
    "called_number",
    "destination_number",
    "dialed_number",
    "dnis",
    "to_number",
    "terminating_number",
    "b_party",
    "called_no",
}
IMEI_ALIASES = {
    "imei",
    "device_imei",
    "caller_imei",
    "source_imei",
    "imei_number",
    "first_imei",
}
TIMESTAMP_ALIASES = {
    "timestamp",
    "call_date",
    "call_time",
    "start_time",
    "datetime",
    "date_time",
    "time",
    "event_time",
}
IP_ALIASES = {
    "ip",
    "ip_address",
    "source_ip",
    "client_ip",
    "dest_ip",
    "ipdr_ip",
}


class CDRParser(BaseParser):
    """Parses telecom CDR and IPDR CSV / Excel dumps."""

    def parse(self, file_source: str | Path | bytes | BinaryIO) -> ParserResult:
        """Parse CDR/IPDR file into normalized records."""
        df = self._load_dataframe(file_source)

        if df.empty:
            raise EmptyFileError("CDR/IPDR file contains no data rows.")

        col_map = self._resolve_columns(df)
        if not ({"caller", "callee", "imei", "ip"} & set(col_map.keys())):
            cols = list(df.columns)
            raise MissingColumnError(
                f"CDR/IPDR file missing identifier columns. Found: {cols}"
            )

        records: list[ParsedRecord] = []
        rows_processed = 0
        rows_skipped = 0
        errors: list[str] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            row_ref = f"row_{row_num}"

            # Extract raw values using mapped columns
            raw_caller = row.get(col_map["caller"]) if "caller" in col_map else None
            raw_callee = row.get(col_map["callee"]) if "callee" in col_map else None
            raw_imei = row.get(col_map["imei"]) if "imei" in col_map else None
            raw_ip = row.get(col_map["ip"]) if "ip" in col_map else None
            raw_timestamp = (
                row.get(col_map["timestamp"]) if "timestamp" in col_map else None
            )

            # Normalize entities
            caller = normalize_phone(raw_caller)
            callee = normalize_phone(raw_callee)
            imei = normalize_imei(raw_imei)
            ip = normalize_ip(raw_ip)
            _ = parse_datetime_flexible(raw_timestamp)

            if not any([caller, callee, imei, ip]):
                skip_msg = f"Row {row_num} skipped: no valid phone, IMEI, or IP found."
                logger.warning(skip_msg)
                errors.append(skip_msg)
                rows_skipped += 1
                continue

            rows_processed += 1

            # Build inter-record linkages
            # 1. Caller record
            if caller:
                caller_links: list[LinkedEntityRef] = []
                if imei:
                    caller_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.DEVICE_IMEI,
                            value=imei,
                            link_type=LinkType.SHARED_IMEI,
                            confidence_score=0.95,
                        )
                    )
                if callee:
                    caller_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=callee,
                            link_type=LinkType.DIRECT_COMMUNICATION,
                            confidence_score=0.90,
                        )
                    )
                if ip:
                    caller_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.IP_ADDRESS,
                            value=ip,
                            link_type=LinkType.SHARED_IP_SUBNET,
                            confidence_score=0.85,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.PHONE,
                        value=caller,
                        linked_entities=caller_links,
                        source_row_ref=row_ref,
                    )
                )

            # 2. Callee record
            if callee:
                callee_links: list[LinkedEntityRef] = []
                if caller:
                    callee_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=caller,
                            link_type=LinkType.DIRECT_COMMUNICATION,
                            confidence_score=0.90,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.PHONE,
                        value=callee,
                        linked_entities=callee_links,
                        source_row_ref=row_ref,
                    )
                )

            # 3. IMEI record
            if imei:
                imei_links: list[LinkedEntityRef] = []
                if caller:
                    imei_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=caller,
                            link_type=LinkType.SHARED_IMEI,
                            confidence_score=0.95,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.DEVICE_IMEI,
                        value=imei,
                        linked_entities=imei_links,
                        source_row_ref=row_ref,
                    )
                )

            # 4. IP record
            if ip:
                ip_links: list[LinkedEntityRef] = []
                if caller:
                    ip_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=caller,
                            link_type=LinkType.SHARED_IP_SUBNET,
                            confidence_score=0.85,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.IP_ADDRESS,
                        value=ip,
                        linked_entities=ip_links,
                        source_row_ref=row_ref,
                    )
                )

        return ParserResult(
            records=records,
            rows_processed=rows_processed,
            rows_skipped=rows_skipped,
            errors=errors,
        )

    def _load_dataframe(
        self, file_source: str | Path | bytes | BinaryIO
    ) -> pd.DataFrame:
        """Load tabular data safely from path, bytes, or buffer."""
        try:
            if isinstance(file_source, str | Path):
                if isinstance(file_source, str) and not file_source.strip():
                    raise EmptyFileError("File path or content is empty.")
                path = Path(file_source)
                if path.is_dir():
                    raise CorruptedFileError(
                        f"Expected a file path, got directory: {path}"
                    )
                if not path.exists():
                    raise CorruptedFileError(f"Evidence file not found: {path}")
                if path.stat().st_size == 0:
                    raise EmptyFileError(f"Evidence file is empty: {path}")

                ext = path.suffix.lower()
                if ext in {".xlsx", ".xls"}:
                    try:
                        return pd.read_excel(path)
                    except ImportError as err:
                        raise IngestionError(
                            "Excel parsing requires openpyxl. "
                            "Convert to CSV or install openpyxl."
                        ) from err
                # Default to CSV parser with flexible encoding
                try:
                    return pd.read_csv(path, dtype=str, index_col=False)
                except UnicodeDecodeError:
                    return pd.read_csv(
                        path, dtype=str, index_col=False, encoding="latin1"
                    )

            elif isinstance(file_source, bytes):
                if len(file_source) == 0:
                    raise EmptyFileError("Provided file byte content is empty.")
                # Try CSV first
                try:
                    return pd.read_csv(
                        io.BytesIO(file_source), dtype=str, index_col=False
                    )
                except Exception:
                    try:
                        return pd.read_excel(io.BytesIO(file_source))
                    except Exception as err:
                        raise CorruptedFileError(
                            f"Failed to parse tabular bytes as CSV or Excel: {err}"
                        ) from err

            elif hasattr(file_source, "read"):
                content = file_source.read()
                if isinstance(content, str):
                    if not content.strip():
                        raise EmptyFileError("File stream is empty.")
                    return pd.read_csv(io.StringIO(content), dtype=str, index_col=False)
                elif isinstance(content, bytes):
                    return self._load_dataframe(content)
                else:
                    raise CorruptedFileError("Unrecognized file stream contents.")

            raise IngestionError(f"Unsupported file source type: {type(file_source)}")

        except (EmptyFileError, MissingColumnError, IngestionError):
            raise
        except Exception as e:
            raise CorruptedFileError(f"Failed to read CDR file: {e}") from e

    def _resolve_columns(self, df: pd.DataFrame) -> dict[str, str]:
        """Resolve canonical column names from DataFrame headers."""
        mapping: dict[str, str] = {}
        for col in df.columns:
            normalized_col = clean_str(col).lower().replace(" ", "_").replace("-", "_")
            if normalized_col in CALLER_ALIASES and "caller" not in mapping:
                mapping["caller"] = col
            elif normalized_col in CALLEE_ALIASES and "callee" not in mapping:
                mapping["callee"] = col
            elif normalized_col in IMEI_ALIASES and "imei" not in mapping:
                mapping["imei"] = col
            elif normalized_col in TIMESTAMP_ALIASES and "timestamp" not in mapping:
                mapping["timestamp"] = col
            elif normalized_col in IP_ALIASES and "ip" not in mapping:
                mapping["ip"] = col
        return mapping
