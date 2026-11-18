"""Explicit file configuration for the native CLI; never exports environment variables."""

import json
from pathlib import Path
from typing import Any

STARTUP_TYPES = {
    'DATA_DIR': str,
    'WEBUI_ADMIN_EMAIL': str,
    'WEBUI_ADMIN_NAME': str,
    'USE_SLIM_DOCKER': bool,
    'ENABLE_TOOL_SERVERS': bool,
    'ENABLE_ADMIN_CHAT_ACCESS': bool,
    'BYPASS_ADMIN_ACCESS_CONTROL': bool,
}
startup: dict[str, Any] = {}
config: dict[str, Any] = {}


def load(path: Path) -> None:
    document = json.loads(path.read_text())
    if not isinstance(document, dict) or set(document) - {'startup', 'config'}:
        raise ValueError('Configuration must contain only startup and config objects')
    proposed_startup = document.get('startup', {})
    proposed_config = document.get('config', {})
    if not isinstance(proposed_startup, dict) or not isinstance(proposed_config, dict):
        raise ValueError('startup and config must be objects')
    for key, value in proposed_startup.items():
        if key not in STARTUP_TYPES or type(value) is not STARTUP_TYPES[key]:
            raise ValueError(f'Unknown startup setting or invalid type: {key}')
    startup.clear()
    startup.update(proposed_startup)
    config.clear()
    config.update(proposed_config)


def registered_values(defaults: dict) -> dict:
    for key, value in config.items():
        if key not in defaults:
            raise ValueError(f'Unknown configuration setting: {key}')
        expected = defaults[key]
        if expected is not None and type(value) is not type(expected):
            raise ValueError(f'Invalid configuration type: {key}')
    return dict(config)
