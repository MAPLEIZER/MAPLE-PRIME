from __future__ import annotations

import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, IntPrompt
from rich.table import Table

from kdr_installer import __version__
from kdr_installer.core import (
    SOURCE_REF,
    InstallAction,
    SelfTestCheck,
    command_available,
    compose_command,
    default_install_root,
    has_installation,
    install_source,
    installer_menu,
    run,
)
from kdr_installer.pairing import generate_pairing_token, tailscale_serve_args, write_runtime_env
from kdr_installer.theme import KDR_THEME
from kdr_installer.updates import (
    InstallState,
    InstallerPreferences,
    ReleaseInfo,
    UpdateMode,
    download_installer_asset,
    fetch_alpha_release,
    fetch_release_checksums,
    load_install_state,
    load_preferences,
    managed_installer_path,
    resolve_installer_asset,
    save_install_state,
    save_preferences,
    sha256_file,
    update_available,
)

DASHBOARD_URL = "http://127.0.0.1:8080"
API_URL = "http://127.0.0.1:8000"
RELEASES_URL = "https://github.com/MAPLEIZER/kenya-data-rights/releases"
ODPC_REGISTRY_URL = "https://www.odpc.go.ke/registered-data-handlers/"
BACKGROUND_SERVICES = frozenset({"api", "web"})

console = Console(theme=KDR_THEME)


@dataclass(frozen=True)
class CheckResult:
    check: SelfTestCheck
    ok: bool
    detail: str


@dataclass(frozen=True)
class LocalApiResult:
    ok: bool
    code: str
    message: str
    payload: dict[str, object]


@contextmanager
def _activity(label: str) -> Iterator[None]:
    started = time.monotonic()
    try:
        with Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[kdr.accent]{task.description}"),
            TimeElapsedColumn(),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task(label, total=None)
            yield
    except Exception:
        elapsed = time.monotonic() - started
        console.print(f"[kdr.danger]✗[/] {label} [kdr.muted]({elapsed:.1f}s)[/]")
        raise
    else:
        elapsed = time.monotonic() - started
        console.print(f"[kdr.success]✓[/] {label} [kdr.muted]({elapsed:.1f}s)[/]")


def _http_json(url: str) -> dict[str, object]:
    request = urllib.request.Request(url, headers={"User-Agent": f"KDR-Installer/{__version__}"})
    with urllib.request.urlopen(request, timeout=8) as response:
        if response.status != 200:
            raise OSError(f"HTTP {response.status}")
        return json.loads(response.read().decode("utf-8"))


def _http_ok(url: str) -> bool:
    request = urllib.request.Request(url, headers={"User-Agent": f"KDR-Installer/{__version__}"})
    with urllib.request.urlopen(request, timeout=8) as response:
        return response.status == 200


