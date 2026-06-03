from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass
class BridgeConfig:
    client_id: str
    client_secret: str
    emotiv_id: str | None = None
    cortex_url: str = "wss://localhost:6868"
    headset_id: str | None = None
    osc_host: str = "127.0.0.1"
    osc_port: int = 7000
    csv_path: Path = Path("logs/cognitive_metrics.csv")
    reconnect_delay_seconds: float = 3.0
    request_access: bool = True
    activate_session: bool = False

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        load_dotenv()
        csv_path = Path(os.getenv("EMOTIV_CSV_PATH", "logs/cognitive_metrics.csv"))
        return cls(
            client_id=os.getenv("EMOTIV_CLIENT_ID", ""),
            client_secret=os.getenv("EMOTIV_CLIENT_SECRET", ""),
            emotiv_id=os.getenv("EMOTIV_ID"),
            cortex_url=os.getenv("EMOTIV_CORTEX_URL", "wss://localhost:6868"),
            headset_id=os.getenv("EMOTIV_HEADSET_ID"),
            osc_host=os.getenv("EMOTIV_OSC_HOST", "127.0.0.1"),
            osc_port=int(os.getenv("EMOTIV_OSC_PORT", "7000")),
            csv_path=csv_path,
            reconnect_delay_seconds=float(
                os.getenv("EMOTIV_RECONNECT_DELAY_SECONDS", "3.0")
            ),
            request_access=os.getenv("EMOTIV_REQUEST_ACCESS", "true").lower()
            not in {"0", "false", "no"},
            activate_session=os.getenv("EMOTIV_ACTIVATE_SESSION", "false").lower()
            in {"1", "true", "yes"},
        )

    def validate(self) -> None:
        if not self.client_id:
            raise ValueError("EMOTIV_CLIENT_ID is required.")
        if not self.client_secret:
            raise ValueError("EMOTIV_CLIENT_SECRET is required.")
