# Qiskit BB84 + AES vs Minimal E91 + AES

This project now contains two Qiskit-backed hybrid encryption flows:

1. `BB84 + AES-256-GCM`
2. `Minimal E91 + AES-256-GCM`

Both pipelines use Qiskit state evolution and measurement rather than the earlier hand-written symbolic qubit encoding.

## 1. BB84 + AES

Files:

- `src/bb84_pipeline.py`
- `src/hybrid_encrypt.py`
- `src/quantum_utils.py`

How it works:

- Alice prepares single-qubit states in Z or X basis.
- Bob measures each qubit in a random Z or X basis using Qiskit basis rotation plus measurement collapse.
- Matching-basis positions are sifted.
- QBER is estimated from a sacrificed sample.
- Reconciliation and privacy amplification derive a 256-bit AES key.
- AES-256-GCM encrypts the message.

Why it is useful:

- Simpler to explain.
- Good for showing prepare-and-measure QKD.
- Eavesdropping appears as increased QBER.

## 2. Minimal E91 + AES

Files:

- `src/e91_pipeline.py`
- `src/hybrid_encrypt.py`
- `src/quantum_utils.py`

How it works:

- A Bell pair is prepared with Qiskit.
- Alice and Bob measure entangled qubits using key-generation and Bell-test settings.
- Key rounds use correlated Z-basis measurements.
- Test rounds estimate a CHSH-style Bell score.
- QBER and Bell-score thresholds decide whether the session should abort.
- Reconciliation and privacy amplification derive a 256-bit AES key.
- AES-256-GCM encrypts the message.

Why it is useful:

- Uses entanglement rather than prepare-and-measure.
- Gives a direct Bell-correlation flavored comparison against BB84.
- Shows how entanglement-based QKD can feed the same AES layer.

## 3. Implementation Comparison

| Aspect | BB84 + AES | Minimal E91 + AES |
| --- | --- | --- |
| Quantum idea | Prepare-and-measure | Entanglement-based |
| Qiskit state | Single-qubit states | Two-qubit Bell pairs |
| Security signal | QBER | QBER + CHSH-style Bell score |
| Basis model | Z and X | Key basis + Bell-test angles |
| Conceptual complexity | Lower | Higher |
| AES usage | AES-256-GCM | AES-256-GCM |

## 4. Why We Did Not Copy the Base Paper's E91 Variant

The base paper adds protocol-specific enhancements such as reverse gate transformations, extra noise handling logic, and a more specialized security design. For this project, the goal is a clean educational build:

- BB84 uses simple Qiskit prepare-and-measure states.
- E91 uses simple Qiskit Bell-pair entanglement and measurement settings.
- Both protocols feed the same AES-256-GCM layer so the comparison stays fair and easy to explain.
