# depcheck

> "What happens if I remove this package?"

`depcheck` answers that question safely on Fedora/RHEL systems — without touching anything.

```
depcheck git
depcheck spotify
```

## What it does

- Checks if the package is installed via **dnf** or **Flatpak**
- Shows which installed packages depend on it
- Simulates `dnf remove` and lists everything that would be pulled along
- Flags system-critical packages (kernel, systemd, glibc, bash, ...)
- Gives a clear risk level: **SAFE**, **CAUTION**, or **DANGER**

Nothing is ever removed. All checks are read-only.

## Flatpak support

Flatpak apps like Spotify, GIMP or Bottles are detected automatically.  
Since Flatpaks run in a sandbox and have no system-level dependencies, they are always **safe to remove** — no other packages depend on them.

> Note: apt (Debian/Ubuntu) and pacman (Arch) are not supported yet.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/depcheck/main/install.sh | bash
```

Requires Python 3. `rich` is installed automatically if missing (via dnf or pip).

## Usage

```bash
depcheck <package>
```

Examples:

```bash
depcheck curl
depcheck git
depcheck spotify
depcheck bash
```

## Requirements

- Fedora / RHEL (uses `dnf`)
- Python 3
- [rich](https://github.com/Textualize/rich) (auto-installed)
- `flatpak` (optional, for Flatpak detection)
