"""Bob's side of the BB84 protocol."""

from __future__ import annotations

import secrets

import numpy as np


class Bob:
    """Choose measurement bases and measure incoming BB84 qubit states."""

    def __init__(self, n_qubits: int) -> None:
        if n_qubits <= 0:
            raise ValueError("n_qubits must be positive")
        self.n_qubits = n_qubits
        self.bases: np.ndarray | None = None
        self.measured_bits: np.ndarray | None = None

    def choose_bases(self) -> np.ndarray:
        """Choose random measurement bases for each qubit."""
        rng = np.random.default_rng(secrets.randbits(128))
        self.bases = rng.integers(0, 2, size=self.n_qubits, dtype=np.uint8)
        return self.bases.copy()

    def measure(self, qubits: np.ndarray) -> np.ndarray:
        """Measure qubits using Bob's bases."""
        if self.bases is None:
            raise RuntimeError("choose_bases must be called before measure")
        if len(qubits) != self.n_qubits:
            raise ValueError("qubits length must equal n_qubits")

        encoded_bases = qubits // 2
        encoded_bits = qubits % 2

        rng = np.random.default_rng(secrets.randbits(128))
        random_bits = rng.integers(0, 2, size=self.n_qubits, dtype=np.uint8)

        correct_basis = self.bases == encoded_bases
        self.measured_bits = np.where(correct_basis, encoded_bits, random_bits).astype(np.uint8)
        return self.measured_bits.copy()

    def sift_key(self, alice_bases: np.ndarray) -> np.ndarray:
        """Keep measured bits where Bob used the same basis as Alice."""
        if self.bases is None or self.measured_bits is None:
            raise RuntimeError("measure must be called before sifting")
        if len(alice_bases) != self.n_qubits:
            raise ValueError("alice_bases length must equal n_qubits")
        matching = self.bases == alice_bases
        return self.measured_bits[matching].copy()

    def get_bases(self) -> np.ndarray:
        """Return Bob's bases for public basis reconciliation."""
        if self.bases is None:
            raise RuntimeError("bases have not been chosen")
        return self.bases.copy()

