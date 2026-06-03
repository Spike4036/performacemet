from __future__ import annotations

from dataclasses import replace

from emotiv_bridge.metrics_parser import CognitiveState


class ExponentialSmoother:
    """Lightweight EMA smoother for installation control signals."""

    def __init__(self, alpha: float = 0.35) -> None:
        self.alpha = alpha
        self._state: CognitiveState | None = None

    def update(self, state: CognitiveState) -> CognitiveState:
        if self._state is None:
            self._state = replace(state)
            return replace(self._state)

        self._state.timestamp = state.timestamp
        self._state.headset_on = state.headset_on
        self._state.pow_active = state.pow_active

        for attr in [
            "engagement",
            "excitement",
            "long_term_excitement",
            "stress",
            "relaxation",
            "interest",
            "attention",
            "battery_percent",
            "signal",
            "overall_contact",
            "sample_rate_quality",
            "theta_power",
            "alpha_power",
            "beta_low_power",
            "beta_high_power",
            "beta_power",
            "gamma_power",
        ]:
            setattr(self._state, attr, self._smooth_value(getattr(self._state, attr), getattr(state, attr)))

        return replace(self._state)

    def _smooth_value(self, previous: float | None, current: float | None) -> float | None:
        if current is None:
            return previous
        if previous is None:
            return current
        return previous + self.alpha * (current - previous)
