# RRQuilts library template

A starting point for an [RRQuilts](https://ragingroosevelt.github.io/RRQuilts/) library: palettes of
fabric images (and later blocks) that quilters add to the app. One repository is one **library**; each
folder in `sources/` becomes a **pack** (one palette) that people can switch on or off.

## Make your library

1. On GitHub, choose **Use this template** (not Fork, so your library starts with clean history).
2. Install [uv](https://docs.astral.sh/uv/) (it brings the right Python and Pillow).
3. Edit `library.config.json`: an `id` (lowercase, e.g. `jane-doe-fabrics`), name, description,
   author, and license (an SPDX id like `CC-BY-SA-4.0`, or `LicenseRef-Personal-Use` for images you
   may only use yourself). Optional `links`: the library's `homepage`, its `gallery` (the Gallery
   site's address) and `others` (each a `name` and `url`). The app's globe icon opens the home page
   (else the gallery), and the gallery lists them under About. Release files name the repository they
   come from, so RRQuilts can connect an imported file to it; on GitHub that's automatic, elsewhere
   set `repository` (its web address) in `library.config.json`.
4. Put each palette's images in its own folder under `sources/` (JPEG, PNG, or WebP). Optional
   `pack.json` in a folder: `name`, `designer`, `tags`, `size_inches` (the real width each image
   shows; 8 when absent, and the app marks it ≈), `crop` (square from the center; default true),
   `description`, and `fabrics`: per-file overrides, e.g.
   `{"13900-11.jpg": {"name": "Daisy Pink", "sku": "13900 11", "size": [44, 22]}}` (size in inches).
   A folder may also hold a `palette.rrqplt` (exported from RRQuilts): its colors join the pack, so
   a solids pack needs no images. Optional in `library.config.json`: `manufacturer`, which fabrics
   then name with their SKU (e.g. "Moda Fabrics 13900 11").
5. Build and check:

   ```sh
   uv run tools/build.py --note "First release"
   uv run tools/validate.py
   ```

   This writes `library.json` and `packs/<pack>/` with each image as WebP at 256 and 512 px
   (never enlarged), plus each fabric's average color.
6. Commit everything except `dist/`, push, and tag a release: `git tag v1 && git push --tags`. The
   **Release** action builds a `.rrqlib` file of the whole library at each size:
   `-256` (Light) and `-512` (Standard). For sharper printouts, build with `--print` to add 1024 px
   images and a `-1024` file; it roughly triples the library's size.

To add or change palettes later: edit `sources/`, run `tools/build.py --note "what changed"`, commit,
and tag the next version. Only changed packs are rebuilt, and each gets a new revision.

## Hosting it

RRQuilts reads a library straight from the web, so the files must be reachable and allow other
websites to read them (CORS):

- **Public GitHub repository** (simplest): people add it with its address,
  `https://github.com/<you>/<repo>`. RRQuilts reads the files from `raw.githubusercontent.com`.
- **GitHub Pages**: turn on Pages for the repository (Settings › Pages › Deploy from a branch ›
  `main` / root) and share the Pages address.
- **Any static host** (Netlify, Codeberg Pages, your own server) that sends
  `Access-Control-Allow-Origin: *` for these files.
- **Release downloads** (`.rrqlib` files) are for importing by hand (RRQuilts › Libraries ›
  Import). Browsers can't read GitHub release downloads from another site, so they can't be
  connected to.
- **Private libraries**: keep the repository private and share the `.rrqlib` files instead.

Images under `LicenseRef-Personal-Use` (for example, a manufacturer's product photos) belong in a
private repository or local `.rrqlib` files only.

## Keeping up with RRQuilts

Every file records its format version. The **RRQuilts format check** action runs weekly and opens an
issue when the app has newer library formats. Then run:

```sh
uv run tools/upgrade.py     # fetches the latest tools and rebuilds every pack
uv run tools/validate.py
```

and commit. (`uv run tools/upgrade.py --check` only reports.) The app also says when a library it has
uses an older format.

## Layout

```
library.config.json     your library's details (you edit this)
sources/<pack>/         your images, one folder per palette (+ optional pack.json)
library.json            the index the app reads first (built)
packs/<pack>/rrqlib.json  one pack (built)
packs/<pack>/<size>/    its images (built)
tools/                  build, validate, release, upgrade
.github/workflows/      validate on push, release on tag, weekly format check
```

## Gallery site

Every push to `main` builds a page showing all the library's fabrics and colors (`tools/site.py`,
workflow **Gallery site**) and publishes it with GitHub Pages. Turn it on once: **Settings › Pages ›
Source: GitHub Actions**. Preview it locally with `uv run tools/site.py` and open `site/index.html`.
The page is public like the repository, so only publish images you're allowed to share.

