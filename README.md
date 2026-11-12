# Hybrid BB84 / E91 + AES-256-GCM

This cybersecurity lab project compares three hybrid key-establishment workflows feeding AES-256-GCM:

1. `RSA-OAEP + AES-256-GCM` (classical baseline)
2. `BB84 + AES-256-GCM` (simulated QKD)
3. `Minimal E91 + AES-256-GCM` (simulated QKD)

The QKD paths use Qiskit state preparation, entanglement, basis rotation, and measurement collapse to model quantum behavior in software. They are educational simulations, not hardware QKD or finite-key security proofs.

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
- an automatic CSV benchmark refresh

## Generate QBER Sweep

```powershell
python src\qber_sweep.py
```

Generate a reproducible three-way comparison (RSA/AES, BB84/AES, E91/AES):

```bash
python -c "from pathlib import Path; from src.qber_sweep import run_comparison; print(run_comparison(trials=30, seed=20261112, output_dir=Path('results')))"
```

This writes trial-level observations to `results/comparison_trials.csv` and aggregate results, approximate 95% intervals, and environment versions to `results/comparison_summary.csv`. Simulator runtimes describe this software implementation only, not physical QKD throughput. Reconciliation now simulates public parity leakage and privacy amplification aborts when a heuristic secret-bit estimate is insufficient; these models are not validated composable security proofs and do not establish proven secure key material.

The sweep writes `results/qber_sweep.csv` with comparative benchmark rows for both `BB84+AES` and `E91+AES`.

The CSV includes:

- intercept rate
- protocol name
- average runtime
- computational load per quantum unit
- average QBER
- average sifted-key ratio
- average Bell score for E91
- aborted trials
- success rate
- key-generation efficiency

## Compare The Protocols

See:

- `docs/protocol_comparison.md`

In short:

- BB84 uses single-qubit prepare-and-measure states.
- E91 uses Bell-pair entanglement and Bell-test rounds.
- Both protocols derive a 256-bit key that feeds the same AES-256-GCM layer.
