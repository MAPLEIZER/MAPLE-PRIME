from __future__ import annotations

import json
import shutil
import sys
import urllib.error
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
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
    UpdateMode,
    fetch_alpha_release,
    load_install_state,
    load_preferences,
    save_install_state,
    save_preferences,
    update_available,
)

DASHBOARD_URL = "http://127.0.0.1:8080"
API_URL = "http://127.0.0.1:8000"
RELEASES_URL = "https://github.com/MAPLEIZER/kenya-data-rights/releases"

console = Console(theme=KDR_THEME)


@dataclass(frozen=True)
class CheckResult:
    check: SelfTestCheck
    ok: bool
    detail: str


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
        results.append(CheckResult(SelfTestCheck.API_INTERNAL, internal_ok, "internal API checks passed" if internal_ok else "internal API checks reported a failure"))
        checks = report.get("checks", {})
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
    completed = run(command, cwd=root, check=False)
    if completed.returncode != 0:
        console.print(completed.stderr.strip() or completed.stdout.strip(), style="kdr.danger")
        return False
    if completed.stdout.strip():
        console.print(completed.stdout.strip(), style="kdr.muted")
    return True


def _latest_release():
    try:
        return fetch_alpha_release()
    except Exception as exc:
        console.print(f"Could not check GitHub Releases: {exc}", style="kdr.muted")
        return None


def _install(root: Path, *, update: bool = False, exact_ref: str | None = None, release_tag: str | None = None) -> bool:
    if not _require_docker():
        return False
    release = None
    if exact_ref is None:
        release = _latest_release()
        exact_ref = release.source_sha if release is not None else SOURCE_REF
        release_tag = release.tag if release is not None else None
    label = "Updating" if update else "Installing"
    console.print(f"[kdr.accent]{label} Kenya Data Rights[/] in {root}")
    console.print(f"[kdr.muted]Source:[/] {exact_ref}")
    try:
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
    show_results(run_self_test(root))
    return True


def _check_update(root: Path, *, auto_install: bool = False) -> bool:
    release = _latest_release()
    if release is None:
        return False
    if not update_available(root, release):
        console.print("KDR application source is already on the newest tested alpha.", style="kdr.success")
        return False
    state = load_install_state(root)
    current = state.source_sha[:10] if state.source_sha else "older/untracked"
    console.print(Panel(f"Current source: {current}\nAvailable source: {release.source_sha[:10]}\n{release.html_url}", title="Update available", border_style="cyan"))
    if auto_install or Confirm.ask("Install this tested alpha now?", default=True, console=console):
        return _install(root, update=True, exact_ref=release.source_sha, release_tag=release.tag)
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
    body = (
        "[kdr.title]Kenya Data Rights[/]\n"
        f"Installer {__version__} · local-first alpha\n\n"
        f"Install location: [kdr.accent]{root}[/]\n"
        f"Installed source: [kdr.accent]{source}[/]\n"
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
    if release is None or not update_available(root, release):
        return
    if mode is UpdateMode.AUTO:
        _install(root, update=True, exact_ref=release.source_sha, release_tag=release.tag)
    elif Confirm.ask(f"A newer tested KDR alpha ({release.source_sha[:10]}) is available. Update now?", default=True, console=console):
        _install(root, update=True, exact_ref=release.source_sha, release_tag=release.tag)


def main() -> int:
    root = default_install_root()
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
                show_results(run_self_test(root))
        elif action is InstallAction.SELF_TEST:
            show_results(run_self_test(root))
        elif action is InstallAction.OPEN:
            webbrowser.open(DASHBOARD_URL)
        elif action is InstallAction.STATUS:
            _run_compose(action, root)
        elif action is InstallAction.REPAIR:
            if _require_docker() and _run_compose(action, root):
                show_results(run_self_test(root))
        elif action is InstallAction.STOP:
            _run_compose(action, root)
        elif action is InstallAction.UNINSTALL:
            _uninstall(root)

        console.print("\nPress Enter to return to the menu.", style="kdr.muted")
        input()


if __name__ == "__main__":
    sys.exit(main())
