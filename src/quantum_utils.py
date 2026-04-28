"""Shared Qiskit helpers for BB84 and E91 simulations."""

from __future__ import annotations

import math
import secrets
from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Statevector


def make_rng() -> np.random.Generator:
    """Return a cryptographically seeded NumPy generator."""
    return np.random.default_rng(secrets.randbits(128))


def prepare_bb84_state(bit: int, basis: int) -> Statevector:
    """Prepare a one-qubit BB84 state using Qiskit state evolution."""
    qc = QuantumCircuit(1)
    if bit:
        qc.x(0)
    if basis:
        qc.h(0)
    return Statevector.from_instruction(qc)


def measure_single_qubit_in_basis(state: Statevector, basis: int) -> tuple[int, Statevector]:
    """Measure a one-qubit state in Z or X basis and restore the post-measurement state."""
    qc = QuantumCircuit(1)
    if basis:
        qc.h(0)
    rotated = state.evolve(qc)
    outcome, collapsed = rotated.measure()
    restored = collapsed.evolve(qc) if basis else collapsed
    return int(outcome), restored


def prepare_bell_state() -> Statevector:
    """Prepare the |Phi+> Bell state used by the minimal E91 pipeline."""
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return Statevector.from_instruction(qc)


def measure_qubit_at_angle(state: Statevector, qubit: int, angle: float) -> tuple[int, Statevector]:
    """
    Measure a target qubit after a Y-axis basis rotation.

    Angle 0 measures Z. Angle pi/2 measures X. Intermediate angles are used
    for the minimal CHSH-style E91 analysis.
    """
    qc = QuantumCircuit(state.num_qubits)
    qc.ry(-angle, qubit)
    rotated = state.evolve(qc)
    outcome, collapsed = rotated.measure([qubit])

    restore = QuantumCircuit(state.num_qubits)
    restore.ry(angle, qubit)
    restored = collapsed.evolve(restore)
    return int(outcome), restored


def bit_to_spin(bit: int) -> int:
    """Map bit 0 -> +1 and bit 1 -> -1 for correlation calculations."""
    return 1 if bit == 0 else -1


@dataclass(frozen=True)
class E91Angles:
    """Measurement settings for the minimal E91 implementation."""

    key: float = 0.0
    a0: float = 0.0
    a1: float = math.pi / 2
    b0: float = math.pi / 4
    b1: float = -math.pi / 4

