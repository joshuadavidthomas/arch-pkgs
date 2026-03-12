# arch-pkgs

Custom Arch Linux packages. Local overlay for fixes not yet upstream and repackaged applications.

## niri

Patches the Wayland compositor [niri](https://github.com/YaLTeR/niri) to increase the default client buffer size from 4 KiB to 1 MiB, fixing "Data too big for buffer" errors that kill applications on multi-monitor setups.

- **Upstream issue:** https://github.com/YaLTeR/niri/issues/2437
- **Fix based on:** [Sway PR #8532](https://github.com/swaywm/sway/pull/8532)

```bash
cd niri
./install.sh
```

Checks if the upstream fix has landed (and tells you to switch back to the official package if so), updates the PKGBUILD to the latest repo version if needed, builds, and installs. If already up to date, it exits early. Use `./install.sh --force` to reinstall.

## paper-desktop

Packages the [Paper](https://paper.design) desktop application (a Figma-like design tool for agent integration) from the upstream `.deb` release for Arch Linux.

```bash
cd paper
./install.sh
```

Checks the latest upstream version, updates the PKGBUILD if needed, builds, and installs. If already up to date, it exits early. Use `./install.sh --force` to reinstall.
