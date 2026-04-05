# depcheck

> "What happens if I remove this package?"

`depcheck` answers that question safely on Fedora/RHEL systems — without touching anything.

```
depcheck git
```

![risk levels: SAFE · CAUTION · DANGER]

## What it does

- Checks if the package is installed
- Shows which installed packages depend on it
- Simulates `dnf remove` and lists everything that would be pulled along
- Flags system-critical packages (kernel, systemd, glibc, bash, ...)
- Gives a clear risk level: **SAFE**, **CAUTION**, or **DANGER**

Nothing is ever removed. All checks are read-only.

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
depcheck nginx
```

## Requirements

- Fedora / RHEL (uses `dnf`)
- Python 3
- [rich](https://github.com/Textualize/rich) (auto-installed)
