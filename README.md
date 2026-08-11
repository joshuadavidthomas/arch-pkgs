# arch-pkgs

Personal Arch Linux package overlay. The PKGBUILDs are public; the signed binary repository is private to my machines.

Each top-level package directory contains a `PKGBUILD` and generated `.SRCINFO`. `nvchecker.toml` tracks upstream releases.

## Install

### Private binary repository

Trust the committed signing key once:

```bash
sudo pacman-key --add ./josh.gpg
sudo pacman-key --lsign-key 553F177AEECD8B668AAD3FA0A6D0CBC27AE90D91
```

Declare the repository in `/etc/pacman.conf` before the official repositories:

```ini
[josh]
Include = /etc/pacman.d/josh.conf
```

Keep the credentials in `/etc/pacman.d/josh.conf`. This included file has no repository header:

```ini
SigLevel = Required DatabaseRequired
Server = https://josh:<password>@pkgs.joshthomas.dev/arch/$repo/os/$arch
```

Install and update packages through pacman:

```bash
sudo pacman -Syu
sudo pacman -S littlesnitch
```

Repository order decides which build pacman uses when `[josh]` and an official repository contain the same package. Keeping `[josh]` first selects this repo's `pandoc` and `shellcheck` builds.

### Public PKGBUILD repository

Paru can build these packages without access to the private binary repository. Add this to `~/.config/paru/paru.conf`:

```ini
[arch-pkgs]
Url = https://github.com/joshuadavidthomas/arch-pkgs.git
```

Refresh the repository and install a package:

```bash
paru -Sya
paru -S littlesnitch
```

## Maintain

### Update packages

`update.py` checks every entry in `nvchecker.toml`, updates versions and checksums, and regenerates `.SRCINFO`:

```bash
./update.py
```

Review the resulting PKGBUILD changes before committing them. The nightly `update.yml` workflow runs the same update and opens a pull request when versions change.

Run the repository checks with:

```bash
node --test worker/index.test.mjs
uv run pytest
uv run ruff check update.py tests
actionlint
```

CI rejects missing source checksums and mismatched package metadata.

### Publish binaries

`publish.yml` builds package versions missing from the repository database, signs each package and database, and uploads them to the private R2 bucket. The workflow refuses to publish unless `pkgs.joshthomas.dev` rejects an anonymous request.

The Worker in `worker/index.mjs` authenticates reads from `pkgs.joshthomas.dev` and serves the R2 objects needed by pacman. R2 has no public domain or `r2.dev` endpoint.

Set its password once, then deploy it with the personal Wrangler profile:

```bash
npx wrangler secret put BASIC_AUTH_PASSWORD --profile personal
npx wrangler deploy --profile personal
```
