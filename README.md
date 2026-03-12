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

```bash
cd <package>
makepkg -sf --nocheck
sudo pacman -U <package>-*.pkg.tar.zst
```

## Upgrading

### niri

When a new niri version is released, check if the fix has been merged upstream:

```bash
cd niri
./check-upstream.sh
```

If the fix is not yet upstream, update the `pkgver` in `niri/PKGBUILD`, rebuild, and reinstall.

### paper-desktop

```bash
cd paper
./upgrade.sh
makepkg -sf
sudo pacman -U paper-desktop-*.pkg.tar.zst
```
