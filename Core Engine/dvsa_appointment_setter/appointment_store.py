from __future__ import annotations

import csv
from datetime import date, datetime
from pathlib import Path
from typing import Any

from .config import SOFTWARE_ROOT


STORAGE_ROOT = SOFTWARE_ROOT / "Storage"
DAILY_TARGET = 10
HEADERS = [
    "recorded_at",
    "action",
    "learner_name",
    "driving_licence_last4",
    "test_centre",
    "appointment_date",
    "appointment_time",
    "booking_reference",
    "proxy_mode",
    "proxy_label",
    "notes",
]


def appointment_csv_path(day: date | None = None) -> Path:
    selected_day = day or date.today()
    return STORAGE_ROOT / f"Appointment_{selected_day.isoformat()}.csv"


def append_appointment(record: dict[str, Any], proxy_mode: str, proxy_label: str) -> dict[str, Any]:
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    path = appointment_csv_path()
    row = normalize_record(record, proxy_mode=proxy_mode, proxy_label=proxy_label)
    write_header = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)
    return dashboard_data()


def dashboard_data() -> dict[str, Any]:
    path = appointment_csv_path()
    rows = read_appointments(path)
    count = len(rows)
    return {
        "date": date.today().isoformat(),
        "path": str(path),
        "count": count,
        "target": DAILY_TARGET,
        "remaining": max(0, DAILY_TARGET - count),
        "complete": count >= DAILY_TARGET,
        "appointments": rows,
    }


def read_appointments(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [{key: row.get(key, "") for key in HEADERS} for row in reader]


def normalize_record(
    record: dict[str, Any],
    proxy_mode: str,
    proxy_label: str,
) -> dict[str, str]:
    action = clean(record.get("action", "changed")).lower()
    if action not in {"booked", "changed"}:
        raise ValueError("appointment action must be booked or changed")

    return {
        "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "learner_name": clean(record.get("learner_name", "")),
        "driving_licence_last4": clean(record.get("driving_licence_last4", ""))[:4],
        "test_centre": clean(record.get("test_centre", "")),
        "appointment_date": clean(record.get("appointment_date", "")),
        "appointment_time": clean(record.get("appointment_time", "")),
        "booking_reference": clean(record.get("booking_reference", "")),
        "proxy_mode": clean(proxy_mode),
        "proxy_label": clean(proxy_label),
        "notes": clean(record.get("notes", "")),
    }


def clean(value: Any) -> str:
    return " ".join(str(value).strip().split())
