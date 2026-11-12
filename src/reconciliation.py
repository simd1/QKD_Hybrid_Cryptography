"""Parameter estimation and parity-only reconciliation simulation.

This models public parity leakage without giving the correction routine direct
access to Alice's bit string. It is not an implementation of authenticated,
interactive Cascade or a security proof.
"""

from __future__ import annotations

import math

import numpy as np


def estimate_qber(
    alice_sifted: np.ndarray,
    bob_sifted: np.ndarray,
    sample_fraction: float = 0.2,
    seed: int | None = None,
) -> tuple[float, np.ndarray, np.ndarray, int]:
    """Reveal a random test sample and return QBER, remaining keys, sample size."""
    if len(alice_sifted) != len(bob_sifted):
        raise ValueError("sifted keys must have equal lengths")
    if len(alice_sifted) == 0:
        raise ValueError("cannot estimate QBER from an empty key")
    if not 0.0 < sample_fraction < 1.0:
        raise ValueError("sample_fraction must be between 0 and 1 (exclusive)")

    n = len(alice_sifted)
    n_sample = min(n - 1, max(1, int(n * sample_fraction)))
    rng = np.random.default_rng(seed)
    indices = rng.choice(n, size=n_sample, replace=False)
    keep_mask = np.ones(n, dtype=bool)
    keep_mask[indices] = False
    qber = float(np.mean(alice_sifted[indices] != bob_sifted[indices]))
    return qber, alice_sifted[keep_mask].copy(), bob_sifted[keep_mask].copy(), n_sample


def wilson_upper_bound(errors: int, samples: int, z: float = 5.0) -> float:
    """One-sided Wilson upper confidence bound for a Bernoulli error rate."""
    if samples <= 0 or errors < 0 or errors > samples:
        raise ValueError("require 0 <= errors <= samples and samples > 0")
    p = errors / samples
    z2 = z * z
    denom = 1.0 + z2 / samples
    center = p + z2 / (2.0 * samples)
    radius = z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * samples)) / samples)
    return min(1.0, (center + radius) / denom)


def _parity(bits: np.ndarray) -> int:
    return int(np.sum(bits, dtype=np.uint64) & 1)


def parity_reconciliation(
    alice_key: np.ndarray,
    bob_key: np.ndarray,
    passes: int = 4,
    seed: int | None = None,
) -> tuple[np.ndarray, int, bool]:
    """Correct errors using public block parities and binary searches only.

    Returns Bob's corrected key, number of parity bits disclosed, and whether
    both simulated parties agree. The routine never copies Alice's bits into
    Bob's key. Block permutations are public protocol randomness.
    """
    if len(alice_key) != len(bob_key):
        raise ValueError("keys must have equal lengths")
    if passes <= 0:
        raise ValueError("passes must be positive")
    rng = np.random.default_rng(seed)
    corrected = bob_key.astype(np.uint8, copy=True)
    alice = alice_key.astype(np.uint8, copy=False)
    n = len(alice)
    disclosed = 0

    def locate(start: int, end: int, order: np.ndarray) -> None:
        nonlocal disclosed
        lo, hi = start, end
        while hi - lo > 1:
            mid = (lo + hi) // 2
            disclosed += 1
            if _parity(alice[order[lo:mid]]) != _parity(corrected[order[lo:mid]]):
                hi = mid
            else:
                lo = mid
        corrected[order[lo]] ^= 1

    for pass_num in range(passes):
        order = rng.permutation(n)
        block_size = max(2, 2 ** (pass_num + 1))
        for start in range(0, n, block_size):
            block = order[start:min(start + block_size, n)]
            if len(block) == 0:
                continue
            disclosed += 1
            if _parity(alice[block]) != _parity(corrected[block]):
                locate(0, len(block), block)

    # A final public whole-key parity check detects residual disagreement;
    # it does not reveal or directly copy any key bit.
    disclosed += 1
    agreed = bool(np.array_equal(alice, corrected))
    return corrected, disclosed, agreed


# Kept as an import-compatible name; semantics are now parity-only.
def cascade_reconciliation(
    alice_key: np.ndarray,
    bob_key: np.ndarray,
    passes: int = 4,
) -> np.ndarray:
    corrected, _, _ = parity_reconciliation(alice_key, bob_key, passes=passes)
    return corrected
