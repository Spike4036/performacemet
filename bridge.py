from __future__ import annotations

import json
import logging
import ssl
import time
from typing import Any

from websocket import WebSocket
from websocket import create_connection

from emotiv_bridge.config import BridgeConfig
from emotiv_bridge.csv_logger import CognitiveCsvLogger
from emotiv_bridge.diffusion_mapping import (
    map_engagement_to_cfg_scale,
    map_interest_to_prompt_weighting,
    map_relaxation_to_image_stabilization,
    map_stress_to_noise_strength,
)
from emotiv_bridge.metrics_parser import PerformanceMetricsParser
from emotiv_bridge.osc_sender import OscCognitiveSender
from emotiv_bridge.smoothing import ExponentialSmoother


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
LOGGER = logging.getLogger("emotiv_bridge")
LOW_CONTACT_THRESHOLD = 0.8
CONTACT_LOG_INTERVAL_SECONDS = 2.0
MET_LOG_INTERVAL_SECONDS = 1.0
POW_LOG_INTERVAL_SECONDS = 0.5


class CortexBridge:
    def __init__(self, config: BridgeConfig) -> None:
        self.config = config
        self.ws: WebSocket | None = None
        self.request_id = 0
        self.auth_token: str | None = None
        self.session_id: str | None = None
        self.headset_id: str | None = None
        self.parser = PerformanceMetricsParser()
        self.csv_logger = CognitiveCsvLogger(config.csv_path)
        self.osc_sender = OscCognitiveSender(config.osc_host, config.osc_port)
        self.smoother = ExponentialSmoother(alpha=0.35)
        self.last_contact_log_time = 0.0
        self.last_met_log_time = 0.0
        self.last_pow_log_time = 0.0

    def connect(self) -> None:
        LOGGER.info("Connecting to Cortex at %s", self.config.cortex_url)
        self.ws = create_connection(
            self.config.cortex_url,
            sslopt={"cert_reqs": ssl.CERT_NONE},
        )

    def requestAccess(self) -> dict[str, Any]:
        return self._rpc(
            "requestAccess",
            {
                "clientId": self.config.client_id,
                "clientSecret": self.config.client_secret,
            },
        )

    def authorize(self) -> str:
        params: dict[str, Any] = {
            "clientId": self.config.client_id,
            "clientSecret": self.config.client_secret,
        }
        if self.config.activate_session and self.config.authorize_debit > 0:
            params["debit"] = self.config.authorize_debit

        result = self._rpc(
            "authorize",
            params,
        )
        token = result["cortexToken"]
        self.auth_token = token
        LOGGER.info(
            "Authorized Cortex session%s",
            f" with debit={self.config.authorize_debit}"
            if self.config.activate_session and self.config.authorize_debit > 0
            else "",
        )
        return token

    def queryHeadsets(self) -> list[dict[str, Any]]:
        result = self._rpc("queryHeadsets", {})
        headsets = result if isinstance(result, list) else result.get("headsets", [])
        if not isinstance(headsets, list):
            raise RuntimeError(f"Unexpected queryHeadsets response: {result}")
        return headsets

    def controlDevice(self, command: str, headset_id: str) -> dict[str, Any]:
        return self._rpc(
            "controlDevice",
            {
                "command": command,
                "headset": headset_id,
            },
        )

    def createSession(self) -> str:
        if not self.auth_token:
            raise RuntimeError("authorize() must run before createSession().")
        if not self.headset_id:
            raise RuntimeError("No headset selected.")

        status = "active" if self.config.activate_session else "open"
        result = self._rpc(
            "createSession",
            {
                "cortexToken": self.auth_token,
                "headset": self.headset_id,
                "status": status,
            },
        )
        self.session_id = result["id"]
        LOGGER.info("Created Cortex session %s with status=%s", self.session_id, status)
        return self.session_id

    def subscribe(self, streams: list[str]) -> dict[str, Any]:
        if not self.auth_token or not self.session_id:
            raise RuntimeError("authorize() and createSession() must run before subscribe().")

        result = self._rpc(
            "subscribe",
            {
                "cortexToken": self.auth_token,
                "session": self.session_id,
                "streams": streams,
            },
        )
        for stream in result.get("success", []):
            stream_name = stream.get("streamName")
            cols = stream.get("cols", [])
            if stream_name and isinstance(cols, list):
                self.parser.set_stream_columns(stream_name, cols)
                LOGGER.info("Subscribed to %s with cols=%s", stream_name, cols)

        failures = result.get("failure", [])
        for failure in failures:
            LOGGER.warning("Subscription failure: %s", failure)
        return result

    def setup(self) -> None:
        self.config.validate()
        self.connect()

        if self.config.request_access:
            access_result = self.requestAccess()
            LOGGER.info("requestAccess result: %s", access_result)

        self.authorize()
        self.headset_id = self._discover_headset()
        self._connect_headset(self.headset_id)
        self.createSession()
        self.subscribe(["met", "pow", "dev", "eq"])

    def stream_loop(self) -> None:
        if not self.ws:
            raise RuntimeError("WebSocket is not connected.")

        LOGGER.info(
            "Streaming cognitive state to OSC %s:%s and CSV %s",
            self.config.osc_host,
            self.config.osc_port,
            self.config.csv_path,
        )
        while True:
            raw_message = self.ws.recv()
            message = json.loads(raw_message)
            state = self.parser.handle_sample(message)
            if state is None:
                self._handle_event_message(message)
                continue

            smoothed_state = self.smoother.update(state)
            self.csv_logger.log(smoothed_state)
            self.osc_sender.send_state(smoothed_state)
            self._build_diffusion_placeholders(smoothed_state)
            self._log_stream_state(smoothed_state)

    def run_forever(self) -> None:
        while True:
            try:
                self.setup()
                self.stream_loop()
            except KeyboardInterrupt:
                LOGGER.info("Stopping bridge")
                raise
            except Exception as exc:  # noqa: BLE001
                if "-32019" in str(exc):
                    LOGGER.error(
                        "Active session quota is exhausted. Increase EMOTIV_AUTHORIZE_DEBIT "
                        "or close/reuse existing licensed sessions in EMOTIV Launcher."
                    )
                LOGGER.exception("Bridge failure: %s", exc)
                self.close()
                LOGGER.info(
                    "Retrying in %.1f seconds", self.config.reconnect_delay_seconds
                )
                time.sleep(self.config.reconnect_delay_seconds)

    def close(self) -> None:
        if self.ws is not None:
            try:
                self.ws.close()
            finally:
                self.ws = None

    def _discover_headset(self) -> str:
        headsets = self.queryHeadsets()
        if not headsets:
            raise RuntimeError("No EMOTIV headset detected.")

        if self.config.headset_id:
            for headset in headsets:
                if headset.get("id") == self.config.headset_id:
                    return self.config.headset_id
            raise RuntimeError(f"Configured headset {self.config.headset_id} not found.")

        first = headsets[0].get("id")
        if not first:
            raise RuntimeError(f"Invalid headset payload: {headsets[0]}")
        LOGGER.info("Using detected headset %s", first)
        return first

    def _connect_headset(self, headset_id: str) -> None:
        self.controlDevice("connect", headset_id)
        LOGGER.info("Requested headset connection for %s", headset_id)
        time.sleep(2.0)

    def _rpc(self, method: str, params: dict[str, Any]) -> Any:
        if not self.ws:
            raise RuntimeError("WebSocket is not connected.")
        self.request_id += 1
        payload = {
            "id": self.request_id,
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        self.ws.send(json.dumps(payload))

        while True:
            response = json.loads(self.ws.recv())
            if response.get("id") != self.request_id:
                self._handle_event_message(response)
                continue
            if "error" in response:
                raise RuntimeError(f"{method} failed: {response['error']}")
            return response["result"]

    @staticmethod
    def _handle_event_message(message: dict[str, Any]) -> None:
        warning = message.get("warning")
        if warning is not None:
            LOGGER.warning("Cortex warning: %s", warning)
        elif message.get("sys") is not None:
            LOGGER.info("System event: %s", message)

    def _build_diffusion_placeholders(self, state: Any) -> dict[str, Any]:
        return {
            "cfg": map_engagement_to_cfg_scale(state),
            "noise": map_stress_to_noise_strength(state),
            "prompt": map_interest_to_prompt_weighting(state),
            "stabilization": map_relaxation_to_image_stabilization(state),
        }

    def _log_stream_state(self, state: Any) -> None:
        now = time.time()
        if self._has_live_metrics(state):
            if now - self.last_met_log_time >= MET_LOG_INTERVAL_SECONDS:
                LOGGER.info(
                    "met eng=%.3f stress=%.3f interest=%.3f relax=%.3f exc=%.3f contact=%s signal=%s",
                    self._metric_or_zero(state.engagement),
                    self._metric_or_zero(state.stress),
                    self._metric_or_zero(state.interest),
                    self._metric_or_zero(state.relaxation),
                    self._metric_or_zero(state.excitement),
                    self._format_optional(state.overall_contact),
                    self._format_optional(state.signal),
                )
                self.last_met_log_time = now

        if state.pow_active and now - self.last_pow_log_time >= POW_LOG_INTERVAL_SECONDS:
            LOGGER.info(
                "pow alpha=%s beta=%s gamma=%s theta=%s contact=%s",
                self._format_optional(state.alpha_power),
                self._format_optional(state.beta_power),
                self._format_optional(state.gamma_power),
                self._format_optional(state.theta_power),
                self._format_optional(state.overall_contact),
            )
            self.last_pow_log_time = now

        if (
            state.overall_contact is not None
            and state.overall_contact < LOW_CONTACT_THRESHOLD
            and now - self.last_contact_log_time >= CONTACT_LOG_INTERVAL_SECONDS
        ):
            LOGGER.warning(
                "Low contact quality overall_contact=%s signal=%s battery=%s sample_rate_quality=%s",
                self._format_optional(state.overall_contact),
                self._format_optional(state.signal),
                self._format_optional(state.battery_percent),
                self._format_optional(state.sample_rate_quality),
            )
            self.last_contact_log_time = now

    @staticmethod
    def _has_live_metrics(state: Any) -> bool:
        return any(
            metric is not None
            for metric in [
                state.engagement,
                state.stress,
                state.interest,
                state.relaxation,
                state.excitement,
                state.long_term_excitement,
                state.attention,
            ]
        )

    @staticmethod
    def _metric_or_zero(value: float | None) -> float:
        return 0.0 if value is None else float(value)

    @staticmethod
    def _format_optional(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.3f}"


def main() -> None:
    config = BridgeConfig.from_env()
    bridge = CortexBridge(config)
    bridge.run_forever()


if __name__ == "__main__":
    main()
