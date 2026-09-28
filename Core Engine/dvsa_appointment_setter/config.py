from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SOFTWARE_ROOT = Path(__file__).resolve().parents[2]
CORE_ROOT = Path(__file__).resolve().parents[1]

ALLOWED_SERVICE_HOSTS = {
    "www.gov.uk",
    "driverpracticaltest.dvsa.gov.uk",
}

PROXY_MODES = {"off", "local", "single", "provider_rotating", "rotating_list"}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def default_config() -> dict[str, Any]:
    return {
        "candidate": {
            "driving_licence_number": "",
            "driving_test_reference": "",
            "theory_test_pass_number": "",
            "autofill_known_fields": False,
        },
        "search": {
            "mode": "change-driving-test",
            "start_url": "https://www.gov.uk/change-driving-test",
            "preferred_test_centres": [],
            "preferred_keywords": [],
            "preferred_date_from": "",
            "preferred_date_to": "",
            "poll_seconds": 180,
            "rate_limit_jitter_seconds": 20,
            "error_backoff_seconds": 300,
            "rate_limit_cooldown_seconds": 3600,
            "max_checks": 0,
            "refresh_between_checks": True,
            "stop_before_final_confirmation": True,
            "service_hours_only": True,
        },
        "proxy": {
            "enabled": False,
            "mode": "off",
            "server": "",
            "local_server": "http://127.0.0.1:8080",
            "servers": [],
            "username": "",
            "password": "",
            "rotation_strategy": "round_robin",
            "rotation_state_path": ".proxy-rotation-state.json",
            "provider_managed_rotating_endpoint": True,
        },
        "browser": {
            "headless": False,
            "slow_mo_ms": 80,
            "user_data_dir": ".browser-profile",
            "click_start_now": True,
            "navigation_timeout_ms": 45000,
        },
        "logging": {
            "process_log_path": "../Logs/process Log.md",
        },
    }


@dataclass(frozen=True)
class CandidateConfig:
    driving_licence_number: str
    driving_test_reference: str
    theory_test_pass_number: str
    autofill_known_fields: bool


@dataclass(frozen=True)
class SearchConfig:
    mode: str
    start_url: str
    preferred_test_centres: list[str]
    preferred_keywords: list[str]
    preferred_date_from: str
    preferred_date_to: str
    poll_seconds: int
    rate_limit_jitter_seconds: int
    error_backoff_seconds: int
    rate_limit_cooldown_seconds: int
    max_checks: int
    refresh_between_checks: bool
    stop_before_final_confirmation: bool
    service_hours_only: bool


@dataclass(frozen=True)
class ProxyConfig:
    enabled: bool
    mode: str
    server: str
    local_server: str
    servers: list[str]
    username: str
    password: str
    rotation_strategy: str
    rotation_state_path: Path
    provider_managed_rotating_endpoint: bool

    def as_playwright_proxy(self, server: str | None = None) -> dict[str, str] | None:
        if not self.enabled:
            return None
        selected_server = server or self.server
        if not selected_server:
            return None
        proxy = {"server": selected_server}
        if self.username:
            proxy["username"] = self.username
        if self.password:
            proxy["password"] = self.password
        return proxy


@dataclass(frozen=True)
class BrowserConfig:
    headless: bool
    slow_mo_ms: int
    user_data_dir: Path
    click_start_now: bool
    navigation_timeout_ms: int


@dataclass(frozen=True)
class LoggingConfig:
    process_log_path: Path


@dataclass(frozen=True)
class AppConfig:
    candidate: CandidateConfig
    search: SearchConfig
    proxy: ProxyConfig
    browser: BrowserConfig
    logging: LoggingConfig
    config_path: Path


