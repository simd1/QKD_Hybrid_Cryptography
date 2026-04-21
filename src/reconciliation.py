"""QBER estimation and simplified reconciliation for BB84 keys."""

from __future__ import annotations

import secrets

import numpy as np


def estimate_qber(
    alice_sifted: np.ndarray,
    bob_sifted: np.ndarray,
    sample_fraction: float = 0.1,
) -> tuple[float, np.ndarray, np.ndarray]:
    """Estimate QBER by publicly comparing a sacrificed random sample."""
    if len(alice_sifted) != len(bob_sifted):
        raise ValueError("sifted keys must have equal lengths")
    if len(alice_sifted) == 0:
        raise ValueError("cannot estimate QBER from an empty key")
    if not 0.0 < sample_fraction <= 1.0:
        raise ValueError("sample_fraction must be in the range (0.0, 1.0]")

    n = len(alice_sifted)
    n_sample = min(n, max(1, int(n * sample_fraction)))
    rng = np.random.default_rng(secrets.randbits(128))
    indices = rng.choice(n, size=n_sample, replace=False)

    keep_mask = np.ones(n, dtype=bool)
    keep_mask[indices] = False

    sample_a = alice_sifted[indices]
    sample_b = bob_sifted[indices]
    qber = float(np.mean(sample_a != sample_b))

    return qber, alice_sifted[keep_mask].copy(), bob_sifted[keep_mask].copy()


def cascade_reconciliation(
    alice_key: np.ndarray,
    bob_key: np.ndarray,
    passes: int = 4,
) -> np.ndarray:
    """
    Simulate Cascade-style reconciliation.

    This lab simulation exposes Alice's key to the function so Bob can be
    corrected deterministically after parity-style passes. Real Cascade uses
    authenticated interactive parity exchanges instead of direct key access.
    """
    if len(alice_key) != len(bob_key):
        raise ValueError("keys must have equal lengths")
    if passes <= 0:
        raise ValueError("passes must be positive")

    corrected = bob_key.copy()
    n = len(corrected)

    for pass_num in range(passes):
        block_size = 2 ** (pass_num + 1)
        for start in range(0, n, block_size):
            end = min(start + block_size, n)
            if np.sum(alice_key[start:end]) % 2 != np.sum(corrected[start:end]) % 2:
                mismatches = np.flatnonzero(alice_key[start:end] != corrected[start:end])
                if len(mismatches) > 0:
                    corrected[start + int(mismatches[0])] ^= 1

    # Final exact correction keeps the educational demo stable after detection.
    corrected[alice_key != corrected] = alice_key[alice_key != corrected]
    return corrected.astype(np.uint8)

