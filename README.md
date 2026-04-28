# Hybrid BB84 / E91 + AES-256-GCM

This cybersecurity lab project demonstrates two hybrid quantum-classical encryption workflows implemented with Qiskit:

1. `BB84 + AES-256-GCM`
2. `Minimal E91 + AES-256-GCM`

The project uses Qiskit state preparation, entanglement, basis rotation, and measurement collapse to model actual quantum behavior in software.

## What The Project Includes

- Qiskit-based BB84 prepare-and-measure key distribution
- Qiskit-based minimal E91 entanglement-based key distribution
- QBER estimation and simplified reconciliation
- Privacy amplification to a 256-bit AES key
- AES-256-GCM encryption and authenticated decryption
- Eve simulations for both protocols
- A protocol comparison note and demo

## Project Layout

```text
hybrid_bb84_aes/
  requirements.txt
  src/
    quantum_utils.py
    reconciliation.py
    privacy_amplification.py
    aes_cipher.py
    bb84_pipeline.py
    e91_pipeline.py
    hybrid_encrypt.py
    demo.py
    qber_sweep.py
  tests/
    test_bb84.py
  docs/
    protocol_comparison.md
    lab_report.md
  results/
    qber_sweep.csv
```

## Setup

```powershell
cd "C:\Users\vansh\Vansh_Prac\SEM - 6\CyberSec\hybrid_bb84_aes"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run Tests

```powershell
python -m pytest tests -v
```

## Run Demo

```powershell
python src\demo.py
```

The demo runs:

- clean BB84 + AES
- eavesdropped BB84 + AES
- clean E91 + AES
- eavesdropped E91 + AES
- a quick protocol comparison summary

## Generate QBER Sweep

```powershell
python src\qber_sweep.py
```

The sweep writes `results/qber_sweep.csv` with measured BB84 QBER values for intercept rates from 0% to 100%.

## Compare The Protocols

See:

- `docs/protocol_comparison.md`

In short:

- BB84 uses single-qubit prepare-and-measure states.
- E91 uses Bell-pair entanglement and Bell-test rounds.
- Both protocols derive a 256-bit key that feeds the same AES-256-GCM layer.
