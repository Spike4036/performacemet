from __future__ import annotations

from dataclasses import dataclass
from typing import Any


METRIC_LABELS = {
    "eng": "engagement",
    "exc": "excitement",
    "lex": "long_term_excitement",
    "str": "stress",
    "rel": "relaxation",
    "int": "interest",
    "attention": "attention",
    "foc": "attention",
}
POW_BAND_NAMES = ("theta", "alpha", "betaL", "betaH", "gamma")


@dataclass
class CognitiveState:
    timestamp: float
    engagement: float | None = None
    excitement: float | None = None
    long_term_excitement: float | None = None
    stress: float | None = None
    relaxation: float | None = None
    interest: float | None = None
    attention: float | None = None
    battery_percent: float | None = None
    signal: float | None = None
    overall_contact: float | None = None
    headset_on: bool = True
    sample_rate_quality: float | None = None
    theta_power: float | None = None
    alpha_power: float | None = None
    beta_low_power: float | None = None
    beta_high_power: float | None = None
    beta_power: float | None = None
    gamma_power: float | None = None
    pow_active: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "engagement": self.engagement,
            "excitement": self.excitement,
            "long_term_excitement": self.long_term_excitement,
            "stress": self.stress,
            "relaxation": self.relaxation,
            "interest": self.interest,
            "attention": self.attention,
            "battery_percent": self.battery_percent,
            "signal": self.signal,
            "overall_contact": self.overall_contact,
            "headset_on": self.headset_on,
            "sample_rate_quality": self.sample_rate_quality,
            "theta_power": self.theta_power,
            "alpha_power": self.alpha_power,
            "beta_low_power": self.beta_low_power,
            "beta_high_power": self.beta_high_power,
            "beta_power": self.beta_power,
            "gamma_power": self.gamma_power,
            "pow_active": self.pow_active,
        }

    def csv_row(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "engagement": self.engagement,
            "stress": self.stress,
            "interest": self.interest,
            "relaxation": self.relaxation,
            "excitement": self.excitement,
            "alpha_power": self.alpha_power,
            "beta_power": self.beta_power,
            "gamma_power": self.gamma_power,
        }


