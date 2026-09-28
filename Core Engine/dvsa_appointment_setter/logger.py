from __future__ import annotations

from datetime import datetime
from pathlib import Path


class MarkdownProcessLogger:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("# Process Log\n\n", encoding="utf-8")

    def append(self, event: str, details: str = "") -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        safe_event = event.strip() or "event"
        safe_details = details.strip()
        line = f"- {timestamp} | {safe_event}"
        if safe_details:
            line += f" | {safe_details}"
        line += "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(line)
