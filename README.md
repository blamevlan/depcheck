# depcheck

Ever wondered what actually happens when you remove a package? Not just "it gets uninstalled" — but what else goes with it, what breaks, and whether it's safe?

`depcheck` runs the simulation for you and gives you a clear answer before you touch anything.

```
depcheck git curl spotify
```

## How it works

Give it one or more package names and it will:

- Check whether each package is actually installed (via dnf or Flatpak)
- Show which other installed packages depend on it
- Simulate the removal with `dnf remove --assumeno` and list everything that would be pulled along
- Warn you if anything critical would be affected — kernel, systemd, glibc, bash, and friends
- Give you a verdict: **SAFE**, **CAUTION**, or **DANGER**

Nothing is ever removed. Every check is completely read-only.

## Flatpak

Flatpak apps are detected automatically. Since they run in a sandbox with no ties to the system package tree, they're always safe to remove without side effects — depcheck will tell you that too.

> apt (Debian/Ubuntu) and pacman (Arch) are not supported yet.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/depcheck/main/install.sh | bash
```

Requires Python 3. The `rich` library is installed automatically if it's missing.

## Usage

```bash
depcheck <package> [package ...]
```

```bash
depcheck curl
depcheck git
depcheck git curl nginx
depcheck spotify
```

## Requirements

- Fedora or RHEL (uses `dnf`)
- Python 3
- [rich](https://github.com/Textualize/rich) — installed automatically
- `flatpak` — optional, only needed for Flatpak detection
