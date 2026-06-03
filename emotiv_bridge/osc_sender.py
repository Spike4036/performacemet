from __future__ import annotations

from pythonosc.udp_client import SimpleUDPClient

from emotiv_bridge.metrics_parser import CognitiveState


class OscCognitiveSender:
    def __init__(self, host: str, port: int) -> None:
        self.client = SimpleUDPClient(host, port)

    def send_state(self, state: CognitiveState) -> None:
        self._send("/engagement", state.engagement)
        self._send("/stress", state.stress)
        self._send("/interest", state.interest)
        self._send("/relaxation", state.relaxation)
        self._send("/excitement", state.excitement)
        self._send("/pow/theta", state.theta_power)
        self._send("/pow/alpha", state.alpha_power)
        self._send("/pow/beta", state.beta_power)
        self._send("/pow/gamma", state.gamma_power)

        # Future-friendly aggregate payload for TouchDesigner CHOP Execute / DAT parsing.
        self.client.send_message(
            "/cognitive_state",
            [
                state.timestamp,
                self._or_zero(state.engagement),
                self._or_zero(state.stress),
                self._or_zero(state.interest),
                self._or_zero(state.relaxation),
                self._or_zero(state.excitement),
                self._or_zero(state.attention),
                self._or_zero(state.alpha_power),
                self._or_zero(state.beta_power),
                self._or_zero(state.gamma_power),
            ],
        )

    def _send(self, address: str, value: float | None) -> None:
        self.client.send_message(address, self._or_zero(value))

    @staticmethod
    def _or_zero(value: float | None) -> float:
        return 0.0 if value is None else float(value)
