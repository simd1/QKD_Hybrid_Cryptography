"""Alice's side of the BB84 protocol."""

from __future__ import annotations

import secrets

import numpy as np


class Alice:
    """Generate BB84 bits, bases, and encoded qubit state indices."""

    def __init__(self, n_qubits: int) -> None:
        if n_qubits <= 0:
            raise ValueError("n_qubits must be positive")
        self.n_qubits = n_qubits
        self.bits: np.ndarray | None = None
        self.bases: np.ndarray | None = None
        self.qubits: np.ndarray | None = None

    def generate_bits_and_bases(self) -> None:
        """Generate random raw bits and random BB84 bases."""
        rng = np.random.default_rng(secrets.randbits(128))
        self.bits = rng.integers(0, 2, size=self.n_qubits, dtype=np.uint8)
        self.bases = rng.integers(0, 2, size=self.n_qubits, dtype=np.uint8)

    def encode_qubits(self) -> np.ndarray:
        """Encode each bit and basis as a qubit state index from 0 to 3."""
        if self.bits is None or self.bases is None:
            raise RuntimeError("generate_bits_and_bases must be called before encoding")
        self.qubits = self.bases * 2 + self.bits
        return self.qubits.copy()

    def sift_key(self, bob_bases: np.ndarray) -> np.ndarray:
        """Keep Alice bits whose bases match Bob's public basis choices."""
        if self.bits is None or self.bases is None:
            raise RuntimeError("bits and bases have not been generated")
        if len(bob_bases) != self.n_qubits:
            raise ValueError("bob_bases length must equal n_qubits")
        matching = self.bases == bob_bases
        return self.bits[matching].copy()

    def get_bases(self) -> np.ndarray:
        """Return Alice's bases for public basis reconciliation."""
        if self.bases is None:
            raise RuntimeError("bases have not been generated")
        return self.bases.copy()

