# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## Usage

### Binary repo (recommended)

Packages are built in CI and published to a pacman repo at `pkgs.joshthomas.dev`. Packages and the repo database are signed; trust the signing key once:

```bash
curl -fsSL https://pkgs.joshthomas.dev/josh.gpg | sudo pacman-key --add -
sudo pacman-key --lsign-key 553F177AEECD8B668AAD3FA0A6D0CBC27AE90D91
```

Add this to `/etc/pacman.conf`:

```ini
[josh]
SigLevel = Required DatabaseRequired
Server = https://pkgs.joshthomas.dev/arch/$repo/os/$arch
```

Then install like any official package:

```bash
sudo pacman -Syu
sudo pacman -S littlesnitch
```

### PKGBUILD repo via paru

Alternatively, this repo can be used as a custom PKGBUILD repository in paru, so packages here can be installed and upgraded without publishing them to the AUR.

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

Upstream version checks are declarative: each package directory has a matching section in `nvchecker.toml`. Check all upstreams and apply updates (requires `uv` and `pacman-contrib`):

```bash
./update.py
```

New versions get `pkgver` bumped, `pkgrel` reset, checksums refreshed via `updpkgsums`, and `.SRCINFO` regenerated. Review and commit the resulting changes.

To add a package: create a directory with a `PKGBUILD` and add a section to `nvchecker.toml` named after the directory ([source reference](https://nvchecker.readthedocs.io/en/latest/usage.html#configuration-files)).

A scheduled workflow (`update.yml`) runs these scripts nightly and opens a PR when upstream releases a new version. On merge to `main`, the publish workflow (`publish.yml`) builds any package whose `.SRCINFO` version is missing from the published database and syncs it to the R2 bucket behind `pkgs.joshthomas.dev`. Old package versions are never deleted, so previous releases stay available for `pacman -U` rollbacks.
