from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .config import CORE_ROOT, SOFTWARE_ROOT, default_config, load_config
from .logger import MarkdownProcessLogger


CONFIG_PATH = CORE_ROOT / "config.local.json"
EXAMPLE_CONFIG_PATH = CORE_ROOT / "config.example.json"
DEVELOPMENT_LOG_PATH = SOFTWARE_ROOT / "Logs" / "development log.md"
PROCESS_LOG_PATH = SOFTWARE_ROOT / "Logs" / "process Log.md"
LAST_PROCESS: subprocess.Popen[str] | None = None


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DVSA Appointment Setter</title>
  <style>
    :root {
      --bg: #efe3d0;
      --surface: #fff8ed;
      --surface-strong: #f7ead7;
      --ink: #2b211a;
      --muted: #766556;
      --line: #d7c3aa;
      --coffee: #7b4f32;
      --coffee-strong: #5a3521;
      --sage: #426e64;
      --amber: #b46f28;
      --danger: #8e332a;
      --shadow: 0 18px 45px rgba(67, 43, 26, 0.16);
    }

    [data-theme="night"] {
      --bg: #191512;
      --surface: #261f1a;
      --surface-strong: #312820;
      --ink: #f4eadc;
      --muted: #c7b5a0;
      --line: #4b3b31;
      --coffee: #c58a57;
      --coffee-strong: #e2aa73;
      --sage: #79aaa0;
      --amber: #d49a53;
      --danger: #e07a68;
      --shadow: 0 18px 45px rgba(0, 0, 0, 0.32);
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.5 "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
      letter-spacing: 0;
    }

    button, input, textarea, select {
      font: inherit;
      color: inherit;
    }

    .shell {
      min-height: 100vh;
      padding: 22px;
    }

    .topbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 18px;
      max-width: 1180px;
      margin: 0 auto 18px;
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 0;
    }

    .mark {
      width: 38px;
      height: 38px;
      display: grid;
      place-items: center;
      border-radius: 8px;
      background: var(--coffee);
      color: #fff8ed;
      font-weight: 800;
      box-shadow: var(--shadow);
    }

    h1 {
      margin: 0;
      font-size: 24px;
      line-height: 1.1;
      font-weight: 750;
    }

    .subtitle {
      color: var(--muted);
      margin-top: 4px;
      font-size: 13px;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }

    .theme-switch {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px;
      border: 1px solid var(--line);
      border-radius: 999px;
      background: var(--surface);
    }

    .theme-switch button {
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--muted);
      min-width: 42px;
      height: 32px;
      cursor: pointer;
    }

    .theme-switch button.active {
      background: var(--coffee);
      color: #fff8ed;
    }

    .layout {
      max-width: 1180px;
      margin: 0 auto;
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(320px, 0.65fr);
      gap: 18px;
    }

    .panel {
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: var(--shadow);
      overflow: hidden;
    }

    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 20px;
      border-bottom: 1px solid var(--line);
      background: var(--surface-strong);
    }

    .panel-header h2 {
      margin: 0;
      font-size: 16px;
      line-height: 1.2;
    }

    .panel-body {
      padding: 18px 20px 20px;
    }

    .status-row {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .chip {
      display: inline-flex;
      align-items: center;
      gap: 7px;
      min-height: 30px;
      padding: 4px 10px;
      border-radius: 999px;
      background: color-mix(in srgb, var(--sage) 14%, transparent);
      color: var(--sage);
      border: 1px solid color-mix(in srgb, var(--sage) 30%, transparent);
      font-size: 13px;
      font-weight: 650;
    }

    .chip.warn {
      color: var(--amber);
      background: color-mix(in srgb, var(--amber) 14%, transparent);
      border-color: color-mix(in srgb, var(--amber) 30%, transparent);
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 14px;
    }

    .full { grid-column: 1 / -1; }

    label {
      display: grid;
      gap: 7px;
      min-width: 0;
      font-weight: 650;
      color: var(--ink);
    }

    .hint {
      color: var(--muted);
      font-size: 12px;
      font-weight: 500;
    }

    input, textarea, select {
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 7px;
      background: var(--surface);
      padding: 10px 11px;
      min-height: 42px;
      outline: none;
    }

    textarea {
      min-height: 96px;
      resize: vertical;
    }

    input:focus, textarea:focus, select:focus {
      border-color: var(--sage);
      box-shadow: 0 0 0 3px color-mix(in srgb, var(--sage) 18%, transparent);
    }

    .checks {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }

    .check {
      display: flex;
      align-items: center;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 7px;
      padding: 10px;
      background: color-mix(in srgb, var(--surface-strong) 62%, transparent);
      font-weight: 600;
    }

    .check input {
      width: 18px;
      height: 18px;
      min-height: 18px;
      accent-color: var(--coffee);
    }

    .actions {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }

    .btn {
      border: 1px solid transparent;
      border-radius: 7px;
      padding: 10px 14px;
      min-height: 42px;
      cursor: pointer;
      font-weight: 750;
      background: var(--coffee);
      color: #fff8ed;
    }

    .btn.secondary {
      background: transparent;
      color: var(--coffee-strong);
      border-color: var(--line);
    }

    .btn.accent {
      background: var(--sage);
      color: #f7fff9;
    }

    .btn:disabled {
      opacity: 0.58;
      cursor: wait;
    }

    .tabs {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }

    .tab {
      border: 1px solid var(--line);
      background: transparent;
      color: var(--muted);
      border-radius: 7px;
      padding: 8px 10px;
      cursor: pointer;
      font-weight: 700;
    }

    .tab.active {
      color: #fff8ed;
      background: var(--coffee);
      border-color: var(--coffee);
    }

    pre {
      margin: 0;
      white-space: pre-wrap;
      overflow: auto;
      max-height: 420px;
      padding: 14px;
      border-radius: 7px;
      border: 1px solid var(--line);
      background: color-mix(in srgb, var(--surface-strong) 76%, transparent);
      color: var(--ink);
      font: 13px/1.55 Consolas, "Cascadia Mono", monospace;
    }

    .toast {
      min-height: 24px;
      margin-top: 12px;
      color: var(--muted);
      font-weight: 600;
    }

    .toast.ok { color: var(--sage); }
    .toast.bad { color: var(--danger); }

    @media (max-width: 900px) {
      .shell { padding: 14px; }
      .topbar { align-items: flex-start; flex-direction: column; }
      .toolbar { width: 100%; justify-content: space-between; }
      .layout { grid-template-columns: 1fr; }
      .grid, .checks { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <header class="topbar">
      <div class="brand">
        <div class="mark">D</div>
        <div>
          <h1>DVSA Appointment Setter</h1>
          <div class="subtitle">Local control panel</div>
        </div>
      </div>
      <div class="toolbar">
        <div class="theme-switch" aria-label="Theme switcher">
          <button type="button" id="dayMode">Day</button>
          <button type="button" id="nightMode">Night</button>
        </div>
        <button class="btn accent" id="launchBtn" type="button">Launch Assistant</button>
      </div>
    </header>

    <section class="layout">
      <form class="panel" id="settingsForm">
        <div class="panel-header">
          <h2>Settings</h2>
          <div class="status-row">
            <span class="chip" id="configChip">Config</span>
            <span class="chip warn" id="proxyChip">Proxy off</span>
          </div>
        </div>
        <div class="panel-body">
          <div class="grid">
            <label class="full">Service URL
              <input id="startUrl" autocomplete="off">
            </label>

            <label>Preferred date from
              <input id="dateFrom" type="date">
            </label>

            <label>Preferred date to
              <input id="dateTo" type="date">
            </label>

            <label class="full">Test centres
              <textarea id="centres" spellcheck="false"></textarea>
              <span class="hint">One centre per line</span>
            </label>

            <label class="full">Matching keywords
              <textarea id="keywords" spellcheck="false"></textarea>
              <span class="hint">One keyword per line</span>
            </label>

            <label>Poll seconds
              <input id="pollSeconds" type="number" min="60" step="5">
            </label>

            <label>Jitter seconds
              <input id="jitterSeconds" type="number" min="0" step="5">
              <span class="hint">Adds a small random delay after each check</span>
            </label>

            <label>Error backoff seconds
              <input id="errorBackoffSeconds" type="number" min="60" step="30">
              <span class="hint">Used after reload or page-read errors</span>
            </label>

            <label>Rate limit cooldown seconds
              <input id="rateLimitCooldownSeconds" type="number" min="300" step="60">
              <span class="hint">Used when a search-limit or too-many-requests page is detected</span>
            </label>

            <label>Maximum checks
              <input id="maxChecks" type="number" min="0" step="1">
            </label>

            <label>Driving licence number
              <input id="licenceNumber" autocomplete="off">
            </label>

            <label>Driving test reference
              <input id="testReference" autocomplete="off">
            </label>

            <label>Theory pass number
              <input id="theoryNumber" autocomplete="off">
            </label>

            <label>Proxy mode
              <select id="proxyMode">
                <option value="off">Off</option>
                <option value="local">Local proxy</option>
                <option value="single">Single proxy</option>
                <option value="provider_rotating">Provider rotating endpoint</option>
                <option value="rotating_list">Auto rotator list</option>
              </select>
            </label>

            <label>Local proxy server
              <input id="localProxyServer" placeholder="http://127.0.0.1:8080" autocomplete="off">
            </label>

            <label>Proxy server
              <input id="proxyServer" placeholder="http://host:port" autocomplete="off">
              <span class="hint">Used by single proxy or provider rotating endpoint</span>
            </label>

            <label>Proxy username
              <input id="proxyUsername" autocomplete="off">
            </label>

            <label>Proxy password
              <input id="proxyPassword" type="password" autocomplete="off">
            </label>

            <label>Rotation strategy
              <select id="rotationStrategy">
                <option value="round_robin">Round robin</option>
                <option value="random">Random</option>
              </select>
            </label>

            <label class="full">Auto rotator proxy list
              <textarea id="proxyServers" spellcheck="false" placeholder="http://proxy-one:8000&#10;socks5://proxy-two:9000"></textarea>
              <span class="hint">One proxy per line. A different entry is selected on each assistant launch.</span>
            </label>

            <div class="checks full">
              <label class="check"><input id="proxyEnabled" type="checkbox"> Proxy enabled</label>
              <label class="check"><input id="rotatingProxy" type="checkbox"> Provider rotates this endpoint</label>
              <label class="check"><input id="autofill" type="checkbox"> Autofill known fields</label>
              <label class="check"><input id="refresh" type="checkbox"> Refresh between checks</label>
              <label class="check"><input id="serviceHours" type="checkbox"> Service hours only</label>
              <label class="check"><input id="clickStart" type="checkbox"> Click Start now</label>
            </div>
          </div>

          <div class="actions">
            <button class="btn" type="submit">Save Settings</button>
            <button class="btn secondary" id="reloadBtn" type="button">Reload</button>
            <button class="btn secondary" id="logsBtn" type="button">Refresh Logs</button>
          </div>
          <div class="toast" id="toast"></div>
        </div>
      </form>

      <aside class="panel">
        <div class="panel-header">
          <h2>Logs</h2>
          <span class="chip" id="processChip">Ready</span>
        </div>
        <div class="panel-body">
          <div class="tabs">
            <button class="tab active" id="processTab" type="button">Process</button>
            <button class="tab" id="devTab" type="button">Development</button>
          </div>
          <pre id="logOutput">Loading...</pre>
        </div>
      </aside>
    </section>
  </main>

  <script>
    const fields = {
      startUrl: document.querySelector("#startUrl"),
      dateFrom: document.querySelector("#dateFrom"),
      dateTo: document.querySelector("#dateTo"),
      centres: document.querySelector("#centres"),
      keywords: document.querySelector("#keywords"),
      pollSeconds: document.querySelector("#pollSeconds"),
      jitterSeconds: document.querySelector("#jitterSeconds"),
      errorBackoffSeconds: document.querySelector("#errorBackoffSeconds"),
      rateLimitCooldownSeconds: document.querySelector("#rateLimitCooldownSeconds"),
      maxChecks: document.querySelector("#maxChecks"),
      licenceNumber: document.querySelector("#licenceNumber"),
      testReference: document.querySelector("#testReference"),
      theoryNumber: document.querySelector("#theoryNumber"),
      proxyMode: document.querySelector("#proxyMode"),
      localProxyServer: document.querySelector("#localProxyServer"),
      proxyServer: document.querySelector("#proxyServer"),
      proxyServers: document.querySelector("#proxyServers"),
      proxyUsername: document.querySelector("#proxyUsername"),
      proxyPassword: document.querySelector("#proxyPassword"),
      rotationStrategy: document.querySelector("#rotationStrategy"),
      proxyEnabled: document.querySelector("#proxyEnabled"),
      rotatingProxy: document.querySelector("#rotatingProxy"),
      autofill: document.querySelector("#autofill"),
      refresh: document.querySelector("#refresh"),
      serviceHours: document.querySelector("#serviceHours"),
      clickStart: document.querySelector("#clickStart")
    };

    const toast = document.querySelector("#toast");
    const logOutput = document.querySelector("#logOutput");
    const configChip = document.querySelector("#configChip");
    const proxyChip = document.querySelector("#proxyChip");
    const processChip = document.querySelector("#processChip");
    let activeLog = "process";

    function splitLines(value) {
      return value.split("\\n").map((item) => item.trim()).filter(Boolean);
    }

    function showToast(message, type = "") {
      toast.textContent = message;
      toast.className = "toast " + type;
    }

    function proxyModeFromConfig(config) {
      if (config.proxy.mode) return config.proxy.mode;
      if (!config.proxy.enabled) return "off";
      return config.proxy.provider_managed_rotating_endpoint ? "provider_rotating" : "single";
    }

    function proxyLabel(mode) {
      const labels = {
        off: "Proxy off",
        local: "Local proxy",
        single: "Single proxy",
        provider_rotating: "Provider rotator",
        rotating_list: "Auto rotator"
      };
      return labels[mode] || "Proxy";
    }

    function updateProxyChip() {
      const mode = fields.proxyEnabled.checked ? fields.proxyMode.value : "off";
      proxyChip.textContent = proxyLabel(mode);
      proxyChip.classList.toggle("warn", mode === "off");
    }

    function setTheme(theme) {
      document.documentElement.dataset.theme = theme;
      localStorage.setItem("dvsa-theme", theme);
      document.querySelector("#dayMode").classList.toggle("active", theme !== "night");
      document.querySelector("#nightMode").classList.toggle("active", theme === "night");
    }

    function fillForm(config, source) {
      fields.startUrl.value = config.search.start_url || "";
      fields.dateFrom.value = config.search.preferred_date_from || "";
      fields.dateTo.value = config.search.preferred_date_to || "";
      fields.centres.value = (config.search.preferred_test_centres || []).join("\\n");
      fields.keywords.value = (config.search.preferred_keywords || []).join("\\n");
      fields.pollSeconds.value = config.search.poll_seconds ?? 180;
      fields.jitterSeconds.value = config.search.rate_limit_jitter_seconds ?? 20;
      fields.errorBackoffSeconds.value = config.search.error_backoff_seconds ?? 300;
      fields.rateLimitCooldownSeconds.value = config.search.rate_limit_cooldown_seconds ?? 3600;
      fields.maxChecks.value = config.search.max_checks ?? 0;
      fields.licenceNumber.value = config.candidate.driving_licence_number || "";
      fields.testReference.value = config.candidate.driving_test_reference || "";
      fields.theoryNumber.value = config.candidate.theory_test_pass_number || "";
      fields.proxyMode.value = proxyModeFromConfig(config);
      fields.localProxyServer.value = config.proxy.local_server || "http://127.0.0.1:8080";
      fields.proxyServer.value = config.proxy.server || "";
      fields.proxyServers.value = (config.proxy.servers || []).join("\\n");
      fields.proxyUsername.value = config.proxy.username || "";
      fields.proxyPassword.value = config.proxy.password || "";
      fields.rotationStrategy.value = config.proxy.rotation_strategy || "round_robin";
      fields.proxyEnabled.checked = fields.proxyMode.value !== "off" || Boolean(config.proxy.enabled);
      fields.rotatingProxy.checked = fields.proxyMode.value === "provider_rotating" || Boolean(config.proxy.provider_managed_rotating_endpoint);
      fields.autofill.checked = Boolean(config.candidate.autofill_known_fields);
      fields.refresh.checked = Boolean(config.search.refresh_between_checks);
      fields.serviceHours.checked = Boolean(config.search.service_hours_only);
      fields.clickStart.checked = Boolean(config.browser.click_start_now);
      configChip.textContent = source === "local" ? "Local config" : "Example config";
      updateProxyChip();
    }

    function collectForm() {
      const selectedProxyMode = fields.proxyEnabled.checked ? fields.proxyMode.value : "off";
      return {
        candidate: {
          driving_licence_number: fields.licenceNumber.value.trim(),
          driving_test_reference: fields.testReference.value.trim(),
          theory_test_pass_number: fields.theoryNumber.value.trim(),
          autofill_known_fields: fields.autofill.checked
        },
        search: {
          mode: "change-driving-test",
          start_url: fields.startUrl.value.trim(),
          preferred_test_centres: splitLines(fields.centres.value),
          preferred_keywords: splitLines(fields.keywords.value),
          preferred_date_from: fields.dateFrom.value,
          preferred_date_to: fields.dateTo.value,
          poll_seconds: Number(fields.pollSeconds.value || 180),
          rate_limit_jitter_seconds: Number(fields.jitterSeconds.value || 0),
          error_backoff_seconds: Number(fields.errorBackoffSeconds.value || 300),
          rate_limit_cooldown_seconds: Number(fields.rateLimitCooldownSeconds.value || 3600),
          max_checks: Number(fields.maxChecks.value || 0),
          refresh_between_checks: fields.refresh.checked,
          stop_before_final_confirmation: true,
          service_hours_only: fields.serviceHours.checked
        },
        proxy: {
          enabled: selectedProxyMode !== "off",
          mode: selectedProxyMode,
          server: fields.proxyServer.value.trim(),
          local_server: fields.localProxyServer.value.trim(),
          servers: splitLines(fields.proxyServers.value),
          username: fields.proxyUsername.value.trim(),
          password: fields.proxyPassword.value,
          rotation_strategy: fields.rotationStrategy.value,
          rotation_state_path: ".proxy-rotation-state.json",
          provider_managed_rotating_endpoint: selectedProxyMode === "provider_rotating" || fields.rotatingProxy.checked
        },
        browser: {
          headless: false,
          slow_mo_ms: 80,
          user_data_dir: ".browser-profile",
          click_start_now: fields.clickStart.checked,
          navigation_timeout_ms: 45000
        },
        logging: {
          process_log_path: "../Logs/process Log.md"
        }
      };
    }

    async function api(path, options = {}) {
      const response = await fetch(path, options);
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Request failed");
      return data;
    }

    async function loadConfig() {
      const data = await api("/api/config");
      fillForm(data.config, data.source);
      showToast("Settings loaded.", "ok");
    }

    async function saveConfig() {
      const data = await api("/api/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(collectForm())
      });
      fillForm(data.config, "local");
      showToast(data.message, "ok");
    }

    async function loadLogs() {
      const data = await api("/api/logs");
      logOutput.textContent = data[activeLog] || "";
    }

    async function launchAssistant() {
      document.querySelector("#launchBtn").disabled = true;
      try {
        const data = await api("/api/launch", { method: "POST" });
        processChip.textContent = data.running ? "Running" : "Started";
        showToast(data.message, "ok");
        await loadLogs();
      } finally {
        document.querySelector("#launchBtn").disabled = false;
      }
    }

    document.querySelector("#settingsForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      try { await saveConfig(); } catch (error) { showToast(error.message, "bad"); }
    });

    document.querySelector("#reloadBtn").addEventListener("click", async () => {
      try { await loadConfig(); } catch (error) { showToast(error.message, "bad"); }
    });

    document.querySelector("#logsBtn").addEventListener("click", async () => {
      try { await loadLogs(); showToast("Logs refreshed.", "ok"); } catch (error) { showToast(error.message, "bad"); }
    });

    document.querySelector("#launchBtn").addEventListener("click", async () => {
      try { await saveConfig(); await launchAssistant(); } catch (error) { showToast(error.message, "bad"); }
    });

    document.querySelector("#processTab").addEventListener("click", async () => {
      activeLog = "process";
      document.querySelector("#processTab").classList.add("active");
      document.querySelector("#devTab").classList.remove("active");
      await loadLogs();
    });

    document.querySelector("#devTab").addEventListener("click", async () => {
      activeLog = "development";
      document.querySelector("#devTab").classList.add("active");
      document.querySelector("#processTab").classList.remove("active");
      await loadLogs();
    });

    document.querySelector("#dayMode").addEventListener("click", () => setTheme("day"));
    document.querySelector("#nightMode").addEventListener("click", () => setTheme("night"));
    fields.proxyEnabled.addEventListener("change", () => {
      if (fields.proxyEnabled.checked && fields.proxyMode.value === "off") {
        fields.proxyMode.value = "local";
      }
      if (!fields.proxyEnabled.checked) {
        fields.proxyMode.value = "off";
      }
      updateProxyChip();
    });
    fields.proxyMode.addEventListener("change", () => {
      fields.proxyEnabled.checked = fields.proxyMode.value !== "off";
      fields.rotatingProxy.checked = fields.proxyMode.value === "provider_rotating";
      updateProxyChip();
    });

    setTheme(localStorage.getItem("dvsa-theme") || "day");
    loadConfig().then(loadLogs).catch((error) => showToast(error.message, "bad"));
  </script>
</body>
</html>
"""


def run_server(host: str, port: int, open_browser: bool) -> None:
    server = ThreadingHTTPServer((host, port), UiRequestHandler)
    url = f"http://{host}:{port}"
    print(f"DVSA Appointment Setter UI running at {url}")
    print("Press Ctrl+C to stop.")
    if open_browser:
        webbrowser.open(url)
    server.serve_forever()


class UiRequestHandler(BaseHTTPRequestHandler):
    server_version = "DVSAAppointmentSetterUI/0.1"

    def do_GET(self) -> None:
        if self.path in {"/", "/index.html"}:
            self._send_html(HTML)
            return
        if self.path == "/api/config":
            self._send_json(read_current_config())
            return
        if self.path == "/api/logs":
            self._send_json(read_logs())
            return
        if self.path == "/api/health":
            self._send_json({"ok": True, "running": assistant_is_running()})
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path == "/api/config":
            self._handle_save_config()
            return
        if self.path == "/api/launch":
            self._handle_launch()
            return
        self.send_error(HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _handle_save_config(self) -> None:
        try:
            payload = self._read_json_body()
            config_data = build_config_from_payload(payload)
            write_local_config(config_data)
            self._send_json(
                {
                    "message": "Settings saved to config.local.json.",
                    "config": config_data,
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _handle_launch(self) -> None:
        try:
            ensure_local_config()
            process = launch_assistant()
            already_running = process is None
            status = "already running" if already_running else "assistant started"
            MarkdownProcessLogger(PROCESS_LOG_PATH).append("ui launch", status)
            self._send_json(
                {
                    "message": (
                        "Assistant is already running."
                        if already_running
                        else "Assistant launched in a separate console."
                    ),
                    "running": assistant_is_running(),
                }
            )
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

    def _read_json_body(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        data = json.loads(raw_body or "{}")
        if not isinstance(data, dict):
            raise ValueError("Request body must be a JSON object")
        return data

    def _send_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_json(self, body: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
        encoded = json.dumps(body, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def read_current_config() -> dict[str, Any]:
    source_path = CONFIG_PATH if CONFIG_PATH.exists() else EXAMPLE_CONFIG_PATH
    if source_path.exists():
        with source_path.open("r", encoding="utf-8") as handle:
            raw_config = json.load(handle)
    else:
        raw_config = {}
    config = merge_dict(default_config(), raw_config)
    return {
        "source": "local" if source_path == CONFIG_PATH else "example",
        "config": config,
        "running": assistant_is_running(),
    }


def merge_dict(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def read_logs() -> dict[str, str]:
    return {
        "process": read_text_or_empty(PROCESS_LOG_PATH),
        "development": read_text_or_empty(DEVELOPMENT_LOG_PATH),
    }


def read_text_or_empty(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def build_config_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    candidate = get_dict(payload, "candidate")
    search = get_dict(payload, "search")
    proxy = get_dict(payload, "proxy")
    browser = get_dict(payload, "browser")

    config = default_config()
    config["candidate"].update(
        {
            "driving_licence_number": clean_string(
                candidate.get("driving_licence_number", "")
            ),
            "driving_test_reference": clean_string(
                candidate.get("driving_test_reference", "")
            ),
            "theory_test_pass_number": clean_string(
                candidate.get("theory_test_pass_number", "")
            ),
            "autofill_known_fields": bool(candidate.get("autofill_known_fields", False)),
        }
    )
    config["search"].update(
        {
            "mode": "change-driving-test",
            "start_url": clean_string(
                search.get("start_url", "https://www.gov.uk/change-driving-test")
            ),
            "preferred_test_centres": clean_string_list(
                search.get("preferred_test_centres", [])
            ),
            "preferred_keywords": clean_string_list(search.get("preferred_keywords", [])),
            "preferred_date_from": clean_string(search.get("preferred_date_from", "")),
            "preferred_date_to": clean_string(search.get("preferred_date_to", "")),
            "poll_seconds": int(search.get("poll_seconds", 180)),
            "rate_limit_jitter_seconds": int(
                search.get("rate_limit_jitter_seconds", 20)
            ),
            "error_backoff_seconds": int(search.get("error_backoff_seconds", 300)),
            "rate_limit_cooldown_seconds": int(
                search.get("rate_limit_cooldown_seconds", 3600)
            ),
            "max_checks": int(search.get("max_checks", 0)),
            "refresh_between_checks": bool(search.get("refresh_between_checks", True)),
            "stop_before_final_confirmation": True,
            "service_hours_only": bool(search.get("service_hours_only", True)),
        }
    )
    config["proxy"].update(
        {
            "enabled": bool(proxy.get("enabled", False)),
            "mode": clean_string(proxy.get("mode", "off")) or "off",
            "server": clean_string(proxy.get("server", "")),
            "local_server": clean_string(
                proxy.get("local_server", "http://127.0.0.1:8080")
            ),
            "servers": clean_string_list(proxy.get("servers", [])),
            "username": clean_string(proxy.get("username", "")),
            "password": str(proxy.get("password", "")),
            "rotation_strategy": clean_string(
                proxy.get("rotation_strategy", "round_robin")
            )
            or "round_robin",
            "rotation_state_path": ".proxy-rotation-state.json",
            "provider_managed_rotating_endpoint": bool(
                proxy.get("provider_managed_rotating_endpoint", True)
            ),
        }
    )
    config["browser"].update(
        {
            "headless": False,
            "slow_mo_ms": int(browser.get("slow_mo_ms", 80)),
            "user_data_dir": ".browser-profile",
            "click_start_now": bool(browser.get("click_start_now", True)),
            "navigation_timeout_ms": int(browser.get("navigation_timeout_ms", 45000)),
        }
    )
    config["logging"]["process_log_path"] = "../Logs/process Log.md"
    return config


def get_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key, {})
    if not isinstance(value, dict):
        raise ValueError(f"{key} must be an object")
    return value


def clean_string(value: Any) -> str:
    return str(value).strip()


def clean_string_list(value: Any) -> list[str]:
    if isinstance(value, str):
        value = value.splitlines()
    if not isinstance(value, list):
        raise ValueError("Expected a list of strings")
    return [clean_string(item) for item in value if clean_string(item)]


def write_local_config(config_data: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        suffix=".json",
        dir=CONFIG_PATH.parent,
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        json.dump(config_data, handle, indent=2)
        handle.write("\n")

    try:
        load_config(temp_path)
        temp_path.replace(CONFIG_PATH)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def ensure_local_config() -> None:
    if CONFIG_PATH.exists():
        load_config(CONFIG_PATH)
        return
    current = read_current_config()["config"]
    write_local_config(current)


def assistant_is_running() -> bool:
    return LAST_PROCESS is not None and LAST_PROCESS.poll() is None


def launch_assistant() -> subprocess.Popen[str] | None:
    global LAST_PROCESS
    if assistant_is_running():
        return None

    command = [
        sys.executable,
        "-m",
        "dvsa_appointment_setter.cli",
        "--config",
        str(CONFIG_PATH),
    ]
    kwargs: dict[str, Any] = {
        "cwd": str(CORE_ROOT),
        "text": True,
    }
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_CONSOLE
    else:
        kwargs["stdin"] = subprocess.DEVNULL
        kwargs["stdout"] = subprocess.DEVNULL
        kwargs["stderr"] = subprocess.DEVNULL
    LAST_PROCESS = subprocess.Popen(command, **kwargs)
    return LAST_PROCESS


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the DVSA Appointment Setter UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-open", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        run_server(args.host, args.port, open_browser=not args.no_open)
        return 0
    except KeyboardInterrupt:
        print("\nUI stopped.")
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
