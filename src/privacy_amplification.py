"""Privacy amplification helper for the educational QKD simulation."""

from __future__ import annotations

import hashlib

import numpy as np


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Pack a NumPy bit array into bytes, padding on the right."""
    if np.any((bits != 0) & (bits != 1)):
        raise ValueError("bits must contain only 0 and 1")
    pad_len = (-len(bits)) % 8
    return np.packbits(np.pad(bits.astype(np.uint8), (0, pad_len)), bitorder="big").tobytes()


def privacy_amplification(
    reconciled_key: np.ndarray,
    output_bits: int,
    seed: bytes,
    estimated_secret_bits: float,
) -> bytes:
    """Hash to the requested length only when a caller-supplied bound permits it.

    SHAKE-256 here is a pedagogical extractor placeholder, not a universal2
    privacy-amplification proof. ``estimated_secret_bits`` must already account
    for parameter-estimation uncertainty and all public reconciliation leakage.
    """
    if output_bits <= 0 or output_bits % 8 != 0:
        raise ValueError("output_bits must be a positive multiple of 8")
    if estimated_secret_bits < output_bits:
        raise ValueError("estimated secret material is shorter than requested output")
    if len(reconciled_key) < output_bits:
        raise ValueError("reconciled_key must contain at least output_bits bits")
    return hashlib.shake_256(seed + bits_to_bytes(reconciled_key)).digest(output_bits // 8)