def normalize_metric(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric < 0.0:
        return 0.0
    if numeric > 1.0:
        return 1.0
    return numeric


class PerformanceMetricsParser:
    def __init__(self) -> None:
        self._state = CognitiveState(timestamp=0.0, headset_on=False)
        self._met_cols: list[str] = []
        self._dev_cols: list[str] = []
        self._eq_cols: list[str] = []
        self._pow_cols: list[str] = []

    def set_stream_columns(self, stream_name: str, cols: list[str]) -> None:
        normalized_cols = self._flatten_cols(cols)
        if stream_name == "met":
            self._met_cols = normalized_cols
        elif stream_name == "dev":
            self._dev_cols = normalized_cols
        elif stream_name == "eq":
            self._eq_cols = normalized_cols
        elif stream_name == "pow":
            self._pow_cols = normalized_cols

    def handle_sample(self, message: dict[str, Any]) -> CognitiveState | None:
        if "met" in message:
            self._parse_met_sample(message["met"], message.get("time"))
            return self.snapshot()
        if "dev" in message:
            self._parse_dev_sample(message["dev"], message.get("time"))
            return self.snapshot()
        if "eq" in message:
            self._parse_eq_sample(message["eq"], message.get("time"))
            return self.snapshot()
        if "pow" in message:
            self._parse_pow_sample(message["pow"], message.get("time"))
            return self.snapshot()
        if message.get("warning") is not None:
            self._state.headset_on = False
            return self.snapshot()
        return None

    def snapshot(self) -> CognitiveState:
        return CognitiveState(**self._state.as_dict())

    def _parse_met_sample(self, values: list[Any], timestamp: float | None) -> None:
        if timestamp is not None:
            self._state.timestamp = float(timestamp)

        sample = dict(zip(self._met_cols, values))
        for raw_name, mapped_name in METRIC_LABELS.items():
            active_key = f"{raw_name}.isActive"
            metric_value = normalize_metric(sample.get(raw_name))
            is_active = sample.get(active_key)

            if raw_name == "lex":
                setattr(self._state, mapped_name, metric_value)
                continue

            if is_active is False:
                setattr(self._state, mapped_name, None)
                continue

            setattr(self._state, mapped_name, metric_value)

        self._state.headset_on = True

    def _parse_dev_sample(self, values: list[Any], timestamp: float | None) -> None:
        if timestamp is not None:
            self._state.timestamp = float(timestamp)

        sample = dict(zip(self._dev_cols, values))
        self._state.signal = normalize_metric(sample.get("Signal"))
        self._state.overall_contact = self._normalize_percentage(sample.get("OVERALL"))
        self._state.battery_percent = self._normalize_percentage(
            sample.get("BatteryPercent")
        )
        if self._state.overall_contact is None:
            self._state.overall_contact = self._normalize_percentage(sample.get("overall"))
        if self._state.battery_percent is None:
            self._state.battery_percent = self._normalize_percentage(
                sample.get("batteryPercent")
            )

        if self._state.battery_percent is None and sample.get("Battery") is not None:
            battery = float(sample["Battery"])
            self._state.battery_percent = max(0.0, min(1.0, battery / 4.0))

        if sample.get("Signal") == 0:
            self._state.headset_on = False
        else:
            self._state.headset_on = True

    def _parse_eq_sample(self, values: list[Any], timestamp: float | None) -> None:
        if timestamp is not None:
            self._state.timestamp = float(timestamp)

        sample = dict(zip(self._eq_cols, values))
        if self._state.battery_percent is None:
            self._state.battery_percent = self._normalize_percentage(
                sample.get("batteryPercent")
            )
        if self._state.overall_contact is None:
            self._state.overall_contact = self._normalize_percentage(sample.get("overall"))
        srq = sample.get("sampleRateQuality")
        if srq is not None:
            try:
                srq_value = float(srq)
            except (TypeError, ValueError):
                srq_value = None
            self._state.sample_rate_quality = srq_value

    def _parse_pow_sample(self, values: list[Any], timestamp: float | None) -> None:
        if timestamp is not None:
            self._state.timestamp = float(timestamp)

        sample = dict(zip(self._pow_cols, values))
        aggregates: dict[str, list[float]] = {band: [] for band in POW_BAND_NAMES}
        for label, raw_value in sample.items():
            if "/" not in label:
                continue
            _, band = label.split("/", 1)
            if band not in aggregates:
                continue
            try:
                numeric = float(raw_value)
            except (TypeError, ValueError):
                continue
            if numeric >= 0.0:
                aggregates[band].append(numeric)

        self._state.theta_power = self._normalize_band_average(aggregates["theta"])
        self._state.alpha_power = self._normalize_band_average(aggregates["alpha"])
        self._state.beta_low_power = self._normalize_band_average(aggregates["betaL"])
        self._state.beta_high_power = self._normalize_band_average(aggregates["betaH"])
        self._state.gamma_power = self._normalize_band_average(aggregates["gamma"])

        beta_components = [
            value
            for value in [self._state.beta_low_power, self._state.beta_high_power]
            if value is not None
        ]
        self._state.beta_power = (
            sum(beta_components) / len(beta_components) if beta_components else None
        )
        self._state.pow_active = any(bool(values) for values in aggregates.values())

    @staticmethod
    def _normalize_percentage(value: Any) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        if numeric <= 1.0:
            return max(0.0, numeric)
        return max(0.0, min(1.0, numeric / 100.0))

    @staticmethod
    def _flatten_cols(cols: list[Any]) -> list[str]:
        flattened: list[str] = []
        for col in cols:
            if isinstance(col, list):
                flattened.extend(str(item) for item in col)
            else:
                flattened.append(str(col))
        return flattened

    @staticmethod
    def _normalize_band_average(values: list[float]) -> float | None:
        if not values:
            return None
        return sum(values) / len(values)
