# Development Log

- 2026-09-28 16:58 | I set up the first working structure inside the Software folder so the bot code, config, logs, and operator notes all stay in the agreed place.
- 2026-09-28 17:06 | I chose a headful browser assistant design because the DVSA service needs the learner to handle security checks and final confirmation personally.
- 2026-09-28 17:16 | I added Playwright as the browser layer, a JSON config file, matching rules for centre/date/keyword checks, and optional proxy endpoint support.
- 2026-09-28 17:24 | I kept runtime logging separate from this development log so day-to-day checks can be reviewed without mixing them with build notes.
- 2026-09-28 17:42 | I added a local control panel with warm brown and beige styling, a night mode switch, config editing, log viewing, and a launch button.
- 2026-09-28 17:55 | I checked the updated instruction file first, then added the main Launcher.bat in the Software root and updated the operating notes to point at it.
- 2026-09-28 18:00 | Review pass 1: I ran the compile and help checks, then improved Launcher.bat so it gives a clear message if Python is missing or the UI server exits with an error.
- 2026-09-28 18:06 | Review pass 2: I checked the UI health, config, and log endpoints, then made the launch response tell me when the assistant is already running instead of always saying it started.
- 2026-09-28 18:12 | Review pass 3: I checked config loading, matcher behavior, and compilation again, then made Launcher.bat work with either python or the Windows py launcher.
- 2026-09-28 18:22 | I checked the instruction file first, then added a repeatable three-pass self-check command so future development runs can test the same launcher, config, UI, and matcher basics.
- 2026-09-28 17:26:12 | Review pass 1: I ran the repeatable project checks and they passed.
- 2026-09-28 17:26:12 | Review pass 2: I ran the repeatable project checks and they passed.
- 2026-09-28 17:26:12 | Review pass 3: I ran the repeatable project checks and they passed.
