from __future__ import annotations

import json
import random
from urllib.parse import urlsplit, urlunsplit

from .config import ProxyConfig


def select_playwright_proxy(config: ProxyConfig) -> tuple[dict[str, str] | None, str]:
    if not config.enabled or config.mode == "off":
        return None, "proxy disabled"

    if config.mode == "local":
        proxy = config.as_playwright_proxy(config.local_server)
        return proxy, f"local proxy {redact_proxy_server(config.local_server)}"

    if config.mode == "single":
        proxy = config.as_playwright_proxy(config.server)
        return proxy, f"single proxy {redact_proxy_server(config.server)}"

    if config.mode == "provider_rotating":
        proxy = config.as_playwright_proxy(config.server)
        return proxy, f"provider rotating endpoint {redact_proxy_server(config.server)}"

    selected = select_rotating_server(config)
    proxy = config.as_playwright_proxy(selected)
    return proxy, f"auto rotator selected {redact_proxy_server(selected)}"


def select_rotating_server(config: ProxyConfig) -> str:
    if not config.servers:
        raise ValueError("No proxies are configured for auto rotator mode")

    if config.rotation_strategy == "random":
        return random.choice(config.servers)

    state = read_rotation_state(config)
    current_index = int(state.get("index", 0))
    selected = config.servers[current_index % len(config.servers)]
    state["index"] = current_index + 1
    write_rotation_state(config, state)
    return selected


def read_rotation_state(config: ProxyConfig) -> dict[str, int]:
    path = config.rotation_state_path
    if not path.exists():
        return {"index": 0}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"index": 0}
    if not isinstance(data, dict):
        return {"index": 0}
    return {"index": int(data.get("index", 0))}


def write_rotation_state(config: ProxyConfig, state: dict[str, int]) -> None:
    path = config.rotation_state_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def redact_proxy_server(server: str) -> str:
    parsed = urlsplit(server)
    if not parsed.netloc or "@" not in parsed.netloc:
        return server
    safe_netloc = "***:***@" + parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit((parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment))
