from typing import Mapping, Dict
import os
from pathlib import Path

from .validate import ConfigParseError, UnknownConfigKey

def parse_dotenv(path: Path) -> Dict[str, str]:
    if not path.is_file():
        return {}

    result = {}
    with open(path, "r", encoding="utf-8") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                raise ConfigParseError(f"Malformed .env at line {line_number}")

            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            if val.startswith('"') and val.endswith('"') and len(val) >= 2:
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'") and len(val) >= 2:
                val = val[1:-1]
            result[key] = val
    return result

def overlay_env(env_mapping: Mapping[str, str]) -> Dict[str, str]:
    SUPPORTED_SBD_KEYS = {
        "SBD_LOG_LEVEL",
        "SBD_MQTT_USERNAME",
        "SBD_MQTT_PASSWORD"
    }

    updates = {}
    for k, v in env_mapping.items():
        if k.startswith("SBD_"):
            if k not in SUPPORTED_SBD_KEYS:
                raise UnknownConfigKey(f"Unknown environment variable: {k}")
            updates[k] = v

    return updates
