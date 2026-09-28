from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime


MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}


@dataclass(frozen=True)
class MatchResult:
    found: bool
    reasons: list[str]
    snippets: list[str]

    def summary(self) -> str:
        if not self.reasons:
            return "no matching appointment text found"
        return "; ".join(self.reasons)


class AvailabilityMatcher:
    def __init__(
        self,
        centres: list[str],
        keywords: list[str],
        date_from: str = "",
        date_to: str = "",
    ) -> None:
        self.centres = [item.lower() for item in centres if item.strip()]
        self.keywords = [item.lower() for item in keywords if item.strip()]
        self.date_from = parse_config_date(date_from) if date_from else None
        self.date_to = parse_config_date(date_to) if date_to else None

    def evaluate(self, page_text: str) -> MatchResult:
        lowered = page_text.lower()
        reasons: list[str] = []
        snippets: list[str] = []

        centre_hits = [centre for centre in self.centres if centre in lowered]
        if centre_hits:
            reasons.append("centre matched: " + ", ".join(centre_hits))
            snippets.extend(find_snippets(page_text, centre_hits))

        keyword_hits = [keyword for keyword in self.keywords if keyword in lowered]
        if keyword_hits:
            reasons.append("keyword matched: " + ", ".join(keyword_hits))
            snippets.extend(find_snippets(page_text, keyword_hits))

        date_hits = self._matching_dates(page_text)
        if date_hits:
            reasons.append(
                "date matched: " + ", ".join(item.strftime("%Y-%m-%d") for item in date_hits)
            )
            snippets.extend(find_snippets(page_text, [item.strftime("%d") for item in date_hits]))

        has_filters = bool(self.centres or self.keywords or self.date_from or self.date_to)
        if not has_filters:
            availability_words = [
                "available",
                "appointment",
                "test slot",
                "change to this test",
                "book this test",
            ]
            if any(word in lowered for word in availability_words):
                reasons.append("availability wording found")
                snippets.extend(find_snippets(page_text, availability_words))

        found = bool(reasons)
        return MatchResult(found=found, reasons=reasons, snippets=unique_list(snippets)[:5])

    def _matching_dates(self, page_text: str) -> list[date]:
        if not self.date_from and not self.date_to:
            return []

        dates = extract_dates(page_text)
        matched: list[date] = []
        for candidate in dates:
            if self.date_from and candidate < self.date_from:
                continue
            if self.date_to and candidate > self.date_to:
                continue
            matched.append(candidate)
        return unique_dates(matched)


def parse_config_date(value: str) -> date:
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %B %Y", "%d %b %Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Could not parse date '{value}'. Use YYYY-MM-DD.")


def extract_dates(text: str) -> list[date]:
    found: list[date] = []

    for match in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", text):
        day = int(match.group(1))
        month = int(match.group(2))
        year = normalize_year(int(match.group(3)))
        maybe_add_date(found, year, month, day)

    month_names = "|".join(sorted(MONTHS.keys(), key=len, reverse=True))
    pattern = re.compile(
        rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_names})\s+(\d{{4}})\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        day = int(match.group(1))
        month = MONTHS[match.group(2).lower()]
        year = int(match.group(3))
        maybe_add_date(found, year, month, day)

    return found


def normalize_year(year: int) -> int:
    if year < 100:
        return 2000 + year
    return year


def maybe_add_date(items: list[date], year: int, month: int, day: int) -> None:
    try:
        items.append(date(year, month, day))
    except ValueError:
        return


def find_snippets(text: str, needles: list[str]) -> list[str]:
    snippets: list[str] = []
    lowered = text.lower()
    for needle in needles:
        if not needle:
            continue
        index = lowered.find(needle.lower())
        if index == -1:
            continue
        start = max(0, index - 90)
        end = min(len(text), index + len(needle) + 90)
        snippet = " ".join(text[start:end].split())
        if snippet:
            snippets.append(snippet)
    return snippets


def unique_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output


def unique_dates(items: list[date]) -> list[date]:
    seen: set[date] = set()
    output: list[date] = []
    for item in sorted(items):
        if item not in seen:
            output.append(item)
            seen.add(item)
    return output