def _resolve_path(value: str, base_dir: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _require_string_list(value: Any, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings")
    output: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(f"{field_name} must be a list of strings")
        cleaned = item.strip()
        if cleaned:
            output.append(cleaned)
    return output


def _normalize_proxy_server(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return ""
    if "://" not in cleaned:
        return f"http://{cleaned}"
    return cleaned


def validate_start_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in ALLOWED_SERVICE_HOSTS:
        allowed = ", ".join(sorted(ALLOWED_SERVICE_HOSTS))
        raise ValueError(f"start_url must be an HTTPS URL on one of: {allowed}")


def load_config(config_path: str | Path) -> AppConfig:
    path = Path(config_path).resolve()
    raw: dict[str, Any] = {}
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

    data = _deep_merge(default_config(), raw)
    candidate = data["candidate"]
    search = data["search"]
    proxy = data["proxy"]
    browser = data["browser"]
    logging = data["logging"]

    validate_start_url(str(search["start_url"]))

    poll_seconds = int(search["poll_seconds"])
    if poll_seconds < 60:
        raise ValueError("poll_seconds must be 60 or higher")

    rate_limit_jitter_seconds = int(search.get("rate_limit_jitter_seconds", 0))
    if rate_limit_jitter_seconds < 0:
        raise ValueError("rate_limit_jitter_seconds must be 0 or higher")

    error_backoff_seconds = int(search.get("error_backoff_seconds", 300))
    if error_backoff_seconds < poll_seconds:
        raise ValueError("error_backoff_seconds must be equal to or higher than poll_seconds")

    rate_limit_cooldown_seconds = int(search.get("rate_limit_cooldown_seconds", 3600))
    if rate_limit_cooldown_seconds < error_backoff_seconds:
        raise ValueError(
            "rate_limit_cooldown_seconds must be equal to or higher than error_backoff_seconds"
        )

    max_checks = int(search["max_checks"])
    if max_checks < 0:
        raise ValueError("max_checks must be 0 or higher")

    proxy_enabled = bool(proxy["enabled"])
    proxy_mode = str(proxy.get("mode", "")).strip() or (
        "provider_rotating"
        if proxy_enabled and bool(proxy.get("provider_managed_rotating_endpoint", False))
        else "single"
        if proxy_enabled
        else "off"
    )
    if not proxy_enabled:
        proxy_mode = "off"
    if proxy_mode not in PROXY_MODES:
        raise ValueError(f"proxy.mode must be one of: {', '.join(sorted(PROXY_MODES))}")

    proxy_server = _normalize_proxy_server(str(proxy["server"]))
    local_proxy_server = _normalize_proxy_server(str(proxy.get("local_server", "")))
    proxy_servers = [
        _normalize_proxy_server(item)
        for item in _require_string_list(proxy.get("servers", []), "proxy.servers")
    ]
    rotation_strategy = str(proxy.get("rotation_strategy", "round_robin")).strip()
    if rotation_strategy not in {"round_robin", "random"}:
        raise ValueError("proxy.rotation_strategy must be round_robin or random")

    if proxy_enabled:
        if proxy_mode == "local" and not local_proxy_server:
            raise ValueError("proxy.local_server is required when proxy.mode is local")
        if proxy_mode in {"single", "provider_rotating"} and not proxy_server:
            raise ValueError("proxy.server is required for the selected proxy mode")
        if proxy_mode == "rotating_list" and not proxy_servers:
            raise ValueError("proxy.servers needs at least one entry for auto rotator mode")

    user_data_dir = _resolve_path(str(browser["user_data_dir"]), path.parent)
    process_log_path = _resolve_path(str(logging["process_log_path"]), path.parent)
    rotation_state_path = _resolve_path(
        str(proxy.get("rotation_state_path", ".proxy-rotation-state.json")), path.parent
    )

    return AppConfig(
        candidate=CandidateConfig(
            driving_licence_number=str(candidate["driving_licence_number"]).strip(),
            driving_test_reference=str(candidate["driving_test_reference"]).strip(),
            theory_test_pass_number=str(candidate["theory_test_pass_number"]).strip(),
            autofill_known_fields=bool(candidate["autofill_known_fields"]),
        ),
        search=SearchConfig(
            mode=str(search["mode"]).strip(),
            start_url=str(search["start_url"]).strip(),
            preferred_test_centres=_require_string_list(
                search["preferred_test_centres"], "search.preferred_test_centres"
            ),
            preferred_keywords=_require_string_list(
                search["preferred_keywords"], "search.preferred_keywords"
            ),
            preferred_date_from=str(search["preferred_date_from"]).strip(),
            preferred_date_to=str(search["preferred_date_to"]).strip(),
            poll_seconds=poll_seconds,
            rate_limit_jitter_seconds=rate_limit_jitter_seconds,
            error_backoff_seconds=error_backoff_seconds,
            rate_limit_cooldown_seconds=rate_limit_cooldown_seconds,
            max_checks=max_checks,
            refresh_between_checks=bool(search["refresh_between_checks"]),
            stop_before_final_confirmation=bool(search["stop_before_final_confirmation"]),
            service_hours_only=bool(search["service_hours_only"]),
        ),
        proxy=ProxyConfig(
            enabled=proxy_enabled,
            mode=proxy_mode,
            server=proxy_server,
            local_server=local_proxy_server,
            servers=proxy_servers,
            username=str(proxy["username"]).strip(),
            password=str(proxy["password"]),
            rotation_strategy=rotation_strategy,
            rotation_state_path=rotation_state_path,
            provider_managed_rotating_endpoint=bool(
                proxy["provider_managed_rotating_endpoint"]
            ),
        ),
        browser=BrowserConfig(
            headless=bool(browser["headless"]),
            slow_mo_ms=int(browser["slow_mo_ms"]),
            user_data_dir=user_data_dir,
            click_start_now=bool(browser["click_start_now"]),
            navigation_timeout_ms=int(browser["navigation_timeout_ms"]),
        ),
        logging=LoggingConfig(process_log_path=process_log_path),
        config_path=path,
    )