def _post_local_api(path: str, *, action: str) -> LocalApiResult:
    request = urllib.request.Request(
        f"{DASHBOARD_URL}{path}",
        data=b"",
        method="POST",
        headers={
            "User-Agent": f"KDR-Installer/{__version__}",
            "X-KDR-Local-Action": action,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return LocalApiResult(True, "ok", "completed", payload if isinstance(payload, dict) else {})
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = {}
        detail = payload.get("detail") if isinstance(payload, dict) else None
        if isinstance(detail, dict):
            code = str(detail.get("code") or "request_failed")
            message = str(detail.get("message") or f"Request failed with HTTP {exc.code}.")
        else:
            code = "request_failed"
            message = str(detail) if isinstance(detail, str) else f"Request failed with HTTP {exc.code}."
        return LocalApiResult(False, code, message, {})
    except (OSError, urllib.error.URLError) as exc:
        return LocalApiResult(False, "local_api_unreachable", f"Local KDR API is unreachable: {exc}", {})


def _docker_preflight() -> list[CheckResult]:
    results: list[CheckResult] = []
    docker_present = command_available("docker")
    results.append(CheckResult(SelfTestCheck.DOCKER_CLI, docker_present, "Docker CLI found" if docker_present else "Docker CLI not found"))
    if not docker_present:
        results.extend(
            [
                CheckResult(SelfTestCheck.DOCKER_DAEMON, False, "cannot check daemon without Docker CLI"),
                CheckResult(SelfTestCheck.COMPOSE, False, "cannot check Compose without Docker CLI"),
            ]
        )
        return results

    daemon = run(["docker", "info"], check=False)
    results.append(CheckResult(SelfTestCheck.DOCKER_DAEMON, daemon.returncode == 0, "Docker daemon reachable" if daemon.returncode == 0 else "Docker daemon is not reachable"))
    compose = run(["docker", "compose", "version"], check=False)
    results.append(CheckResult(SelfTestCheck.COMPOSE, compose.returncode == 0, "Docker Compose v2 available" if compose.returncode == 0 else "Docker Compose v2 unavailable"))
    return results


def _service_summary(root: Path) -> str:
    if not has_installation(root):
        return "[kdr.muted]not installed[/]"
    if not command_available("docker"):
        return "[kdr.warning]Docker unavailable[/]"
    command = [*compose_command(InstallAction.STATUS, root), "--all", "--format", "json"]
    completed = run(command, cwd=root, check=False)
    if completed.returncode != 0:
        return "[kdr.warning]status unavailable[/]"
    raw = completed.stdout.strip()
    if not raw:
        return f"[kdr.danger]0/{len(BACKGROUND_SERVICES)} running[/]"
    try:
        parsed = json.loads(raw)
        rows = parsed if isinstance(parsed, list) else [parsed]
    except json.JSONDecodeError:
        rows = []
        for line in raw.splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict):
                rows.append(item)

    persistent_rows = {
        str(item.get("Service", "")): item
        for item in rows
        if isinstance(item, dict) and str(item.get("Service", "")) in BACKGROUND_SERVICES
    }
    running = sum(
        str(persistent_rows.get(service, {}).get("State", "")).lower() == "running"
        for service in BACKGROUND_SERVICES
    )
    total = len(BACKGROUND_SERVICES)
    if running == total:
        return f"[kdr.success]{running}/{total} running[/]"
    if running:
        return f"[kdr.warning]{running}/{total} running[/]"
    return f"[kdr.danger]0/{total} running[/]"


def run_self_test(install_root: Path) -> list[CheckResult]:
    results = _docker_preflight()
    if not has_installation(install_root):
        detail = f"KDR source not installed at {install_root}"
        for check in [SelfTestCheck.API_DIRECT, SelfTestCheck.WEB, SelfTestCheck.API_PROXY, SelfTestCheck.API_INTERNAL, SelfTestCheck.PERSISTENCE]:
            results.append(CheckResult(check, False, detail))
        return results

    endpoints = [
        (SelfTestCheck.API_DIRECT, f"{API_URL}/api/v1/health", "direct API health"),
        (SelfTestCheck.WEB, f"{DASHBOARD_URL}/", "dashboard root"),
        (SelfTestCheck.API_PROXY, f"{DASHBOARD_URL}/api/v1/health", "nginx API proxy"),
    ]
    for check, url, label in endpoints:
        try:
            ok = _http_ok(url)
            results.append(CheckResult(check, ok, f"{label} reachable" if ok else f"{label} returned an unexpected response"))
        except (OSError, urllib.error.URLError):
            results.append(CheckResult(check, False, f"{label} unreachable"))

    try:
        report = _http_json(f"{DASHBOARD_URL}/api/v1/system/self-test")
        internal_ok = bool(report.get("ok"))
        checks = report.get("checks", {})
        internal_detail = "internal API checks passed"
        if not internal_ok and isinstance(checks, dict):
            failed = []
            for name, item in checks.items():
                if isinstance(item, dict) and not item.get("ok"):
                    failed.append(f"{name}: {item.get('detail', 'failed')}")
            internal_detail = "; ".join(failed) if failed else "internal API checks reported a failure"
        results.append(CheckResult(SelfTestCheck.API_INTERNAL, internal_ok, internal_detail))
        persistence_ok = bool(isinstance(checks, dict) and checks.get("database", {}).get("ok") and checks.get("snapshot_storage", {}).get("ok"))
        results.append(CheckResult(SelfTestCheck.PERSISTENCE, persistence_ok, "database and snapshot storage writable" if persistence_ok else "persistence check failed"))
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        results.append(CheckResult(SelfTestCheck.API_INTERNAL, False, "internal API self-test unavailable"))
        results.append(CheckResult(SelfTestCheck.PERSISTENCE, False, "persistence could not be verified"))
    return results


def show_results(results: list[CheckResult]) -> bool:
    table = Table(title="KDR self-test", show_lines=False)
    table.add_column("Check")
    table.add_column("Result")
    table.add_column("Detail")
    for result in results:
        state = "[kdr.success]PASS[/]" if result.ok else "[kdr.danger]FAIL[/]"
        table.add_row(result.check.value.replace("_", " ").title(), state, result.detail)
    console.print(table)
    ok = all(item.ok for item in results)
    console.print("[kdr.success]System is ready for hands-on testing.[/]" if ok else "[kdr.warning]One or more checks need attention.[/]")
    return ok


def _require_docker() -> bool:
    with _activity("Checking Docker and Compose"):
        results = _docker_preflight()
    show_results(results)
    if not all(item.ok for item in results):
        console.print("\nInstall/start Docker Desktop or Docker Engine with Compose v2, then rerun this installer.", style="kdr.warning")
        return False
    return True


def _run_compose(action: InstallAction, root: Path, *, purge_data: bool = False) -> bool:
    if not has_installation(root):
        console.print(f"No KDR installation found at {root}", style="kdr.warning")
        return False
    command = compose_command(action, root, purge_data=purge_data)
    console.print(f"[kdr.muted]Running:[/] {' '.join(command)}")
    label = {
        InstallAction.INSTALL: "Building and starting KDR containers",
        InstallAction.START: "Starting KDR containers",
        InstallAction.UPDATE: "Rebuilding KDR with the tested update",
        InstallAction.REPAIR: "Repairing and rebuilding KDR containers",
        InstallAction.STOP: "Stopping KDR containers",
        InstallAction.UNINSTALL: "Removing KDR containers",
        InstallAction.STATUS: "Reading Docker service status",
    }.get(action, "Running Docker Compose")
    with _activity(label):
        completed = run(command, cwd=root, check=False)
    if completed.returncode != 0:
        console.print(completed.stderr.strip() or completed.stdout.strip(), style="kdr.danger")
        return False
    if completed.stdout.strip():
        console.print(completed.stdout.strip(), style="kdr.muted")
    return True


def _latest_release() -> ReleaseInfo | None:
    try:
        with _activity("Checking GitHub Releases for the newest tested alpha"):
            return fetch_alpha_release()
    except Exception as exc:
        console.print(f"Could not check GitHub Releases: {exc}", style="kdr.muted")
        return None


def _current_executable() -> Path | None:
    if not getattr(sys, "frozen", False):
        return None
    try:
        return Path(sys.executable).resolve()
    except OSError:
        return Path(sys.executable)


def _prepare_installer_handoff(root: Path, release: ReleaseInfo) -> Path | None:
    with _activity("Checking and verifying the installer executable"):
        checksums = fetch_release_checksums(release)
        asset = resolve_installer_asset(release, checksums)
        current = _current_executable()
        if current is not None and current.is_file():
            try:
                if sha256_file(current) == asset.sha256:
                    return None
            except OSError:
                pass

        destination = managed_installer_path(root)
        if os.name == "nt" and current is not None:
            try:
                if destination.resolve() == current.resolve():
                    destination = destination.with_name("kdr-installer-next.exe")
            except OSError:
                destination = destination.with_name("kdr-installer-next.exe")

        if destination.is_file():
            try:
                if sha256_file(destination) == asset.sha256:
                    return destination if current is not None else None
            except OSError:
                pass
        download_installer_asset(asset, destination)
        return destination if current is not None else None


def _restart_into_installer(path: Path) -> None:
    console.print(
        Panel(
            f"Application update complete. Restarting into the verified installer at:\n{kdr_path(path)}",
            title="Installer update",
            border_style="cyan",
        )
    )
    try:
        path.chmod(0o700)
    except OSError:
        pass
    os.execv(str(path), [str(path)])


def kdr_path(path: Path) -> str:
    return str(path)


def _refresh_installer_after_update(root: Path, release: ReleaseInfo | None) -> None:
    if release is None:
        return
    try:
        handoff = _prepare_installer_handoff(root, release)
    except Exception as exc:
        console.print(
            f"Application updated, but the installer executable could not refresh automatically: {exc}",
            style="kdr.warning",
        )
        return
    if handoff is not None:
        _restart_into_installer(handoff)


def _install(
    root: Path,
    *,
    update: bool = False,
    exact_ref: str | None = None,
    release_tag: str | None = None,
    release: ReleaseInfo | None = None,
) -> bool:
    if not _require_docker():
        return False
    if exact_ref is None:
        release = release or _latest_release()
        exact_ref = release.source_sha if release is not None else SOURCE_REF
        release_tag = release.tag if release is not None else None
    label = "Updating" if update else "Installing"
    console.print(f"[kdr.accent]{label} Kenya Data Rights[/] in {root}")
    console.print(f"[kdr.muted]Source:[/] {exact_ref}")
    try:
        with _activity("Downloading, verifying and staging KDR source"):
            install_source(root, ref=exact_ref)
    except Exception as exc:
        console.print(f"Source download/install failed: {exc}", style="kdr.danger")
        return False
    action = InstallAction.UPDATE if update else InstallAction.INSTALL
    if not _run_compose(action, root):
        return False
    save_install_state(
        root,
        InstallState(
            source_sha=exact_ref if len(exact_ref) == 40 else None,
            release_tag=release_tag,
            installed_version=__version__,
        ),
    )
    console.print("KDR started successfully.", style="kdr.success")
    with _activity("Running post-install self-test"):
        results = run_self_test(root)
    show_results(results)
    _refresh_installer_after_update(root, release)
    return True


def _sync_regulator_sources(root: Path) -> None:
    if not has_installation(root):
        console.print("Install KDR first.", style="kdr.warning")
        return
    try:
        if not _http_ok(f"{DASHBOARD_URL}/api/v1/health"):
            raise OSError("health endpoint returned an unexpected response")
    except (OSError, urllib.error.URLError):
        console.print("KDR is not reachable. Start or repair the local stack first.", style="kdr.warning")
        return

    successful: list[str] = []
    stages = [
        ("CBK", "/api/v1/sources/cbk_dcp/sync"),
        ("ODPC", "/api/v1/sources/odpc_registered/sync"),
    ]
    for label, path in stages:
        with _activity(f"Syncing {label} official source"):
            result = _post_local_api(path, action="sync")
        if result.ok:
            count = result.payload.get("record_count", "?")
            console.print(f"[kdr.success]{label} synced:[/] {count} records")
            successful.append(label)
        else:
            console.print(f"[kdr.danger]{label} sync failed[/] [{result.code}]: {result.message}")
            if label == "ODPC" and result.code == "source_access_restricted":
                console.print(
                    "KDR will not bypass ODPC site protections. The successful CBK snapshot remains saved, and reconciliation is skipped until ODPC can be synced legitimately.",
                    style="kdr.warning",
                )
                if Confirm.ask("Open the official ODPC registry in your browser?", default=False, console=console):
                    webbrowser.open(ODPC_REGISTRY_URL)

    if len(successful) == 2:
        with _activity("Reconciling CBK against the ODPC snapshot"):
            result = _post_local_api("/api/v1/reconciliation/cbk-odpc/run", action="reconcile")
        if result.ok:
            console.print(
                f"[kdr.success]Reconciliation complete:[/] {result.payload.get('finding_count', '?')} findings prepared for review"
            )
        else:
            console.print(f"[kdr.danger]Reconciliation failed[/] [{result.code}]: {result.message}")
    else:
        console.print("Reconciliation skipped because both current source snapshots are required.", style="kdr.warning")


def _check_update(root: Path, *, auto_install: bool = False) -> bool:
    release = _latest_release()
    if release is None:
        return False
    if not update_available(root, release):
        console.print("KDR application source is already on the newest tested alpha.", style="kdr.success")
        _refresh_installer_after_update(root, release)
        return False
    state = load_install_state(root)
    current = state.source_sha[:10] if state.source_sha else "older/untracked"
    console.print(Panel(f"Current source: {current}\nAvailable source: {release.source_sha[:10]}\n{release.html_url}", title="Update available", border_style="cyan"))
    if auto_install or Confirm.ask("Install this tested alpha now?", default=True, console=console):
        return _install(
            root,
            update=True,
            exact_ref=release.source_sha,
            release_tag=release.tag,
            release=release,
        )
    return False


def _configure_updates(root: Path) -> None:
    current = load_preferences(root)
    console.print(f"Current update mode: [kdr.accent]{current.update_mode.value}[/]")
    options = [(UpdateMode.PROMPT, "Prompt when a tested update is available"), (UpdateMode.AUTO, "Automatically install tested application updates when the installer starts"), (UpdateMode.MANUAL, "Only check when I choose Check / install update")]
    for index, (_, label) in enumerate(options, 1):
        console.print(f"[kdr.accent]{index}[/] {label}")
    choice = IntPrompt.ask("Choose update behavior", choices=["1", "2", "3"], console=console)
    selected = options[choice - 1][0]
    save_preferences(root, InstallerPreferences(update_mode=selected))
    console.print(f"Update mode saved: {selected.value}", style="kdr.success")


def _pair_android(root: Path) -> None:
    if not has_installation(root):
        console.print("Install KDR first.", style="kdr.warning")
        return
    if not _require_docker():
        return
    token = generate_pairing_token()
    write_runtime_env(root, token=token, telemetry_enabled=True)
    if not _run_compose(InstallAction.REPAIR, root):
        return

    server_url = "<your HTTPS URL pointing to 127.0.0.1:8080>"
    if command_available("tailscale") and Confirm.ask("Publish KDR to your tailnet over Tailscale HTTPS?", default=True, console=console):
        with _activity("Configuring Tailscale HTTPS mobile endpoint"):
            served = run(tailscale_serve_args(), check=False)
        if served.returncode == 0:
            status_result = run(["tailscale", "status", "--json"], check=False)
            if status_result.returncode == 0:
                try:
                    dns_name = str(json.loads(status_result.stdout).get("Self", {}).get("DNSName", "")).rstrip(".")
                    if dns_name:
                        server_url = f"https://{dns_name}"
                except json.JSONDecodeError:
                    pass
        else:
            console.print("Tailscale Serve could not be configured automatically.", style="kdr.warning")

    console.print(
        Panel(
            f"Server URL: [kdr.accent]{server_url}[/]\n"
            f"Pairing token: [kdr.accent]{token}[/]\n\n"
            "Enter these values in the Android app. The token enables derived-feature telemetry only; raw SMS text is not accepted by the API schema. Rotate this token by running Pair Android again.",
            title="Android pairing",
            border_style="cyan",
        )
    )


def _uninstall(root: Path) -> None:
    purge = Confirm.ask("Also delete the persistent KDR Docker data volume?", default=False, console=console)
    if purge and not Confirm.ask("This permanently deletes local KDR database and snapshots. Continue?", default=False, console=console):
        purge = False
    _run_compose(InstallAction.UNINSTALL, root, purge_data=purge)
    if root.exists() and Confirm.ask("Remove downloaded KDR application files too?", default=True, console=console):
        shutil.rmtree(root)
        console.print("Application files removed.", style="kdr.success")
    if not purge:
        console.print("Persistent Docker data was preserved.", style="kdr.accent")


def _banner(root: Path) -> None:
    preferences = load_preferences(root)
    state = load_install_state(root)
    source = state.source_sha[:10] if state.source_sha else "not installed / untracked"
    services = _service_summary(root)
    body = (
        "[kdr.title]Kenya Data Rights[/]\n"
        f"Installer {__version__} · local-first alpha\n\n"
        f"Install location: [kdr.accent]{root}[/]\n"
        f"Installed source: [kdr.accent]{source}[/]\n"
        f"Services: {services}\n"
        f"Updates: [kdr.accent]{preferences.update_mode.value}[/]\n"
        "Dashboard: [kdr.accent]http://127.0.0.1:8080[/]\n"
        "Telemetry off by default · localhost-only defaults"
    )
    console.print(Panel(body, border_style="cyan", title="KDR", subtitle="Privacy-first self-hosting"))


def _startup_update_check(root: Path) -> None:
    if not has_installation(root):
        return
    mode = load_preferences(root).update_mode
    if mode is UpdateMode.MANUAL:
        return
    release = _latest_release()
    if release is None:
        return
    if not update_available(root, release):
        if mode is UpdateMode.AUTO:
            _refresh_installer_after_update(root, release)
        return
    if mode is UpdateMode.AUTO:
        _install(
            root,
            update=True,
            exact_ref=release.source_sha,
            release_tag=release.tag,
            release=release,
        )
    elif Confirm.ask(f"A newer tested KDR alpha ({release.source_sha[:10]}) is available. Update now?", default=True, console=console):
        _install(
            root,
            update=True,
            exact_ref=release.source_sha,
            release_tag=release.tag,
            release=release,
        )


def _record_running_installer_version(root: Path) -> None:
    if not has_installation(root):
        return
    state = load_install_state(root)
    if state.installed_version == __version__:
        return
    save_install_state(
        root,
        InstallState(
            source_sha=state.source_sha,
            release_tag=state.release_tag,
            installed_version=__version__,
        ),
    )


def main() -> int:
    root = default_install_root()
    _record_running_installer_version(root)
    _startup_update_check(root)
    while True:
        console.clear()
        _banner(root)
        menu = installer_menu()
        table = Table(show_header=False, box=None, padding=(0, 1))
        for index, item in enumerate(menu, start=1):
            table.add_row(f"[kdr.accent]{index}[/]", f"[bold]{item.label}[/]", f"[kdr.muted]{item.description}[/]")
        console.print(table)
        choice = IntPrompt.ask("Choose an option", choices=[str(i) for i in range(1, len(menu) + 1)], console=console)
        action = menu[choice - 1].action

        if action is InstallAction.QUIT:
            return 0
        if action is InstallAction.INSTALL:
            _install(root)
        elif action is InstallAction.UPDATE:
            _check_update(root)
        elif action is InstallAction.UPDATE_SETTINGS:
            _configure_updates(root)
        elif action is InstallAction.PAIR_ANDROID:
            _pair_android(root)
        elif action is InstallAction.RELEASES:
            webbrowser.open(RELEASES_URL)
        elif action is InstallAction.START:
            if _require_docker() and _run_compose(action, root):
                with _activity("Running startup self-test"):
                    results = run_self_test(root)
                show_results(results)
        elif action is InstallAction.SELF_TEST:
            with _activity("Running KDR self-test"):
                results = run_self_test(root)
            show_results(results)
        elif action is InstallAction.SYNC_SOURCES:
            _sync_regulator_sources(root)
        elif action is InstallAction.OPEN:
            webbrowser.open(DASHBOARD_URL)
        elif action is InstallAction.STATUS:
            _run_compose(action, root)
        elif action is InstallAction.REPAIR:
            if _require_docker() and _run_compose(action, root):
                with _activity("Running post-repair self-test"):
                    results = run_self_test(root)
                show_results(results)
        elif action is InstallAction.STOP:
            _run_compose(action, root)
        elif action is InstallAction.UNINSTALL:
            _uninstall(root)

        console.print("\nPress Enter to return to the menu.", style="kdr.muted")
        input()


if __name__ == "__main__":
    sys.exit(main())
