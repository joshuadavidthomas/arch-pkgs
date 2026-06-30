#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
fi

repo_url="https://downloads.claude.ai/claude-desktop/apt/stable"
packages_url="$repo_url/dists/stable/main/binary-amd64/Packages"

echo "Checking for latest Claude Desktop version..."
package_rows=$(curl -fsSL "$packages_url" | awk '
  BEGIN { RS=""; FS="\n" }
  {
    package=""
    architecture=""
    version=""
    filename=""
    sha256=""
    for (i = 1; i <= NF; i++) {
      if ($i ~ /^Package: /) {
        package = substr($i, 10)
      } else if ($i ~ /^Architecture: /) {
        architecture = substr($i, 15)
      } else if ($i ~ /^Version: /) {
        version = substr($i, 10)
      } else if ($i ~ /^Filename: /) {
        filename = substr($i, 11)
      } else if ($i ~ /^SHA256: /) {
        sha256 = substr($i, 9)
      }
    }
    if (package == "claude-desktop" && architecture == "amd64" && version != "" && filename != "" && sha256 != "") {
      print version, filename, sha256
    }
  }
')

if [[ -z "$package_rows" ]]; then
  echo "Could not find claude-desktop amd64 metadata in $packages_url." >&2
  exit 1
fi

latest=$(printf '%s\n' "$package_rows" | sort -V -k1,1 | tail -n1)
read -r upstream_version upstream_filename new_sha256 <<< "$latest"
current_version=$(sed -n 's/^pkgver=//p' PKGBUILD)
expected_filename="pool/main/c/claude-desktop/claude-desktop_${upstream_version}_amd64.deb"

if [[ "$upstream_filename" != "$expected_filename" ]]; then
  echo "Unexpected upstream filename: $upstream_filename" >&2
  echo "Expected: $expected_filename" >&2
  exit 1
fi

echo "Current:  $current_version"
echo "Upstream: $upstream_version"

if [[ "$upstream_version" == "$current_version" ]] && ! $force; then
  echo "PKGBUILD is already up to date."
  exit 0
fi

echo "Updating PKGBUILD to $upstream_version..."
sed -i "s/^pkgver=.*/pkgver=$upstream_version/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums=.*/sha256sums=('$new_sha256')/" PKGBUILD
makepkg --printsrcinfo > .SRCINFO

echo "Updated PKGBUILD and .SRCINFO to $upstream_version."
