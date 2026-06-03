from __future__ import annotations

from emotiv_bridge.config import BridgeConfig
from emotiv_bridge.csv_logger import CognitiveCsvLogger


def main() -> None:
    config = BridgeConfig.from_env()
    logger = CognitiveCsvLogger(config.csv_path)
    with config.csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        csv_file.write(",".join(logger.FIELDNAMES) + "\n")
    print(f"Cleared metrics CSV: {config.csv_path}")


if __name__ == "__main__":
    main()
