# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## Use with paru

This repo can be used as a custom PKGBUILD repository in paru, so packages here can be installed and upgraded without publishing them to the AUR.

Add this to `~/.config/paru/paru.conf`:

```ini
[arch-pkgs]
Url = https://github.com/joshuadavidthomas/arch-pkgs.git
Depth = 1
GenerateSrcinfo
```

Then refresh PKGBUILD repositories and install packages from this repo with paru:

```bash
paru -Sya
paru -S littlesnitch
```

Packages from PKGBUILD repositories take priority over the AUR, so this repo can override stale or broken AUR packages.

## niri-max-buffer-size

Patches the Wayland compositor [niri](https://github.com/niri-wm/niri) to increase the default client buffer size from 4 KiB to 1 MiB, fixing "Data too big for buffer" errors that kill applications on multi-monitor setups.

- **Upstream issue:** https://github.com/YaLTeR/niri/issues/2437
- **Fix based on:** [Sway PR #8532](https://github.com/swaywm/sway/pull/8532)

Install it through paru from this repo:

```bash
paru -S niri-max-buffer-size
```

The package is named `niri-max-buffer-size` because official repo packages win for `paru -S niri`. This package `provides` and `conflicts` with `niri` so it can replace the official package cleanly.

To update the package metadata when a new upstream `niri` release lands:

```bash
cd niri
./update.sh
```

`update.sh` checks whether the patch is still needed, bumps `pkgver`, refreshes checksums, and regenerates `.SRCINFO`.

## paper-design

Packages the [Paper](https://paper.design) desktop application from the upstream `.deb` release for Arch Linux. Paper is a collaborative design tool built on web standards that connects teams, agents, code, and data on a single canvas. Think Figma, but designed around agent workflows.

Install it through paru from this repo:

```bash
paru -S paper-design
```

To update the package metadata when upstream releases a new version:

```bash
cd paper
./update.sh
```

`update.sh` bumps `pkgver`, refreshes the SHA-256 from the current upstream `.deb`, and regenerates `.SRCINFO`.

## littlesnitch

Packages [Little Snitch for Linux](https://obdev.at/products/littlesnitch-linux/) from the upstream `.pkg.tar.zst` release. A network monitor that uses eBPF to show which applications are opening outgoing connections, with a local web UI at `http://localhost:3031/`. Requires Linux 6.12+ with BTF kernel support.

Install it through paru from this repo:

```bash
paru -S littlesnitch
```

To update the package metadata when upstream releases a new version:

```bash
cd littlesnitch
./update.sh
```

`update.sh` bumps `pkgver`, refreshes the SHA-256 from the upstream signed `hashes.txt`, and regenerates `.SRCINFO`.

The AUR `littlesnitch-bin` package exists but lags upstream; this package takes priority from this repo without waiting on the public AUR.
