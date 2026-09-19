"""Parser for Bank and UPI settlement sheets."""

import io
import re
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
    normalize_account,
    normalize_phone,
    parse_datetime_flexible,
)

SENDER_ALIASES = {
    "sender_account",
    "sender_acc",
    "remitter_account",
    "from_account",
    "sender",
    "debit_account",
    "source_account",
    "remitter",
}
RECEIVER_ALIASES = {
    "receiver_account",
    "receiver_acc",
    "beneficiary_account",
    "to_account",
    "receiver",
    "credit_account",
    "destination_account",
    "beneficiary",
}
UPI_ALIASES = {
    "upi_handle",
    "upi_id",
    "vpa",
    "virtual_address",
    "upi",
    "payee_vpa",
    "payer_vpa",
    "beneficiary_upi",
}
AMOUNT_ALIASES = {
    "amount",
    "txn_amount",
    "transaction_amount",
    "value",
    "amt",
    "inr",
}
TIMESTAMP_ALIASES = {
    "timestamp",
    "txn_date",
    "transaction_date",
    "date",
    "datetime",
    "time",
    "txn_time",
}


class BankParser(BaseParser):
    """Parses Bank and UPI settlement ledgers from CSV or Excel files."""

    def parse(self, file_source: str | Path | bytes | BinaryIO) -> ParserResult:
        """Parse Bank/UPI transaction sheet into normalized records."""
        df = self._load_dataframe(file_source)

        if df.empty:
            raise EmptyFileError("Bank/UPI sheet contains no data rows.")

        col_map = self._resolve_columns(df)
        if not ({"sender", "receiver", "upi"} & set(col_map.keys())):
            cols = list(df.columns)
            raise MissingColumnError(
                f"Bank/UPI sheet missing required columns. Found: {cols}"
            )

        records: list[ParsedRecord] = []
        rows_processed = 0
        rows_skipped = 0
        errors: list[str] = []

        for row_num, (_, row) in enumerate(df.iterrows(), start=1):
            row_ref = f"row_{row_num}"

            raw_sender = row.get(col_map["sender"]) if "sender" in col_map else None
            raw_receiver = (
                row.get(col_map["receiver"]) if "receiver" in col_map else None
            )
            raw_upi = row.get(col_map["upi"]) if "upi" in col_map else None
            raw_timestamp = (
                row.get(col_map["timestamp"]) if "timestamp" in col_map else None
            )
            raw_amount = row.get(col_map["amount"]) if "amount" in col_map else None

            sender = normalize_account(raw_sender)
            receiver = normalize_account(raw_receiver)
            upi = normalize_account(raw_upi)
            _ = parse_datetime_flexible(raw_timestamp)
            _ = self._clean_amount(raw_amount)

            if not any([sender, receiver, upi]):
                skip_msg = (
                    f"Row {row_num} skipped: missing valid sender, receiver, or UPI."
                )
                logger.warning(skip_msg)
                errors.append(skip_msg)
                rows_skipped += 1
                continue

            rows_processed += 1

            # Detect phone number in UPI handle (e.g. 9811122233@bank)
            phone_from_upi: str | None = None
            if upi and "@" in upi:
                prefix = upi.split("@")[0]
                phone_from_upi = normalize_phone(prefix)

            # 1. Sender record
            if sender:
                sender_links: list[LinkedEntityRef] = []
                if receiver:
                    sender_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=receiver,
                            link_type=LinkType.TRANSACTION,
                            confidence_score=0.95,
                        )
                    )
                if upi:
                    sender_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=upi,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.90,
                        )
                    )
                if phone_from_upi:
                    sender_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=phone_from_upi,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.88,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.ACCOUNT,
                        value=sender,
                        linked_entities=sender_links,
                        source_row_ref=row_ref,
                    )
                )

            # 2. Receiver record
            if receiver:
                receiver_links: list[LinkedEntityRef] = []
                if sender:
                    receiver_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=sender,
                            link_type=LinkType.TRANSACTION,
                            confidence_score=0.95,
                        )
                    )
                if upi:
                    receiver_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=upi,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.95,
                        )
                    )
                if phone_from_upi:
                    receiver_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=phone_from_upi,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.92,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.ACCOUNT,
                        value=receiver,
                        linked_entities=receiver_links,
                        source_row_ref=row_ref,
                    )
                )

            # 3. UPI handle record
            if upi:
                upi_links: list[LinkedEntityRef] = []
                if receiver:
                    upi_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=receiver,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.95,
                        )
                    )
                if sender:
                    upi_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=sender,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.90,
                        )
                    )
                if phone_from_upi:
                    upi_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.PHONE,
                            value=phone_from_upi,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.98,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.ACCOUNT,
                        value=upi,
                        linked_entities=upi_links,
                        source_row_ref=row_ref,
                    )
                )

            # 4. Phone entity extracted from UPI handle
            if phone_from_upi:
                p_links: list[LinkedEntityRef] = [
                    LinkedEntityRef(
                        entity_type=EntityType.ACCOUNT,
                        value=upi,  # type: ignore[arg-type]
                        link_type=LinkType.SHARED_UPI_HANDLE,
                        confidence_score=0.98,
                    )
                ]
                if receiver:
                    p_links.append(
                        LinkedEntityRef(
                            entity_type=EntityType.ACCOUNT,
                            value=receiver,
                            link_type=LinkType.SHARED_UPI_HANDLE,
                            confidence_score=0.92,
                        )
                    )
                records.append(
                    ParsedRecord(
                        entity_type=EntityType.PHONE,
                        value=phone_from_upi,
                        linked_entities=p_links,
                        source_row_ref=row_ref,
                    )
                )

        return ParserResult(
            records=records,
            rows_processed=rows_processed,
            rows_skipped=rows_skipped,
            errors=errors,
        )

    def _clean_amount(self, raw: object) -> float | None:
        """Sanitize numerical amounts removing currency symbols and formatting."""
        s = clean_str(raw)
        if not s:
            return None
        # Remove currency symbols and formatting: ₹, $, commas, whitespace
        cleaned = re.sub(r"[₹\$,\sINRinrUSDusd]", "", s)
        try:
            return float(cleaned)
        except ValueError:
            return None

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
                try:
                    return pd.read_csv(path, dtype=str, index_col=False)
                except UnicodeDecodeError:
                    return pd.read_csv(
                        path, dtype=str, index_col=False, encoding="latin1"
                    )

            elif isinstance(file_source, bytes):
                if len(file_source) == 0:
                    raise EmptyFileError("Provided file byte content is empty.")
                try:
                    return pd.read_csv(
                        io.BytesIO(file_source), dtype=str, index_col=False
                    )
                except Exception:
                    try:
                        return pd.read_excel(io.BytesIO(file_source))
                    except Exception as err:
                        raise CorruptedFileError(
                            f"Failed to parse bytes as CSV or Excel: {err}"
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
            raise CorruptedFileError(f"Failed to read Bank/UPI file: {e}") from e

    def _resolve_columns(self, df: pd.DataFrame) -> dict[str, str]:
        """Resolve canonical column names from DataFrame headers."""
        mapping: dict[str, str] = {}
        for col in df.columns:
            normalized_col = clean_str(col).lower().replace(" ", "_").replace("-", "_")
            if normalized_col in SENDER_ALIASES and "sender" not in mapping:
                mapping["sender"] = col
            elif normalized_col in RECEIVER_ALIASES and "receiver" not in mapping:
                mapping["receiver"] = col
            elif normalized_col in UPI_ALIASES and "upi" not in mapping:
                mapping["upi"] = col
            elif normalized_col in AMOUNT_ALIASES and "amount" not in mapping:
                mapping["amount"] = col
            elif normalized_col in TIMESTAMP_ALIASES and "timestamp" not in mapping:
                mapping["timestamp"] = col
        return mapping
