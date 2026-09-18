# depcheck

`depcheck` checks what would happen before you remove a package on a Fedora or RHEL system.

It runs the relevant package-manager checks and removal simulation, then shows what else depends on the package and what DNF would remove with it. Nothing is removed by depcheck itself.

```bash
depcheck git curl spotify
```

## What it checks

For each package, depcheck can:

- check whether it is installed through DNF or Flatpak
- show installed packages that depend on it
- run `dnf remove --assumeno` and parse the result
- flag removals that include critical system packages
- show a simple SAFE, CAUTION or DANGER result

Flatpak applications are handled separately because they are not part of the DNF dependency tree.

Debian/Ubuntu and Arch package managers are not supported yet.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/blamevlan/depcheck/main/install.sh | bash
```

The script needs Python 3. It installs `rich` if it is missing.

## Usage

```bash
depcheck <package> [package ...]
```

Examples:

```bash
depcheck curl
depcheck git curl nginx
depcheck spotify
```

## Requirements

- Fedora or RHEL
- Python 3
- [rich](https://github.com/Textualize/rich)
- Flatpak is optional and only needed for Flatpak detection

## License

MIT. See [LICENSE](LICENSE).
