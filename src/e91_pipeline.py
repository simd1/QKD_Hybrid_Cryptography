"""Minimal Qiskit-based E91 key distribution pipeline."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit

from privacy_amplification import privacy_amplification
from quantum_utils import E91Angles, bit_to_spin, make_rng, measure_qubit_at_angle, prepare_bell_state
from reconciliation import estimate_qber, parity_reconciliation, wilson_upper_bound

QBER_THRESHOLD = 0.11
CHSH_THRESHOLD = 2.2


def run_e91(
    n_pairs: int = 4096,
    eve_present: bool = False,
    intercept_rate: float = 1.0,
    key_bits: int = 256,
    verbose: bool = True,
    return_metrics: bool = False,
    seed: int | None = None,
    bit_flip_rate: float = 0.0,
    phase_flip_rate: float = 0.0,
    loss_rate: float = 0.0,
) -> bytes | None | tuple[bytes | None, dict[str, float | int | bool | str]]:
    """Run a minimal entanglement-based E91 workflow and return an AES key."""
    if n_pairs <= 0:
        raise ValueError("n_pairs must be positive")
    if key_bits <= 0 or key_bits % 8 != 0:
        raise ValueError("key_bits must be a positive multiple of 8")
    if any(not 0.0 <= x <= 1.0 for x in (intercept_rate, bit_flip_rate, phase_flip_rate, loss_rate)):
        raise ValueError("attack/noise/loss rates must be between 0 and 1")

    if verbose:
        print("\n" + "=" * 60)
        print(f"Minimal Qiskit E91 key distribution: {n_pairs} entangled pairs")
        print(f"Eve present: {eve_present}", end="")
        if eve_present:
            print(f" (intercept rate: {intercept_rate:.0%})")
        else:
            print()
        print("=" * 60)

    angles = E91Angles()
    rng = make_rng(seed)

    key_alice: list[int] = []
    key_bob: list[int] = []
    correlations: dict[str, list[int]] = {"a0b0": [], "a0b1": [], "a1b0": [], "a1b1": []}
    bell_rounds = 0
    eve_events = 0
    lost_pairs = 0

    if verbose:
        print("[1/7] Preparing Bell pairs with Qiskit.")

    for _ in range(n_pairs):
        state = prepare_bell_state()

        if eve_present and rng.random() < intercept_rate:
            eve_angle = float(rng.choice([angles.key, angles.a1]))
            _, state = measure_qubit_at_angle(state, 1, eve_angle)
            eve_events += 1

        if rng.random() < loss_rate:
            lost_pairs += 1
            continue
        if rng.random() < bit_flip_rate:
            qc_noise = QuantumCircuit(2)
            qc_noise.x(int(rng.integers(0, 2)))
            state = state.evolve(qc_noise)
        if rng.random() < phase_flip_rate:
            qc_noise = QuantumCircuit(2)
            qc_noise.z(int(rng.integers(0, 2)))
            state = state.evolve(qc_noise)

        alice_mode = str(rng.choice(["key", "a0", "a1"]))
        bob_mode = str(rng.choice(["key", "b0", "b1"]))

        alice_angle = {
            "key": angles.key,
            "a0": angles.a0,
            "a1": angles.a1,
        }[alice_mode]
        bob_angle = {
            "key": angles.key,
            "b0": angles.b0,
            "b1": angles.b1,
        }[bob_mode]

        alice_bit, state = measure_qubit_at_angle(state, 0, alice_angle)
        bob_bit, _ = measure_qubit_at_angle(state, 1, bob_angle)

        if alice_mode == "key" and bob_mode == "key":
            key_alice.append(alice_bit)
            key_bob.append(bob_bit)
        elif alice_mode != "key" and bob_mode != "key":
            bell_rounds += 1
            correlations[alice_mode + bob_mode].append(bit_to_spin(alice_bit) * bit_to_spin(bob_bit))

    if verbose:
        print("[2/7] Entangled pairs distributed and measured.")

    alice_sifted = np.array(key_alice, dtype=np.uint8)
    bob_sifted = np.array(key_bob, dtype=np.uint8)
    sifted_len = len(alice_sifted)

    if sifted_len == 0:
        metrics: dict[str, float | int | bool | str] = {
            "n_pairs": n_pairs,
            "eve_present": eve_present,
            "intercept_rate": intercept_rate,
            "bell_test_rounds": bell_rounds,
            "eve_intercepted_pairs": eve_events,
            "sifted_bits": 0,
            "sifted_ratio": 0.0,
            "qber": 1.0,
            "chsh_s": 0.0,
            "aborted": True,
            "abort_reason": "no_key_rounds",
        }
        return (None, metrics) if return_metrics else None

    if verbose:
        print(f"[3/7] Key-generation rounds retained: {sifted_len} bits ({sifted_len / n_pairs:.1%}).")

    qber, alice_remaining, bob_remaining, test_bits = estimate_qber(alice_sifted, bob_sifted, seed=None if seed is None else seed + 1)
    qber_upper = wilson_upper_bound(int(round(qber * test_bits)), test_bits)
    if verbose:
        print(f"[4/7] Estimated key-round QBER: {qber:.2%}")

    e_a0b0 = float(np.mean(correlations["a0b0"])) if correlations["a0b0"] else 0.0
    e_a0b1 = float(np.mean(correlations["a0b1"])) if correlations["a0b1"] else 0.0
    e_a1b0 = float(np.mean(correlations["a1b0"])) if correlations["a1b0"] else 0.0
    e_a1b1 = float(np.mean(correlations["a1b1"])) if correlations["a1b1"] else 0.0
    chsh_s = e_a0b0 + e_a0b1 + e_a1b0 - e_a1b1

    if verbose:
        print(f"[5/7] CHSH-style Bell score: {chsh_s:.3f}")

    metrics = {
        "n_pairs": n_pairs,
        "sent_pairs": n_pairs,
        "detected_pairs": n_pairs - lost_pairs,
        "lost_pairs": lost_pairs,
        "bit_flip_rate": bit_flip_rate,
        "phase_flip_rate": phase_flip_rate,
        "loss_rate": loss_rate,
        "eve_present": eve_present,
        "intercept_rate": intercept_rate,
        "bell_test_rounds": bell_rounds,
        "eve_intercepted_pairs": eve_events,
        "key_security_status": "educational_simulation_no_finite_key_proof",
        "sifted_bits": sifted_len,
        "sifted_ratio": sifted_len / n_pairs,
        "qber": qber,
        "qber_upper_99.9999": qber_upper,
        "qber_test_bits": test_bits,
        "chsh_s": chsh_s,
        "aborted": qber_upper > QBER_THRESHOLD or chsh_s < CHSH_THRESHOLD,
    }

    if qber_upper > QBER_THRESHOLD:
        metrics["abort_reason"] = "qber_threshold"
        if verbose:
            print(f"[ABORT] QBER upper bound {qber_upper:.2%} exceeds threshold {QBER_THRESHOLD:.2%}.")
        return (None, metrics) if return_metrics else None

    if chsh_s < CHSH_THRESHOLD:
        metrics["abort_reason"] = "chsh_threshold"
        if verbose:
            print(f"[ABORT] Bell score {chsh_s:.3f} is below threshold {CHSH_THRESHOLD:.2f}.")
        return (None, metrics) if return_metrics else None

    bob_corrected, leakage_bits, reconciled = parity_reconciliation(
        alice_remaining, bob_remaining, seed=None if seed is None else seed + 2
    )
    post_error_rate = float(np.mean(alice_remaining != bob_corrected)) if len(alice_remaining) else 0.0
    metrics["post_reconciliation_error_rate"] = post_error_rate
    metrics["reconciliation_leakage_bits"] = leakage_bits
    metrics["reconciliation_success"] = reconciled
    if verbose:
        print(f"[6/7] Post-reconciliation error rate: {post_error_rate:.4%}")

    # Conservative BB84-style entropy expression used as a heuristic only;
    # E91 security requires an E91-specific finite-key proof and Bell bounds.
    q = min(qber_upper, 0.5 - 1e-12)
    h2 = -q * np.log2(q) - (1 - q) * np.log2(1 - q) if q > 0 else 0.0
    estimated_secret_bits = max(0.0, len(bob_corrected) * (1.0 - 2.0 * h2) - leakage_bits)
    metrics["estimated_secret_bits"] = estimated_secret_bits
    metrics["security_model"] = "heuristic_not_validated_for_e91_or_composable"
    if not reconciled or estimated_secret_bits < key_bits:
        metrics["aborted"] = True
        metrics["abort_reason"] = "reconciliation_failed_or_insufficient_secret_bits"
        if verbose:
            print(f"[ABORT] Reconciliation agreement={reconciled}; estimated secret bits={estimated_secret_bits:.1f}.")
        return (None, metrics) if return_metrics else None

    final_key = privacy_amplification(
        bob_corrected, output_bits=key_bits, seed=b"e91-aes-v2", estimated_secret_bits=estimated_secret_bits
    )
    metrics["final_key_bits"] = key_bits
    if verbose:
        print("[7/7] Privacy amplification complete.")
        print(f"[SUCCESS] Final {key_bits}-bit key: {final_key.hex()[:32]}...")

    return (final_key, metrics) if return_metrics else final_key
