# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## Usage

This repo can be used as a custom PKGBUILD repository in paru, so packages here can be installed and upgraded without publishing them to the AUR.

Add this to `~/.config/paru/paru.conf`:

```ini
[arch-pkgs]
Url = https://github.com/joshuadavidthomas/arch-pkgs.git
```

Then refresh PKGBUILD repositories and install packages from this repo with paru:

```bash
paru -Sya
paru -S littlesnitch
```

Packages from PKGBUILD repositories take priority over the AUR, so this repo can override stale or broken AUR packages.

## Packages

### claude-desktop

Packages the [Claude Desktop](https://claude.ai/download) Linux beta from Anthropic's upstream `.deb` release for Arch Linux. The app includes Chat, Cowork, and Claude Code tabs on Linux.

Install it through paru from this repo:

```bash
paru -S claude-desktop
```

### littlesnitch

Packages [Little Snitch for Linux](https://obdev.at/products/littlesnitch-linux/) from the upstream `.pkg.tar.zst` release. A network monitor that uses eBPF to show which applications are opening outgoing connections, with a local web UI at `http://localhost:3031/`. Requires Linux 6.12+ with BTF kernel support.

Install it through paru from this repo:

```bash
paru -S littlesnitch
```

The AUR `littlesnitch-bin` package exists but lags upstream; this package takes priority from this repo without waiting on the public AUR.

### paper-design

Packages the [Paper](https://paper.design) desktop application from the upstream `.deb` release for Arch Linux. Paper is a collaborative design tool built on web standards that connects teams, agents, code, and data on a single canvas. Think Figma, but designed around agent workflows.

Install it through paru from this repo:

```bash
paru -S paper-design
```

## Development

Update all packages from the repo root:

```bash
./update.sh
```

Or run a package update script directly:

```bash
cd littlesnitch
./update.sh
```

Each script updates package metadata and regenerates `.SRCINFO`. Review and commit the resulting changes.
