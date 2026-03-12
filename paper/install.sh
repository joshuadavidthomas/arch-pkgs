#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

makepkg -sf
sudo pacman -U --noconfirm paper-desktop-*.pkg.tar.zst
