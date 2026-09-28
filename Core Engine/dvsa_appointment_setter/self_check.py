from __future__ import annotations

import argparse
import compileall
from datetime import datetime
from pathlib import Path

from .config import CORE_ROOT, SOFTWARE_ROOT, load_config
from .logger import MarkdownProcessLogger
from .matcher import AvailabilityMatcher
from .ui_server import HTML


INSTRUCTION_PATH = SOFTWARE_ROOT.parent / "Instructions" / "instructions.md"
DEVELOPMENT_LOG_PATH = SOFTWARE_ROOT / "Logs" / "development log.md"
PROCESS_LOG_PATH = SOFTWARE_ROOT / "Logs" / "process Log.md"
ROOT_LAUNCHER_PATH = SOFTWARE_ROOT / "Launcher.bat"
LOCAL_CONFIG_PATH = CORE_ROOT / "config.local.json"
EXAMPLE_CONFIG_PATH = CORE_ROOT / "config.example.json"


class CheckFailed(RuntimeError):
    pass


def run_three_pass_review() -> int:
    instruction_text = read_instruction_file()
    development_log = MarkdownProcessLogger(DEVELOPMENT_LOG_PATH)
    process_log = MarkdownProcessLogger(PROCESS_LOG_PATH)

    checks = [
        check_instruction_file,
        check_root_launcher,
        check_python_sources,
        check_config_loading,
        check_matcher,
        check_ui_markup,
    ]

    for pass_number in range(1, 4):
        print(f"Review pass {pass_number}")
        for check in checks:
            check(instruction_text)
        message = f"Review pass {pass_number}: I ran the repeatable project checks and they passed."
        development_log.append(message)
        process_log.append(f"review pass {pass_number}", "repeatable project checks passed")
        print("  passed")

    print("All three review passes passed.")
    return 0


def read_instruction_file() -> str:
    if not INSTRUCTION_PATH.exists():
        raise CheckFailed(f"Instruction file not found: {INSTRUCTION_PATH}")
    return INSTRUCTION_PATH.read_text(encoding="utf-8")


def check_instruction_file(instruction_text: str) -> None:
    required_bits = [
        "automated appointment setter",
        "Autoratating proxy",
        "development log.md",
        "process Log.md",
        "Software folder",
        "night mode",
        "Launcher",
    ]
    lowered = instruction_text.lower()
    missing = [item for item in required_bits if item.lower() not in lowered]
    if missing:
        raise CheckFailed("Instruction file is missing expected wording: " + ", ".join(missing))


def check_root_launcher(_: str) -> None:
    if not ROOT_LAUNCHER_PATH.exists():
        raise CheckFailed("Launcher.bat is missing from the Software root folder")
    content = ROOT_LAUNCHER_PATH.read_text(encoding="utf-8")
    if "instructions.md" not in content or "ui_server" not in content:
        raise CheckFailed("Launcher.bat does not check instructions and start the UI server")


def check_python_sources(_: str) -> None:
    ok = compileall.compile_dir(str(CORE_ROOT / "dvsa_appointment_setter"), quiet=1)
    if not ok:
        raise CheckFailed("Python compilation check failed")


def check_config_loading(_: str) -> None:
    config_path = LOCAL_CONFIG_PATH if LOCAL_CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    config = load_config(config_path)
    if config.search.poll_seconds < 60:
        raise CheckFailed("poll_seconds must stay at 60 or higher")
    if not config.search.start_url.startswith("https://"):
        raise CheckFailed("start_url must stay on HTTPS")


def check_matcher(_: str) -> None:
    matcher = AvailabilityMatcher(
        ["London Mill Hill"],
        ["available"],
        "2026-10-01",
        "2026-10-31",
    )
    result = matcher.evaluate("London Mill Hill has an available test on 12 October 2026")
    if not result.found:
        raise CheckFailed("matcher did not find the sample appointment text")


def check_ui_markup(_: str) -> None:
    required_bits = [
        "DVSA Appointment Setter",
        "Night",
        "Day",
        "Launch Assistant",
        "Proxy enabled",
        "--coffee",
        "--bg",
    ]
    missing = [item for item in required_bits if item not in HTML]
    if missing:
        raise CheckFailed("UI markup is missing expected controls: " + ", ".join(missing))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the DVSA Appointment Setter three-pass project review."
    )
    parser.add_argument(
        "--stamp",
        action="store_true",
        help="Print a timestamp before running checks.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.stamp:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    try:
        return run_three_pass_review()
    except CheckFailed as exc:
        print(f"Review failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
