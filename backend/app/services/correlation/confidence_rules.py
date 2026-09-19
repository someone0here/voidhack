"""Config-driven confidence weighting rules and signal compounding logic.

===============================================================================
JUDICIAL & FORENSIC EVIDENTIARY WEIGHTING RATIONALE
===============================================================================
In cyber fraud and syndicate financial crime investigations, entity linkage
is not a binary condition. In court and operational field arrests, false links
have catastrophic real-world consequences for innocent citizens whose identifiers
coincidentally brush against a criminal network.

Raw graph connectivity is therefore insufficient: weighting and probabilistic
signal provenance matter far more than mere graph topology.

This module establishes deterministic, transparent, config-driven confidence
weights for each link type. Every constant below reflects empirical forensic
attribution confidence under telecommunications and banking mechanics in India.
===============================================================================
"""

from collections.abc import Sequence
from enum import Enum
from typing import Final

from app.db.models import LinkType

# -----------------------------------------------------------------------------
# Named Confidence Weight Constants
# -----------------------------------------------------------------------------

# Physical Device Hardware Nexus (0.85):
# An IMEI (International Mobile Equipment Identity) is an immutable hardware
# identifier burned into the baseband processor of a mobile handset. In cyber fraud
# investigations, when two phone numbers or accounts share the same physical IMEI
# (especially on low-overall-traffic or burner devices), this indicates physical
# possession or operational sharing of the exact same mobile device. The false-positive
# rate is exceptionally low (confined almost entirely to rare counterfeit dual-SIM
# clone chips), providing near-conclusive physical attribution.
CONFIDENCE_SHARED_IMEI: Final[float] = 0.85

# Financial Beneficiary & VPA Control Nexus (0.80):
# Virtual Payment Addresses (VPAs / UPI handles) in the Indian Unified Payments
# Interface ecosystem are tied directly to verified KYC bank accounts. When multiple
# transactions or suspects route through a shared UPI handle as a recurring beneficiary,
# it represents direct economic collusion and synchronized cash funneling through
# the same money mule or aggregator node.
CONFIDENCE_SHARED_UPI_HANDLE: Final[float] = 0.80

# Ledger Transaction Nexus (0.75):
# Direct bank ledger transfers (IMPS/NEFT/RTGS/UPI) between accounts demonstrate an
# unambiguous flow of illicit funds from sender to receiver. While account takeovers
# or intermediary commercial payments can occasionally occur, verified banking
# transactions establish strong evidentiary causality in layering money trails.
CONFIDENCE_TRANSACTION: Final[float] = 0.75

# Direct Telecommunication Nexus (0.70):
# Direct CDR bilateral telecommunications (voice calls, SMS messages) between
# phone entities demonstrate active, two-way operational coordination between parties.
CONFIDENCE_DIRECT_COMMUNICATION: Final[float] = 0.70

# Local Physical Link-Layer Nexus (0.60):
# A Media Access Control (MAC) address identifies a physical network interface card
# on local area networks (e.g., shared Wi-Fi hotspot or tethering device). While highly
# specific in local environments, modern mobile operating systems (Android 10+, iOS 14+)
# frequently employ randomized MAC addresses for privacy on non-home Wi-Fi networks,
# moderating its raw evidentiary certainty compared to hardware IMEIs.
CONFIDENCE_SHARED_MAC: Final[float] = 0.60

# Circumstantial Co-Occurrence Nexus (0.40):
# Extracted from shared spatial or temporal logs (such as simultaneous registration
# or cell-tower azimuth overlap) without explicit direct communication or hardware
# linkage. Represents weak circumstantial association.
CONFIDENCE_CO_OCCURRENCE: Final[float] = 0.40

# Network Prefix / Carrier-Grade NAT (CGNAT) Nexus (0.30):
# In modern cellular (4G/5G) and broadband ISP networks, thousands of civilian mobile
# subscribers share a single public IPv4 address or /24 subnet via Carrier-Grade NAT.
# Consequently, an isolated or lone shared IP subnet provides weak circumstantial
# evidence that must never be treated as definitive attribution on its own.
CONFIDENCE_SHARED_IP_SUBNET: Final[float] = 0.30

# Baseline Weak Signal Threshold:
# Links with individual confidence scores strictly below 0.50 are classified as
# "Weak" circumstantial signals (e.g., shared IP subnet or co-occurrence).
WEAK_SIGNAL_THRESHOLD: Final[float] = 0.50

