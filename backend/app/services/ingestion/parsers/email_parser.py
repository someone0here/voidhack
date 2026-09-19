"""Parser for RFC 822 / MIME .eml email evidence files."""

import email
import ipaddress
from email import policy
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import BinaryIO

from app.db.models import EntityType, LinkType
from app.services.ingestion.exceptions import (
    CorruptedFileError,
    EmptyFileError,
    IngestionError,
)
from app.services.ingestion.models import LinkedEntityRef, ParsedRecord, ParserResult
from app.services.ingestion.parsers.base import (
    IPV4_PATTERN,
    BaseParser,
    logger,
    normalize_email,
    normalize_ip,
)


class EmailParser(BaseParser):
    """Parses .eml email files, extracting identities and routing IPs."""

    def parse(self, file_source: str | Path | bytes | BinaryIO) -> ParserResult:
        """Parse .eml file into intermediate normalized records."""
        msg = self._load_email_message(file_source)

        # Extract From
        from_header = msg.get("From", "")
        from_addresses = [addr for _, addr in getaddresses([from_header]) if addr]
        sender_email = normalize_email(from_addresses[0]) if from_addresses else None

        # Extract To & Cc
        to_header = msg.get("To", "")
        cc_header = msg.get("Cc", "")
        recipient_addresses = [
            addr for _, addr in getaddresses([to_header, cc_header]) if addr
        ]
        recipients = [
            norm
            for addr in recipient_addresses
            if (norm := normalize_email(addr)) is not None
        ]

        # Extract Message-ID
        message_id = msg.get("Message-ID", "").strip()

        # Extract Date (parsed for debug logging only)
        date_header = msg.get("Date", "")
        if date_header:
            try:
                parsedate_to_datetime(date_header).replace(tzinfo=None)
            except Exception as e:
                logger.debug(
                    "Failed to parse email Date header '%s': %s", date_header, e
                )

        # Extract Received IP hop chains
        received_headers = msg.get_all("Received", [])
        hop_ips: list[str] = []
        for hdr in received_headers:
            ips = self._extract_ips_from_received_header(hdr)
            for ip in ips:
                norm_ip = normalize_ip(ip)
                if norm_ip and norm_ip not in hop_ips:
                    # Filter loopback
                    try:
                        ip_obj = ipaddress.ip_address(norm_ip)
                        if not ip_obj.is_loopback:
                            hop_ips.append(norm_ip)
                    except ValueError:
                        hop_ips.append(norm_ip)

        if not sender_email and not recipients and not hop_ips:
            raise CorruptedFileError(
                "Email artifact contains no extractable sender, "
                "recipient, or routing IP entities."
            )

        records: list[ParsedRecord] = []
        source_ref = message_id or "email_msg_1"

        # 1. Sender Record
        if sender_email:
            sender_links: list[LinkedEntityRef] = []
            for rcpt in recipients:
                sender_links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.EMAIL_ADDRESS,
                        value=rcpt,
                        link_type=LinkType.DIRECT_COMMUNICATION,
                        confidence_score=0.95,
                    )
                )
            for hop_ip in hop_ips:
                sender_links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.IP_ADDRESS,
                        value=hop_ip,
                        link_type=LinkType.SHARED_IP_SUBNET,
                        confidence_score=0.85,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.EMAIL_ADDRESS,
                    value=sender_email,
                    linked_entities=sender_links,
                    source_row_ref=source_ref,
                )
            )

        # 2. Recipient Records
        for rcpt in recipients:
            rcpt_links: list[LinkedEntityRef] = []
            if sender_email:
                rcpt_links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.EMAIL_ADDRESS,
                        value=sender_email,
                        link_type=LinkType.DIRECT_COMMUNICATION,
                        confidence_score=0.95,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.EMAIL_ADDRESS,
                    value=rcpt,
                    linked_entities=rcpt_links,
                    source_row_ref=source_ref,
                )
            )

        # 3. Hop IP Records
        for hop_ip in hop_ips:
            ip_links: list[LinkedEntityRef] = []
            if sender_email:
                ip_links.append(
                    LinkedEntityRef(
                        entity_type=EntityType.EMAIL_ADDRESS,
                        value=sender_email,
                        link_type=LinkType.SHARED_IP_SUBNET,
                        confidence_score=0.85,
                    )
                )
            records.append(
                ParsedRecord(
                    entity_type=EntityType.IP_ADDRESS,
                    value=hop_ip,
                    linked_entities=ip_links,
                    source_row_ref=source_ref,
                )
            )

        return ParserResult(
            records=records,
            rows_processed=1,
            rows_skipped=0,
            errors=[],
        )

    def _extract_ips_from_received_header(self, header_value: str) -> list[str]:
        """Extract IP addresses from Received header hops."""
        ips: list[str] = []
        matches = IPV4_PATTERN.findall(header_value)
        for match in matches:
            try:
                ipaddress.ip_address(match)
                ips.append(match)
            except ValueError:
                continue
        return ips

    def _load_email_message(
        self, file_source: str | Path | bytes | BinaryIO
    ) -> email.message.EmailMessage:
        """Load and parse email message from source."""
        try:
            if isinstance(file_source, str | Path):
                if isinstance(file_source, str) and not file_source.strip():
                    raise EmptyFileError("Email file path is empty.")
                path = Path(file_source)
                if path.is_dir():
                    raise CorruptedFileError(
                        f"Expected a file path, got directory: {path}"
                    )
                if not path.exists():
                    raise CorruptedFileError(f"Email file not found: {path}")
                if path.stat().st_size == 0:
                    raise EmptyFileError(f"Email file is empty: {path}")

                with open(path, "rb") as f:
                    content = f.read()
                if not content.strip():
                    raise EmptyFileError("Email file is empty.")
                return email.message_from_bytes(content, policy=policy.default)

            elif isinstance(file_source, bytes):
                if not file_source.strip():
                    raise EmptyFileError("Email bytes content is empty.")
                return email.message_from_bytes(file_source, policy=policy.default)

            elif hasattr(file_source, "read"):
                content = file_source.read()
                if isinstance(content, str):
                    if not content.strip():
                        raise EmptyFileError("Email content is empty.")
                    return email.message_from_string(content, policy=policy.default)
                elif isinstance(content, bytes):
                    if not content.strip():
                        raise EmptyFileError("Email content is empty.")
                    return email.message_from_bytes(content, policy=policy.default)
                raise CorruptedFileError("Unrecognized email stream format.")

            raise IngestionError(f"Unsupported file source: {type(file_source)}")

        except (EmptyFileError, CorruptedFileError, IngestionError):
            raise
        except Exception as e:
            raise CorruptedFileError(f"Failed to parse email message: {e}") from e
