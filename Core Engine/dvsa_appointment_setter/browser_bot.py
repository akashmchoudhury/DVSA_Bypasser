from __future__ import annotations

import asyncio
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from .config import AppConfig
from .logger import MarkdownProcessLogger
from .matcher import AvailabilityMatcher


class AppointmentAssistant:
    def __init__(self, config: AppConfig, logger: MarkdownProcessLogger) -> None:
        self.config = config
        self.logger = logger
        self.matcher = AvailabilityMatcher(
            centres=config.search.preferred_test_centres,
            keywords=config.search.preferred_keywords,
            date_from=config.search.preferred_date_from,
            date_to=config.search.preferred_date_to,
        )

    async def run(self, once: bool = False) -> None:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. Run: python -m pip install -r requirements.txt"
            ) from exc

        self.config.browser.user_data_dir.mkdir(parents=True, exist_ok=True)
        self.logger.append("session started", "browser automation launched")

        async with async_playwright() as playwright:
            launch_options = {
                "headless": self.config.browser.headless,
                "slow_mo": self.config.browser.slow_mo_ms,
                "timeout": self.config.browser.navigation_timeout_ms,
            }
            proxy = self.config.proxy.as_playwright_proxy()
            if proxy:
                launch_options["proxy"] = proxy
                self.logger.append("proxy enabled", "using configured proxy endpoint")

            context = await playwright.chromium.launch_persistent_context(
                user_data_dir=str(self.config.browser.user_data_dir),
                **launch_options,
            )
            page = context.pages[0] if context.pages else await context.new_page()
            page.set_default_timeout(self.config.browser.navigation_timeout_ms)

            try:
                await page.goto(self.config.search.start_url, wait_until="domcontentloaded")
                self.logger.append("opened start page", self.config.search.start_url)

                if self.config.browser.click_start_now:
                    await self._click_start_now(page, PlaywrightTimeoutError)

                if self.config.candidate.autofill_known_fields:
                    await self._autofill_known_fields(page)

                print()
                print("The browser is open. Complete any DVSA security and navigation steps.")
                print("Go to the page where appointment results or slots are visible.")
                input("Press Enter here when that page is ready, then monitoring will start.")

                await self._monitor(page, once=once)
            finally:
                self.logger.append("session closed", "browser context closed")
                await context.close()

    async def _click_start_now(self, page, timeout_error_type: type[Exception]) -> None:
        try:
            start_link = page.get_by_role("link", name=re.compile("start now", re.I))
            await start_link.first.click()
            await page.wait_for_load_state("domcontentloaded")
            self.logger.append("clicked start now", "moved from GOV.UK content page to service")
        except timeout_error_type:
            self.logger.append("start now not clicked", "link not found before timeout")
        except Exception as exc:
            self.logger.append("start now not clicked", str(exc))

    async def _autofill_known_fields(self, page) -> None:
        fields = [
            (
                re.compile("driving licence", re.I),
                self.config.candidate.driving_licence_number,
                "driving licence number",
            ),
            (
                re.compile("test reference|booking reference", re.I),
                self.config.candidate.driving_test_reference,
                "driving test reference",
            ),
            (
                re.compile("theory.*pass|pass certificate", re.I),
                self.config.candidate.theory_test_pass_number,
                "theory test pass number",
            ),
        ]

        for label_pattern, value, description in fields:
            if not value:
                continue
            try:
                await page.get_by_label(label_pattern).first.fill(value)
                self.logger.append("field filled", description)
            except Exception:
                self.logger.append("field skipped", f"{description} field was not visible")

    async def _monitor(self, page, once: bool) -> None:
        check_count = 0
        max_checks = 1 if once else self.config.search.max_checks

        while True:
            if self.config.search.service_hours_only and not self._inside_service_hours():
                print()
                print("The DVSA service is outside the configured 06:00-23:40 UK window.")
                print(f"Waiting {self.config.search.poll_seconds} seconds before checking again.")
                self.logger.append("waiting", "outside configured DVSA service hours")
                await asyncio.sleep(self.config.search.poll_seconds)
                continue

            check_count += 1
            text = await self._read_body_text(page)
            result = self.matcher.evaluate(text)
            self.logger.append(
                "availability check",
                f"check {check_count}; {result.summary()}",
            )

            print()
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Check {check_count}: {result.summary()}")
            if result.snippets:
                print("Matched page text:")
                for snippet in result.snippets:
                    print(f"  - {snippet}")

            if result.found:
                self._alert_user()
                self.logger.append("match found", result.summary())
                print()
                print("A possible matching appointment is visible in the browser.")
                print("Review it yourself before changing, booking, paying, or confirming.")
                decision = input("Type stop to end, or press Enter to keep monitoring: ").strip().lower()
                if decision == "stop":
                    return

            if max_checks and check_count >= max_checks:
                self.logger.append("monitoring stopped", "maximum check count reached")
                return

            await asyncio.sleep(self.config.search.poll_seconds)
            if self.config.search.refresh_between_checks:
                await page.reload(wait_until="domcontentloaded")

    async def _read_body_text(self, page) -> str:
        try:
            return await page.locator("body").inner_text(timeout=15000)
        except Exception as exc:
            self.logger.append("page text read failed", str(exc))
            return ""

    def _alert_user(self) -> None:
        print("\a", end="")
        try:
            import winsound

            winsound.Beep(1200, 400)
            winsound.Beep(1500, 400)
        except Exception:
            return

    def _inside_service_hours(self) -> bool:
        uk_now = datetime.now(ZoneInfo("Europe/London"))
        minutes = uk_now.hour * 60 + uk_now.minute
        return (6 * 60) <= minutes <= (23 * 60 + 40)


def run_assistant(config: AppConfig, logger: MarkdownProcessLogger, once: bool = False) -> None:
    asyncio.run(AppointmentAssistant(config, logger).run(once=once))
