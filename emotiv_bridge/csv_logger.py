from __future__ import annotations

import csv
from pathlib import Path

from emotiv_bridge.metrics_parser import CognitiveState


class CognitiveCsvLogger:
    FIELDNAMES = [
        "timestamp",
        "engagement",
        "stress",
        "interest",
        "relaxation",
        "excitement",
        "alpha_power",
        "beta_power",
        "gamma_power",
    ]

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_header()

    def log(self, state: CognitiveState) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
            writer.writerow(state.csv_row())

    def _ensure_header(self) -> None:
        if self.path.exists() and self.path.stat().st_size > 0:
            return
        with self.path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=self.FIELDNAMES)
            writer.writeheader()
