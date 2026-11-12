"""Reproducible trial-level comparison of RSA, BB84, and E91 key establishment."""

from __future__ import annotations

import csv
import json
import math
import platform
import statistics
from pathlib import Path
from time import perf_counter

import cryptography
import qiskit

from bb84_pipeline import run_bb84
from e91_pipeline import run_e91
from rsa_hybrid import rsa_aes_decrypt, rsa_trial

DEFAULT_MESSAGE = "Common AES-GCM payload for key-establishment comparison."


def _mean_ci(values: list[float]) -> tuple[float, float, float]:
    mean = statistics.mean(values)
    if len(values) < 2:
        return mean, mean, mean
    # Approximate 95% CI; use normal critical value for a compact dependency-free report.
    margin = 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return mean, mean - margin, mean + margin


def run_comparison(
    trials: int = 30,
    seed: int = 20261112,
    message: str = DEFAULT_MESSAGE,
    bb84_qubits: int = 4096,
    e91_pairs: int = 8192,
    intercept_rate: float = 0.0,
    bit_flip_rate: float = 0.0,
    phase_flip_rate: float = 0.0,
    loss_rate: float = 0.0,
    output_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Run all methods and save raw trial data plus aggregate CSV summaries.

    Runtime measures this Python implementation and local simulator only; it is
    not a QKD link throughput or real-hardware latency estimate.
    """
    if trials <= 0:
        raise ValueError("trials must be positive")
    if not 0 <= intercept_rate <= 1:
        raise ValueError("intercept_rate must be between 0 and 1")
    output_dir = output_dir or Path(__file__).resolve().parents[1] / "results"
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_path = output_dir / "comparison_trials.csv"
    summary_path = output_dir / "comparison_summary.csv"
    rows: list[dict[str, object]] = []

    for trial in range(trials):
        trial_seed = seed + trial * 100
        # RSA creates a fresh ephemeral keypair per trial; key generation is included in timing.
        start = perf_counter()
        rsa_result = rsa_trial(message)
        rsa_elapsed = perf_counter() - start
        rsa_ok = rsa_aes_decrypt(**{k: rsa_result[k] for k in ("ciphertext", "nonce", "aad", "wrapped_key", "private_key_pem")}) == message
        rows.append({"trial": trial, "seed": trial_seed, "protocol": "RSA+AES-GCM", "runtime_sec": rsa_elapsed,
                     "rsa_keygen_sec": rsa_result["keygen_sec"], "rsa_operation_sec": rsa_result["operation_sec"],
                     "success": int(rsa_ok), "aborted": 0, "qber": "", "chsh_s": "",
                     "quantum_units": 0, "intercept_rate": "", "key_bits": 256})

        for name, runner, units, unit_name in (
            ("BB84+AES-GCM", run_bb84, bb84_qubits, "n_qubits"),
            ("E91+AES-GCM", run_e91, e91_pairs, "n_pairs"),
        ):
            start = perf_counter()
            if name.startswith("BB84"):
                key, metrics = runner(n_qubits=units, eve_present=intercept_rate > 0,
                                      intercept_rate=intercept_rate, verbose=False,
                                      return_metrics=True, seed=trial_seed, bit_flip_rate=bit_flip_rate,
                                      phase_flip_rate=phase_flip_rate, loss_rate=loss_rate)
            else:
                key, metrics = runner(n_pairs=units, eve_present=intercept_rate > 0,
                                      intercept_rate=intercept_rate, verbose=False,
                                      return_metrics=True, seed=trial_seed, bit_flip_rate=bit_flip_rate,
                                      phase_flip_rate=phase_flip_rate, loss_rate=loss_rate)
            elapsed = perf_counter() - start
            rows.append({"trial": trial, "seed": trial_seed, "protocol": name, "runtime_sec": elapsed,
                         "success": int(key is not None), "aborted": int(bool(metrics["aborted"])),
                         "qber": metrics.get("qber", ""), "chsh_s": metrics.get("chsh_s", ""),
                         "quantum_units": units, "unit_type": unit_name, "intercept_rate": intercept_rate,
                         "key_bits": 256, "key_security_status": metrics.get("key_security_status", "")})

    raw_fields = sorted({key for row in rows for key in row})
    with raw_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=raw_fields)
        writer.writeheader()
        writer.writerows(rows)

    with summary_path.open("w", newline="", encoding="utf-8") as f:
        fields = ["protocol", "trials", "mean_runtime_sec", "runtime_ci95_low", "runtime_ci95_high",
                  "success_rate", "success_rate_ci95_low", "success_rate_ci95_high", "mean_qber",
                  "mean_chsh_s", "mean_quantum_units", "intercept_rate", "seed", "python_version",
                  "qiskit_version", "cryptography_version", "bit_flip_rate", "phase_flip_rate", "loss_rate"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for protocol in ("RSA+AES-GCM", "BB84+AES-GCM", "E91+AES-GCM"):
            group = [r for r in rows if r["protocol"] == protocol]
            runtimes = [float(r["runtime_sec"]) for r in group]
            successes = [float(r["success"]) for r in group]
            runtime_stats = _mean_ci(runtimes)
            success_stats = _mean_ci(successes)
            qbers = [float(r["qber"]) for r in group if r["qber"] != ""]
            chsh = [float(r["chsh_s"]) for r in group if r["chsh_s"] != ""]
            quantum_units = [float(r["quantum_units"]) for r in group]
            writer.writerow({"protocol": protocol, "trials": trials, "mean_runtime_sec": runtime_stats[0],
                             "runtime_ci95_low": runtime_stats[1], "runtime_ci95_high": runtime_stats[2],
                             "success_rate": success_stats[0], "success_rate_ci95_low": success_stats[1],
                             "success_rate_ci95_high": success_stats[2],
                             "mean_qber": statistics.mean(qbers) if qbers else "",
                             "mean_chsh_s": statistics.mean(chsh) if chsh else "",
                             "mean_quantum_units": statistics.mean(quantum_units),
                             "intercept_rate": "" if protocol.startswith("RSA") else intercept_rate,
                             "seed": seed, "python_version": platform.python_version(),
                             "qiskit_version": qiskit.__version__, "cryptography_version": cryptography.__version__})
    return raw_path, summary_path


def sweep_qber(trials: int = 3, output_path: Path | None = None) -> Path:
    """Backward-compatible BB84/E91 intercept sweep with explicit seeds."""
    output_path = output_path or Path(__file__).resolve().parents[1] / "results" / "qber_sweep.csv"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["protocol", "intercept_rate", "trials", "mean_qber", "success_rate", "mean_chsh_s", "seed"]
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for protocol, runner, param, units in (("BB84+AES", run_bb84, "n_qubits", 2048), ("E91+AES", run_e91, "n_pairs", 4096)):
            for rate_i in range(11):
                rate = rate_i / 10
                metrics_rows = []
                for trial in range(trials):
                    kwargs = {param: units, "eve_present": rate > 0, "intercept_rate": rate,
                              "verbose": False, "return_metrics": True, "seed": 70000 + rate_i * 100 + trial}
                    _, metrics = runner(**kwargs)
                    metrics_rows.append(metrics)
                writer.writerow({"protocol": protocol, "intercept_rate": rate, "trials": trials,
                                 "mean_qber": statistics.mean(float(m["qber"]) for m in metrics_rows),
                                 "success_rate": sum(not bool(m["aborted"]) for m in metrics_rows) / trials,
                                 "mean_chsh_s": statistics.mean(float(m.get("chsh_s", 0.0)) for m in metrics_rows),
                                 "seed": 70000})
    return output_path


if __name__ == "__main__":
    raw, summary = run_comparison()
    print(f"Wrote raw trials to {raw} and summary to {summary}")
