"""
Compass NYC — Benchmark Utility
────────────────────────────────────────────────────────────
Lightweight performance tracking for end-to-end RAG pipeline.

Tracks:
  - timings (start/stop)
  - custom metrics (log)
  - structured report output
  - optional CSV export for experiments
"""

import time
from collections import defaultdict
from typing import Dict, Any, Optional, List


class Benchmark:
    """
    Simple benchmark tracker for profiling pipeline components.
    """

    def __init__(self):
        # Stores start timestamps
        self._start_times = {}

        # Stores final metrics
        self.metrics = defaultdict(float)

        # Stores non-time scalar values (counts, tokens, etc.)
        self.values = {}

    # ─────────────────────────────────────────────
    # Timing functions
    # ─────────────────────────────────────────────

    def start(self, key: str):
        """
        Start timing a block.
        """
        self._start_times[key] = time.time()

    def stop(self, key: str):
        """
        Stop timing a block and store duration.
        """
        if key not in self._start_times:
            raise ValueError(f"[Benchmark] No start time for key: {key}")

        elapsed = time.time() - self._start_times[key]
        self.metrics[key] += elapsed

        # cleanup
        del self._start_times[key]

    # ─────────────────────────────────────────────
    # Logging functions
    # ─────────────────────────────────────────────

    def log(self, key: str, value: Any):
        """
        Store arbitrary metric (non-timing).
        If key repeats, we accumulate lists or overwrite intelligently.
        """
        if key in self.values:
            # If numeric → accumulate
            if isinstance(value, (int, float)) and isinstance(self.values[key], (int, float)):
                self.values[key] += value
            else:
                # convert to list
                if not isinstance(self.values[key], list):
                    self.values[key] = [self.values[key]]
                self.values[key].append(value)
        else:
            self.values[key] = value

    # ─────────────────────────────────────────────
    # Reporting
    # ─────────────────────────────────────────────

    def report(self) -> Dict[str, Any]:
        """
        Return full benchmark report as a single dictionary.
        """
        report = {}

        # timings
        for k, v in self.metrics.items():
            report[k] = round(v, 6)

        # values
        for k, v in self.values.items():
            report[k] = v

        return report

    # ─────────────────────────────────────────────
    # Pretty print
    # ─────────────────────────────────────────────

    def print(self):
        """
        Pretty print benchmark summary.
        """
        print("\n" + "=" * 60)
        print(" PERFORMANCE BENCHMARK")
        print("=" * 60)

        for k, v in self.report().items():
            print(f"{k:30} : {v}")

        print("=" * 60 + "\n")

    # ─────────────────────────────────────────────
    # CSV Export (for experiments)
    # ─────────────────────────────────────────────

    def to_dict_flat(self) -> Dict[str, Any]:
        """
        Flattened version for logging experiments (CSV-ready).
        """
        return self.report()

    def reset(self):
        """
        Reset benchmark state.
        """
        self._start_times.clear()
        self.metrics.clear()
        self.values.clear()