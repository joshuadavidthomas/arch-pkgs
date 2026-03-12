# arch-pkgs

Patched Arch Linux packages. Local overlay for fixes not yet upstream.

## Packages

### niri

Patches the Wayland compositor [niri](https://github.com/YaLTeR/niri) to increase the default client buffer size from 4 KiB to 1 MiB, fixing "Data too big for buffer" errors that kill applications on multi-monitor setups.

- **Upstream issue:** https://github.com/YaLTeR/niri/issues/2437
- **Fix based on:** [Sway PR #8532](https://github.com/swaywm/sway/pull/8532)

### paper-desktop

Packages the [Paper](https://paper.design) desktop application (a Figma-like design tool for agent integration) from the upstream `.deb` release for Arch Linux.

## Usage

### niri

```bash
cd niri
makepkg -sf --nocheck
sudo pacman -U niri-*.pkg.tar.zst
```

When a new version is released, check if the fix has been merged upstream:

```bash
./check-upstream.sh
```

If not yet upstream, update `pkgver` in `PKGBUILD`, rebuild, and reinstall.

### paper-desktop

```bash
cd paper
./install.sh
```

This checks the latest upstream version, updates the PKGBUILD if needed, builds, and installs. If already up to date, it exits early. To force a reinstall:

```bash
./install.sh --force
```
