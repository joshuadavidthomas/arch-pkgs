#!/usr/bin/env bash
set -euo pipefail

# Check if niri upstream has fixed the Wayland buffer size issue.
# Looks for wl_display_set_default_max_buffer_size or max_buffer_size
# in the niri source on the main branch.

echo "Checking niri upstream for buffer size fix..."

if curl -sf "https://raw.githubusercontent.com/YaLTeR/niri/main/src/main.rs" \
    | grep -q 'max_buffer_size'; then
    echo "✅ Fix appears to be upstream! You can drop the patch."
    echo "   Remove niri/max-buffer-size.patch and the patch line from niri/PKGBUILD,"
    echo "   or just switch back to the official Arch package:"
    echo "     sudo pacman -S niri"
else
    echo "❌ Fix is NOT upstream yet. Keep using the patched PKGBUILD."

    installed=$(pacman -Q niri 2>/dev/null | awk '{print $2}')
    latest=$(pacman -Si niri 2>/dev/null | awk '/^Version/ {print $3}')

    if [[ -n "$installed" && -n "$latest" && "$installed" != "$latest"* ]]; then
        echo ""
        echo "⚠️  New version available: $latest (you have $installed)"
        echo "   Update pkgver in niri/PKGBUILD, then:"
        echo "     cd niri && makepkg -sf --nocheck && sudo pacman -U niri-*.pkg.tar.zst"
    fi
fi
