#!/usr/bin/env python3
# depcheck — "What happens if I remove this package?"
# github.com/blamevlan

import argparse
import subprocess
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.tree import Tree
from rich import box

console = Console()

CRITICAL = {
    "systemd", "systemd-libs", "kernel", "kernel-core",
    "glibc", "glibc-common", "bash", "dnf5", "dnf",
    "rpm", "rpm-libs", "python3", "python3-libs",
    "coreutils", "shadow-utils", "pam", "openssl-libs",
    "libselinux", "dbus", "NetworkManager",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def run(cmd, env_lang_c=False):
    env = None
    if env_lang_c:
        import os
        env = os.environ.copy()
        env["LANG"] = "C"
        env["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )
        return result.returncode, result.stdout, result.stderr
    except FileNotFoundError:
        console.print("[bold red]Error:[/] dnf not found — is this a Fedora/RHEL system?")
        sys.exit(1)


def strip_epoch_arch(pkg):
    """'curl-0:8.11.1-1.fc43.x86_64' → 'curl'"""
    name = pkg.split(":")[0] if ":" in pkg else pkg
    name = name.split("-")[0] if "-" in name else name
    return name


def pkg_name_only(full):
    """Remove epoch, version, release, arch from full NEVRA."""
    # format: name-0:ver-rel.arch
    parts = full.split("-")
    # drop epoch from second part if present
    name_parts = []
    for p in parts:
        if ":" in p:
            break
        name_parts.append(p)
    return "-".join(name_parts) if name_parts else full.split("-")[0]

# ── Flatpak ───────────────────────────────────────────────────────────────────

def flatpak_available():
    try:
        subprocess.run(["flatpak", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False


def check_flatpak(package):
    """Return flatpak info dict or None if not installed as flatpak."""
    code, out, _ = run(["flatpak", "list", "--columns=name,application,version,origin"])
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            name, app_id = parts[0].strip(), parts[1].strip()
            if package.lower() in name.lower() or package.lower() in app_id.lower():
                version = parts[2].strip() if len(parts) > 2 else "unknown"
                origin  = parts[3].strip() if len(parts) > 3 else "unknown"
                return {"name": name, "app_id": app_id, "version": version, "origin": origin}
    return None


def simulate_flatpak_removal(app_id):
    """Returns list of refs that would be removed."""
    code, out, err = run(["flatpak", "remove", "--dry-run", "--noninteractive", app_id])
    combined = out + err
    would_remove = []
    for line in combined.splitlines():
        stripped = line.strip()
        if stripped.startswith("flatpak") or not stripped:
            continue
        if any(kw in stripped.lower() for kw in ("uninstall:", "remove")):
            continue
        parts = stripped.split()
        if parts and "/" in parts[0]:
            would_remove.append(parts[0])
    return would_remove


def print_flatpak_result(info, package):
    console.print(f"  [green]✓[/] [bold]{info['name']}[/] is installed as a [bold cyan]Flatpak[/].\n")
    console.print(f"    App ID:  [dim]{info['app_id']}[/]")
    console.print(f"    Version: [dim]{info['version']}[/]")
    console.print(f"    Origin:  [dim]{info['origin']}[/]")
    console.print()
    console.print("  [bold]Simulating removal...[/]")
    would_remove = simulate_flatpak_removal(info["app_id"])
    if would_remove:
        table = Table(
            title="flatpak refs that would be removed",
            box=box.SIMPLE,
            title_style="bold",
            show_header=False,
        )
        table.add_column("Ref", style="white")
        for ref in would_remove:
            table.add_row(ref)
        console.print(table)
    else:
        console.print(f"  [green]✓[/] Only [cyan]{info['app_id']}[/] would be removed.\n")
    console.print()
    console.print(Panel(
        f"[green]Safe to remove.[/] Flatpaks are sandboxed and isolated — "
        f"removing [cyan]{info['name']}[/] will not affect system packages.",
        border_style="green",
    ))
    console.print()

# ── Core checks ───────────────────────────────────────────────────────────────

def check_installed(package):
    code, out, _ = run(["dnf", "repoquery", "--installed", package])
    return bool(out.strip())


def get_reverse_deps(package):
    """Packages currently installed that require this package."""
    code, out, _ = run(["dnf", "repoquery", "--installed", "--whatrequires", package])
    lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
    return lines


def simulate_removal(package):
    """
    Run dnf remove --assumeno with LANG=C so output is English and parsable.
    Returns (would_remove: list[str], error_lines: list[str])

    dnf5 output format:
      Removing:
       git   x86_64   2.53.0-1.fc43   ...
      Removing unused dependencies:
       perl-Git   ...
      Transaction Summary:
       ...
    """
    code, out, err = run(["dnf", "remove", "--assumeno", package], env_lang_c=True)
    combined = out + err

    would_remove = []
    errors = []

    in_pkg_block = False
    for line in combined.splitlines():
        stripped = line.strip()

        # Section headers that introduce package lists
        if stripped.lower().startswith("removing"):
            in_pkg_block = True
            continue

        # Stop at summary or empty-ish structural lines
        if in_pkg_block:
            if stripped == "" or stripped.lower().startswith("transaction"):
                in_pkg_block = False
                continue
            # Lines start with a space in raw output — first word is package name
            parts = stripped.split()
            if parts and not stripped.startswith("-"):
                would_remove.append(parts[0])

        # Collect problem/error lines (from stderr / resolution failures)
        if any(kw in stripped for kw in ("Problem:", "- installed", "conflicting")):
            errors.append(stripped)

    return would_remove, errors


def risk_level(reverse_deps, would_remove, sim_errors):
    names = set()
    for r in reverse_deps:
        names.add(pkg_name_only(r))
    for r in would_remove:
        names.add(r.split()[0])

    if names & CRITICAL or sim_errors:
        return "danger"
    if reverse_deps or would_remove:
        return "caution"
    return "safe"

# ── Output ────────────────────────────────────────────────────────────────────

RISK_STYLE = {
    "safe":    ("[bold green] SAFE [/]",    "green"),
    "caution": ("[bold yellow] CAUTION [/]","yellow"),
    "danger":  ("[bold red] DANGER [/]",    "red"),
}

def print_header(package):
    console.print()
    console.print(Panel(
        f"[bold]depcheck[/]  [dim]github.com/blamevlan[/]\n"
        f"Analysing: [bold cyan]{package}[/]",
        border_style="blue",
        padding=(0, 2),
    ))
    console.print()


def print_risk(level):
    badge, color = RISK_STYLE[level]
    console.print(f"  Risk level:  {badge}")
    console.print()


MAX_SHOW = 12

def print_reverse_deps(deps, package):
    if not deps:
        console.print("  [green]✓[/] No installed packages depend on this.")
        console.print()
        return

    shown   = deps[:MAX_SHOW]
    hidden  = len(deps) - len(shown)

    tree = Tree(f"[bold]Installed packages that require [cyan]{package}[/][/]")
    for d in shown:
        name = pkg_name_only(d)
        style = "red bold" if name in CRITICAL else "yellow"
        tree.add(f"[{style}]{name}[/]  [dim]{d}[/]")
    if hidden:
        tree.add(f"[dim]... and {hidden} more[/]")
    console.print("  ", tree)
    console.print()


def print_simulation(would_remove, sim_errors, package):
    if sim_errors and not would_remove:
        console.print("  [red]✗[/] Dependency resolution failed — removing this package")
        console.print("    would break the system:\n")
        for e in sim_errors[:8]:
            console.print(f"    [dim]{e}[/]")
        console.print()
        return

    if not would_remove:
        console.print("  [green]✓[/] dnf simulation: only this package would be removed.")
        console.print()
        return

    table = Table(
        title=f"dnf simulation — packages that would be removed",
        box=box.SIMPLE,
        title_style="bold",
        show_header=True,
        header_style="dim",
    )
    table.add_column("Package", style="white")
    table.add_column("Note", style="dim")

    for pkg in would_remove:
        note = "[bold red]CRITICAL[/]" if pkg in CRITICAL else ""
        table.add_row(pkg, note)

    console.print(table)
    console.print()


def print_verdict(level, package):
    if level == "safe":
        console.print(Panel(
            f"[green]Safe to remove.[/] No installed packages depend on [cyan]{package}[/] "
            f"and dnf reports no collateral removals.",
            border_style="green",
        ))
    elif level == "caution":
        console.print(Panel(
            f"[yellow]Proceed with caution.[/] Other packages depend on [cyan]{package}[/] "
            f"and will also be removed. Review the list above before continuing.",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            f"[bold red]Do not remove.[/] Removing [cyan]{package}[/] would affect "
            f"critical system packages. This could break your system.",
            border_style="red",
        ))
    console.print()

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        prog="depcheck",
        description='Answer "What happens if I remove this package?" safely.',
    )
    parser.add_argument("package", help="Package name to check (e.g. nginx, curl)")
    args = parser.parse_args()
    package = args.package

    print_header(package)

    # 1. Check installed (DNF first, then Flatpak)
    if not check_installed(package):
        if flatpak_available():
            flatpak_info = check_flatpak(package)
            if flatpak_info:
                print_flatpak_result(flatpak_info, package)
                sys.exit(0)
        console.print(f"  [red]✗[/] [bold]{package}[/] is not installed. Nothing to check.\n")
        sys.exit(0)

    console.print(f"  [green]✓[/] [bold]{package}[/] is installed.\n")

    # 2. Reverse dependencies
    console.print("  [bold]Checking reverse dependencies...[/]")
    rdeps = get_reverse_deps(package)
    print_reverse_deps(rdeps, package)

    # 3. Simulate removal
    console.print("  [bold]Simulating removal...[/]")
    would_remove, sim_errors = simulate_removal(package)
    print_simulation(would_remove, sim_errors, package)

    # 4. Risk + verdict
    level = risk_level(rdeps, would_remove, sim_errors)
    print_risk(level)
    print_verdict(level, package)


if __name__ == "__main__":
    main()
