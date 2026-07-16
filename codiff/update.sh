#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
fi

repo="nkzw-tech/codiff"
release_url="https://api.github.com/repos/$repo/releases/latest"

echo "Checking for latest Codiff version..."
release=$(curl -fsSL \
  -H "Accept: application/vnd.github+json" \
  -H "X-GitHub-Api-Version: 2022-11-28" \
  "$release_url")

upstream_tag=$(jq -er '.tag_name' <<< "$release")
if [[ ! "$upstream_tag" =~ ^v([0-9]+\.[0-9]+\.[0-9]+)$ ]]; then
  echo "Unexpected release tag: $upstream_tag" >&2
  exit 1
fi
upstream_version=${BASH_REMATCH[1]}
asset_name="codiff_${upstream_version}_amd64.deb"

asset=$(jq -er --arg name "$asset_name" \
  '.assets[] | select(.name == $name)' <<< "$release")
asset_url=$(jq -er '.browser_download_url' <<< "$asset")
asset_digest=$(jq -er '.digest' <<< "$asset")
expected_url="https://github.com/$repo/releases/download/$upstream_tag/$asset_name"

if [[ "$asset_url" != "$expected_url" ]]; then
  echo "Unexpected asset URL: $asset_url" >&2
  echo "Expected: $expected_url" >&2
  exit 1
fi

if [[ ! "$asset_digest" =~ ^sha256:([0-9a-f]{64})$ ]]; then
  echo "Unexpected asset digest: $asset_digest" >&2
  exit 1
fi
new_sha256=${BASH_REMATCH[1]}
current_version=$(sed -n 's/^pkgver=//p' PKGBUILD)

echo "Current:  $current_version"
echo "Upstream: $upstream_version"

if [[ "$upstream_version" == "$current_version" ]] && ! $force; then
  echo "PKGBUILD is already up to date."
  exit 0
fi

echo "Updating PKGBUILD to $upstream_version..."
sed -i "s/^pkgver=.*/pkgver=$upstream_version/" PKGBUILD
sed -i "s/^pkgrel=.*/pkgrel=1/" PKGBUILD
sed -i "s/^sha256sums_x86_64=.*/sha256sums_x86_64=('$new_sha256')/" PKGBUILD
makepkg --printsrcinfo > .SRCINFO

echo "Updated PKGBUILD and .SRCINFO to $upstream_version."
