#!/usr/bin/env -S uv run
"""Build site/: a static page showing every pack of the library (fabric images and colors), for
GitHub Pages. The Pages workflow runs this on each push to main.

    uv run tools/site.py          # writes site/index.html and copies the images it shows
    python -m http.server -d site # preview at http://localhost:8000
"""
import html, json, shutil
from pathlib import Path
from common import ROOT, read_json

SITE = ROOT / 'site'
APP = 'https://ragingroosevelt.github.io/RRQuilts/'


def esc(s):
    return html.escape(str(s or ''), quote=True)


def main():
    index = read_json(ROOT / 'library.json')
    shutil.rmtree(SITE, ignore_errors=True)
    SITE.mkdir()
    sections, total = [], 0
    for p in sorted(index['packs'], key=lambda p: p['name'].lower()):
        doc = read_json(ROOT / p['path'])
        base = Path(p['path']).parent
        tiles = []
        for item in doc['items']:
            data = item['data']
            for c in data.get('colors', []):
                rgb = 'rgb({},{},{})'.format(*c['rgb'])
                tiles.append(f'<figure><div class="sw" style="background:{rgb}"></div>'
                             f'<figcaption>{esc(c["notecard"]["name"])}</figcaption></figure>')
            for f in data.get('fabrics', []):
                sizes = sorted(f.get('sizes', []), key=lambda s: s['px'])
                small = next((s for s in sizes if s['px'] <= 256), sizes[0] if sizes else None)
                large = sizes[-1] if sizes else None
                if not small:
                    continue
                for s in {small['path'], large['path']}:
                    dest = SITE / base / s
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(ROOT / base / s, dest)
                avg = 'rgb({},{},{})'.format(*f['average'])
                size = ' × '.join(f'{n:g}' for n in f['size']) + ' in' + (' ≈' if f.get('approximate') else '')
                tiles.append(
                    f'<figure><a href="{esc((base / large["path"]).as_posix())}">'
                    f'<img src="{esc((base / small["path"]).as_posix())}" alt="{esc(f["notecard"]["name"])}"'
                    f' loading="lazy" style="background:{avg}"></a>'
                    f'<figcaption>{esc(f["notecard"]["name"])}<small>{esc(size)}</small></figcaption></figure>')
        total += len(tiles)
        who = ' · '.join(x for x in [doc.get('author', {}).get('name'), p.get('date') if p.get('date') != '??-??' else ''] if x)
        sections.append(
            f'<section id="{esc(p["id"])}"><h2>{esc(p["name"])} <span>{len(tiles)}</span></h2>'
            f'<p class="by">{esc(who)}</p><div class="grid">{"".join(tiles)}</div></section>')
    nav = ''.join(f'<a href="#{esc(p["id"])}">{esc(p["name"])}</a>'
                  for p in sorted(index['packs'], key=lambda p: p['name'].lower()))
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(index["name"])}</title>
<style>
:root {{ color-scheme: light dark; --fg: #222; --muted: #666; --bg: #fff; --line: #ddd; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg: #eee; --muted: #aaa; --bg: #121212; --line: #333; }} }}
body {{ margin: 0; font: 15px/1.4 system-ui, sans-serif; color: var(--fg); background: var(--bg); }}
header, main {{ max-width: 1100px; margin: 0 auto; padding: 16px; }}
h1 {{ margin: 0 0 4px; }} .by, header p {{ color: var(--muted); margin: 0 0 8px; }}
nav {{ display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: 8px; }} nav a {{ color: inherit; }}
h2 {{ margin: 24px 0 2px; border-top: 1px solid var(--line); padding-top: 16px; }} h2 span {{ color: var(--muted); font-weight: normal; font-size: .8em; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }}
figure {{ margin: 0; }} img, .sw {{ width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 6px; display: block; border: 1px solid var(--line); }}
figcaption {{ font-size: 12px; margin-top: 4px; }} figcaption small {{ display: block; color: var(--muted); }}
</style></head><body>
<header><h1>{esc(index["name"])}</h1>
<p>{esc(index.get("description", ""))} {len(index["packs"])} packs, {total} colors and fabrics.
Use it in <a href="{APP}">RRQuilts</a>: Libraries › Add from the web, then this repository's address.</p>
<nav>{nav}</nav></header>
<main>{"".join(sections)}</main></body></html>
'''
    (SITE / 'index.html').write_text(page, encoding='utf-8')
    print(f'site/index.html: {len(index["packs"])} packs, {total} tiles')


if __name__ == '__main__':
    main()
