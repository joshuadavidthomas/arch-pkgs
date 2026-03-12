#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

echo "Downloading latest Paper deb to check version..."
tmpfile=$(mktemp --suffix=.deb)
trap 'rm -f "$tmpfile"' EXIT

curl -fSL -o "$tmpfile" https://download.paper.design/linux/deb

upstream_version=$(ar p "$tmpfile" control.tar.* | tar xf - --to-stdout ./control 2>/dev/null | sed -n 's/^Version: \([^-]*\).*/\1/p')
current_version=$(sed -n 's/^pkgver=//p' PKGBUILD)

echo "Current: $current_version"
echo "Upstream: $upstream_version"

if [[ "$upstream_version" == "$current_version" ]]; then
  echo "Already up to date."
  exit 0
fi

echo "Updating PKGBUILD to $upstream_version..."
new_sha256=$(sha256sum "$tmpfile" | awk '{print $1}')
sed -i "s/^pkgver=.*/pkgver=$upstream_version/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums=.*/sha256sums=('$new_sha256')/" PKGBUILD

echo "Updated. Build with: makepkg -sf"
