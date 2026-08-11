# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## Usage

### Binary repo (recommended)

All packages are built in CI and published to the private pacman repo at `pkgs.joshthomas.dev`. Packages and the repo database are signed; trust the committed signing key once:

```bash
sudo pacman-key --add ./josh.gpg
sudo pacman-key --lsign-key 553F177AEECD8B668AAD3FA0A6D0CBC27AE90D91
```

The repository owner provides an authenticated pacman stanza in `/etc/pacman.d/josh.conf`. Include it in `/etc/pacman.conf` before the official repositories:

```ini
Include = /etc/pacman.d/josh.conf
```

Then install like any official package:

```bash
sudo pacman -Syu
sudo pacman -S littlesnitch
```

Pacman gives the first configured repository priority when two repositories contain the same package name. Put `[josh]` before the official repositories to use this repo's `pandoc` and `shellcheck` builds; put it after them to prefer Arch's builds.

The R2 bucket has no public endpoint. An authenticated Cloudflare Worker at `pkgs.joshthomas.dev` handles package reads while GitHub Actions writes directly through R2's S3 API.

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

Install it from the binary repo:

```bash
sudo pacman -S claude-desktop
```

### littlesnitch

Packages [Little Snitch for Linux](https://obdev.at/products/littlesnitch-linux/) from the upstream `.pkg.tar.zst` release. A network monitor that uses eBPF to show which applications are opening outgoing connections, with a local web UI at `http://localhost:3031/`. Requires Linux 6.12+ with BTF kernel support.

Install it from the binary repo:

```bash
sudo pacman -S littlesnitch
```

The AUR `littlesnitch-bin` package exists but lags upstream; this package takes priority from this repo without waiting on the public AUR.

### paper-design

Packages the [Paper](https://paper.design) desktop application from the upstream `.deb` release for Arch Linux. Paper is a collaborative design tool built on web standards that connects teams, agents, code, and data on a single canvas. Think Figma, but designed around agent workflows.

Install it from the binary repo:

```bash
sudo pacman -S paper-design
```

## Development

### Integrity model

Every downloaded source and binary has a SHA-256 checksum; CI rejects `SKIP` entries. Automated update PRs replace those hashes when upstream publishes a new version, so review establishes trust in each new upstream artifact. The repository signature proves that a package passed this build pipeline and came from this repository; it does not add an upstream signature that the publisher did not provide.

CI fixes `SOURCE_DATE_EPOCH` to the repository commit time, so retrying the same commit cannot change an immutable package URL merely because the build ran later.

### Package updates

Upstream version checks are declarative: each package directory has a matching section in `nvchecker.toml`. Check all upstreams and apply updates (requires `uv` and `pacman-contrib`):

```bash
./update.py
```

New versions get `pkgver` bumped, `pkgrel` reset, checksums refreshed via `updpkgsums`, and `.SRCINFO` regenerated. Review and commit the resulting changes.

To add a package: create a directory with a `PKGBUILD` and add a section to `nvchecker.toml` named after the directory ([source reference](https://nvchecker.readthedocs.io/en/latest/usage.html#configuration-files)).

A scheduled workflow (`update.yml`) runs these scripts nightly and opens a PR when upstream releases a new version. Successful updates still reach the PR when another upstream check fails; the failed workflow names packages that need attention. On merge to `main`, the publish workflow (`publish.yml`) builds each package whose `.SRCINFO` version is missing from the repository database and syncs it to R2. Old package versions are never deleted, so previous releases stay available for `pacman -U` rollbacks.

The read-only Worker in `worker/index.mjs` requires HTTP Basic authentication, supports HEAD and byte-range requests, and disables shared caching. Deploy it with the personal Wrangler profile after setting `BASIC_AUTH_PASSWORD` as a Worker secret:

```bash
npx wrangler deploy --profile personal
```
