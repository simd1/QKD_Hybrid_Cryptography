# Hybrid BB84 + AES-256-GCM

This cybersecurity lab project demonstrates a hybrid quantum-classical encryption workflow:

1. Alice and Bob simulate BB84 quantum key distribution.
2. They sift matching-basis measurements and estimate QBER.
3. A simplified reconciliation step corrects remaining key disagreement.
4. Privacy amplification derives a 256-bit key.
5. AES-256-GCM encrypts and authenticates the plaintext message.
6. A simulated Eve can intercept qubits and trigger BB84 abort behavior.

The quantum channel is a software simulation. It is useful for learning BB84 mechanics, not for production cryptography.

## Project Layout

```text
hybrid_bb84_aes/
  requirements.txt
  src/
    alice.py
    bob.py
    channel.py
    reconciliation.py
    privacy_amplification.py
    aes_cipher.py
    bb84_pipeline.py
    hybrid_encrypt.py
    demo.py
    qber_sweep.py
  tests/
    test_bb84.py
  docs/
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

## Generate QBER Sweep

```powershell
python src\qber_sweep.py
```

The sweep writes `results/qber_sweep.csv` with measured QBER values for intercept rates from 0% to 100%.