# Default confidence for unrecognized or generic link types:
CONFIDENCE_DEFAULT: Final[float] = 0.50


# -----------------------------------------------------------------------------
# Config-Driven Weighting Table
# -----------------------------------------------------------------------------

LINK_TYPE_CONFIDENCE: Final[dict[str, float]] = {
    LinkType.SHARED_IMEI.value: CONFIDENCE_SHARED_IMEI,
    LinkType.SHARED_UPI_HANDLE.value: CONFIDENCE_SHARED_UPI_HANDLE,
    LinkType.TRANSACTION.value: CONFIDENCE_TRANSACTION,
    LinkType.DIRECT_COMMUNICATION.value: CONFIDENCE_DIRECT_COMMUNICATION,
    LinkType.SHARED_MAC.value: CONFIDENCE_SHARED_MAC,
    LinkType.CO_OCCURRENCE.value: CONFIDENCE_CO_OCCURRENCE,
    LinkType.SHARED_IP_SUBNET.value: CONFIDENCE_SHARED_IP_SUBNET,
}


def get_link_confidence(link_type: LinkType | str) -> float:
    """Retrieve the config-driven confidence score for a given link type.

    Args:
        link_type: LinkType enum instance or string identifier.

    Returns:
        Deterministic confidence weight in the range [0.0, 1.0].
    """
    key = link_type.value if isinstance(link_type, Enum) else str(link_type).lower()
    return LINK_TYPE_CONFIDENCE.get(key, CONFIDENCE_DEFAULT)


# -----------------------------------------------------------------------------
# Signal Compounding Logic
# -----------------------------------------------------------------------------


def compound_weak_signals(weights: Sequence[float]) -> float:
    r"""Escalate combined confidence for multiple independent weak signals (< 0.50).

    Formula:
        C_combined = 1 - \prod_{i=1}^{k} (1 - w_i)

    Mathematical rationale:
        Treats independent weak evidentiary observations as non-redundant probabilistic
        corroboration. If each weak signal carries an independent probability w_i of
        signaling a genuine investigative link, the probability that ALL
        observed signals are false coincidences is \prod_{i=1}^k (1 - w_i).
        Therefore, at least one represents a true operational nexus;
        the complement: 1 - \prod_{i=1}^k (1 - w_i).

        Example:
          Two independent shared IP subnet links (0.30 each):
            1 - (1 - 0.30) * (1 - 0.30) = 1 - 0.70 * 0.70 = 1 - 0.49 = 0.51 ("Medium")
          Three independent shared IP subnet links (0.30 each):
            1 - 0.70^3 = 1 - 0.343 = 0.657 ("Medium")
          Five independent shared IP subnet links (0.30 each):
            1 - 0.70^5 = 1 - 0.168 = 0.832 ("Strong")

    Args:
        weights: Sequence of float confidence scores.

    Returns:
        Compounded confidence score in [0.0, 1.0], rounded to 4 decimal places.
    """

    if not weights:
        return 0.0
    if len(weights) == 1:
        return float(weights[0])

    product = 1.0
    for w in weights:
        clamped = min(max(float(w), 0.0), 1.0)
        product *= 1.0 - clamped

    return min(max(round(1.0 - product, 4), 0.0), 1.0)


def combine_confidences(weights: Sequence[float]) -> float:
    r"""Combine multiple link confidence scores between the same two entities.

    Rule:
      - If all signals are weak (< 0.50 individually), escalate the combined
        confidence using the compounding formula: 1 - \prod(1 - w_i).
      - If one or more signals are already medium or strong (>= 0.50), the dominant
        signal governs the link, compounded with any cumulative weak evidence if
        the compounded weak signals exceed the dominant weight.

    Args:
        weights: Sequence of individual link confidence scores.

    Returns:
        Final combined confidence score in [0.0, 1.0].
    """

    if not weights:
        return 0.0
    if len(weights) == 1:
        return float(weights[0])

    weak_signals = [float(w) for w in weights if float(w) < WEAK_SIGNAL_THRESHOLD]
    strong_or_medium = [float(w) for w in weights if float(w) >= WEAK_SIGNAL_THRESHOLD]

    if not strong_or_medium:
        # All signals are weak: compounding formula applies rather than naive max
        return compound_weak_signals(weak_signals)

    compounded_weak = (
        compound_weak_signals(weak_signals)
        if len(weak_signals) > 1
        else (weak_signals[0] if weak_signals else 0.0)
    )
    return max(max(strong_or_medium), compounded_weak)
