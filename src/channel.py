"""Quantum channel simulation, including optional Eve interception."""

from __future__ import annotations

import secrets

import numpy as np


class QuantumChannel:
    """Transmit qubit state indices from Alice to Bob."""

    def __init__(self, eve_present: bool = False, intercept_rate: float = 1.0) -> None:
        if not 0.0 <= intercept_rate <= 1.0:
            raise ValueError("intercept_rate must be between 0.0 and 1.0")
        self.eve_present = eve_present
        self.intercept_rate = intercept_rate
        self.eve_bases: np.ndarray | None = None
        self.eve_bits: np.ndarray | None = None
        self.intercept_mask: np.ndarray | None = None

    def transmit(self, qubits: np.ndarray) -> np.ndarray:
        """Return received qubits, disturbed if Eve intercepts and re-sends."""
        if not self.eve_present or self.intercept_rate == 0.0:
            return qubits.copy()

        n = len(qubits)
        rng = np.random.default_rng(secrets.randbits(128))

        self.eve_bases = rng.integers(0, 2, size=n, dtype=np.uint8)
        self.intercept_mask = rng.random(size=n) < self.intercept_rate

        alice_bases = qubits // 2
        alice_bits = qubits % 2
        random_bits = rng.integers(0, 2, size=n, dtype=np.uint8)

        correct_basis = self.eve_bases == alice_bases
        self.eve_bits = np.where(correct_basis, alice_bits, random_bits).astype(np.uint8)

        resent_qubits = self.eve_bases * 2 + self.eve_bits
        return np.where(self.intercept_mask, resent_qubits, qubits).astype(np.uint8)

