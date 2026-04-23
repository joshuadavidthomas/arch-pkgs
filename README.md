# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## niri

Patches the Wayland compositor [niri](https://github.com/niri-wm/niri) to increase the default client buffer size from 4 KiB to 1 MiB, fixing "Data too big for buffer" errors that kill applications on multi-monitor setups.

- **Upstream issue:** https://github.com/YaLTeR/niri/issues/2437
- **Fix based on:** [Sway PR #8532](https://github.com/swaywm/sway/pull/8532)

```bash
cd niri
./install.sh
```

Checks if the upstream fix has landed (and tells you to switch back to the official package if so), updates the PKGBUILD to the latest repo version if needed, builds, and installs. If already up to date, it exits early. Use `./install.sh --force` to reinstall.

## paper-design

Packages the [Paper](https://paper.design) desktop application from the upstream `.deb` release for Arch Linux. Paper is a collaborative design tool built on web standards that connects teams, agents, code, and data on a single canvas. Think Figma, but designed around agent workflows.

```bash
cd paper
./install.sh
```

Checks the latest upstream version, updates the PKGBUILD if needed, builds, and installs. If already up to date, it exits early. Use `./install.sh --force` to reinstall.

## littlesnitch

Packages [Little Snitch for Linux](https://obdev.at/products/littlesnitch-linux/) from the upstream `.pkg.tar.zst` release. A network monitor that uses eBPF to show which applications are opening outgoing connections, with a local web UI at `http://localhost:3031/`. Requires Linux 6.12+ with BTF kernel support.

```bash
cd littlesnitch
./install.sh
```

Checks the latest upstream version, updates the PKGBUILD if needed (pulling the SHA-256 from the upstream signed `hashes.txt`), builds, and installs. If already up to date, it exits early. Use `./install.sh --force` to reinstall.

The AUR `littlesnitch-bin` package exists but lags upstream; this exists so I can stay current without waiting on it.
