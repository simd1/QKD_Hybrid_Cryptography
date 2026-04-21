"""Privacy amplification for distilling an AES key from reconciled BB84 bits."""

from __future__ import annotations

import hashlib

import numpy as np


def bits_to_bytes(bits: np.ndarray) -> bytes:
    """Pack a NumPy bit array into bytes, padding on the right."""
    if np.any((bits != 0) & (bits != 1)):
        raise ValueError("bits must contain only 0 and 1")

    pad_len = (-len(bits)) % 8
    padded = np.pad(bits.astype(np.uint8), (0, pad_len), constant_values=0)
    packed = np.packbits(padded, bitorder="big")
    return packed.tobytes()


def privacy_amplification(
    reconciled_key: np.ndarray,
    output_bits: int = 256,
    seed: bytes = b"hybrid-bb84-aes-v1",
) -> bytes:
    """Derive a fixed-length key using SHAKE-256 as a hash extractor."""
    if output_bits <= 0 or output_bits % 8 != 0:
        raise ValueError("output_bits must be a positive multiple of 8")
    if len(reconciled_key) < output_bits:
        raise ValueError("reconciled_key must contain at least output_bits bits")

    material = seed + bits_to_bytes(reconciled_key)
    return hashlib.shake_256(material).digest(output_bits // 8)

