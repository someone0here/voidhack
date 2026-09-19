"""PII masking utilities for investigative briefs.

Ensures that exported judicial and tactical briefs redact sensitive personal
identifiers (phone numbers, bank accounts/UPI handles, device IMEIs) to a
last-4-digits-visible format by default.

Full unredacted values remain preserved in the relational database and queryable
via authenticated drill-down API endpoints.
"""

from app.db.models import EntityType


def mask_phone(phone: str) -> str:
    """Mask a phone number, preserving country code prefix and last 4 digits.

    Examples:
        "+919876543210" -> "+91******3210"
        "9876543210"    -> "******3210"
        "+14155552671"  -> "+1*******2671"
        "123"           -> "123"

    Args:
        phone: Phone number string (e.g. E.164 formatted).

    Returns:
        Redacted phone number with intermediate digits replaced by '*'.
    """
    clean = phone.strip()
    if not clean:
        return clean

    prefix = ""
    digits_part = clean
    if clean.startswith("+"):
        # Handle 1-digit country codes (+1 for US/Canada, +7 for Kazakhstan/Russia)
        if clean.startswith(("+1", "+7")) and len(clean) in (11, 12):
            prefix = clean[:2]
            digits_part = clean[2:]
        elif len(clean) > 3 and clean[1:3].isdigit():
            prefix = clean[:3]
            digits_part = clean[3:]
        elif len(clean) > 2 and clean[1:2].isdigit():
            prefix = clean[:2]
            digits_part = clean[2:]
        else:
            prefix = "+"
            digits_part = clean[1:]

    if len(digits_part) <= 4:
        return f"{prefix}{digits_part}"

    masked_body = "*" * (len(digits_part) - 4) + digits_part[-4:]
    return f"{prefix}{masked_body}"


def mask_account(account: str) -> str:
    """Mask a bank account number or UPI VPA, showing last 4 characters/digits.

    Examples:
        "123456789012"      -> "********9012"
        "mule1@okhdfcbank"   -> "*ule1@okhdfcbank"
        "victim.pay@upi"    -> "******.pay@upi"

    Args:
        account: Account number or UPI handle string.

    Returns:
        Redacted account string.
    """
    clean = account.strip()
    if not clean:
        return clean

    # Handle UPI VPA (e.g., username@bank)
    if "@" in clean:
        user, domain = clean.split("@", 1)
        if len(user) <= 4:
            masked_user = ("*" * (len(user) - 1) + user[-1:]) if len(user) > 1 else "*"
        else:
            masked_user = "*" * (len(user) - 4) + user[-4:]
        return f"{masked_user}@{domain}"

    # Pure bank account number
    if len(clean) <= 4:
        return clean

    return "*" * (len(clean) - 4) + clean[-4:]


def mask_imei(imei: str) -> str:
    """Mask a 14-16 digit hardware IMEI, preserving only the last 4 digits.

    Example:
        "860123456789012" -> "***********9012"

    Args:
        imei: Device IMEI string.

    Returns:
        Redacted IMEI string.
    """
    clean = imei.strip()
    if len(clean) <= 4:
        return clean
    return "*" * (len(clean) - 4) + clean[-4:]


def mask_email(email: str) -> str:
    """Mask an email address, redacting the username portion.

    Example:
        "investigator@agency.gov" -> "i**********r@agency.gov"
        "a@b.com"                  -> "*@b.com"

    Args:
        email: Email address string.

    Returns:
        Redacted email string.
    """
    clean = email.strip()
    if "@" not in clean:
        return clean

    user, domain = clean.split("@", 1)
    if len(user) <= 2:
        masked_user = "*" * len(user)
    else:
        masked_user = user[0] + ("*" * (len(user) - 2)) + user[-1]
    return f"{masked_user}@{domain}"


def mask_identifier(value: str, entity_type: EntityType | str | None = None) -> str:
    """Dispatch masking by entity type or inferred format.

    Args:
        value: Identifier string to mask.
        entity_type: Known EntityType enum value or string representation.

    Returns:
        Properly masked identifier string.
    """
    if not value:
        return value

    type_val = (
        entity_type.value if hasattr(entity_type, "value") else str(entity_type or "")
    )

    if type_val == EntityType.PHONE.value:
        return mask_phone(value)
    elif type_val == EntityType.ACCOUNT.value:
        return mask_account(value)
    elif type_val == EntityType.DEVICE_IMEI.value:
        return mask_imei(value)
    elif type_val == EntityType.EMAIL_ADDRESS.value:
        return mask_email(value)

    # Heuristic inference if entity_type is omitted or generic
    if value.startswith("+") and any(c.isdigit() for c in value):
        return mask_phone(value)
    if "@" in value:
        return mask_email(value)
    if value.isdigit() and len(value) in (14, 15, 16):
        return mask_imei(value)
    if value.isdigit() and len(value) > 4:
        return mask_account(value)

    return value
