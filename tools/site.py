#!/usr/bin/env -S uv run
"""Build site/: a static page showing every pack of the library (fabric images and colors), for
GitHub Pages. The Pages workflow runs this on each push to main.

    uv run tools/site.py          # writes site/index.html and copies the images it shows
    python -m http.server -d site # preview at http://localhost:8000
"""
import html, os, re, shutil, subprocess
from pathlib import Path
from common import ROOT, read_json

SITE = ROOT / 'site'
APP = 'https://ragingroosevelt.github.io/RRQuilts/'


def esc(s):
    return html.escape(str(s or ''), quote=True)


def repo_url():
    """The repository's GitHub address: from GitHub Actions, else the git remote; None if neither."""
    if os.environ.get('GITHUB_REPOSITORY'):
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}"
    try:
        url = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, capture_output=True,
                             text=True).stdout.strip()
    except OSError:
        return None
    m = re.match(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?$', url)
    return f'https://github.com/{m.group(1)}' if m else None


def how_to(repo):
    """Brief instructions for adding the library to RRQuilts."""
    if not repo:
        return (f'<p>Add it in <a href="{APP}">RRQuilts</a>: <b>Libraries › Add from the web…</b> with this '
                'library\'s address, or import its <code>.rrqlib</code> file in <b>Libraries › Import</b>.</p>')
    return f'''<div class="how">
<h2>Use it in <a href="{APP}">RRQuilts</a></h2>
<ol>
<li><b>Add this library</b> to get new collections as they're added.
<ol type="a">
<li>Copy this address:
<div class="copy"><input readonly value="{esc(repo)}" aria-label="Library address"
onfocus="this.select()"><button type="button" onclick="copyAddress(this)">Copy</button></div></li>
<li>In RRQuilts, open <b>Libraries › Add from the web…</b></li>
<li>Paste the address and click <b>Connect</b>.</li>
<li>Switch on the collections you want.</li>
</ol></li>
<li><b>Or import it</b> as a file.
<ol type="a">
<li>Download a <code>.rrqlib</code> file from the <a href="{esc(repo)}/releases/latest">latest release</a>:
<code>-256</code> is Light, <code>-512</code> Standard.</li>
<li>In RRQuilts, open <b>Libraries › Import</b> and choose the file.</li>
</ol></li>
</ol></div>'''


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
                    f'<figure><a class="zoom" href="{esc((base / large["path"]).as_posix())}"'
                    f' data-name="{esc(f["notecard"]["name"])}" data-size="{esc(size)}">'
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
    repo = repo_url()
    page = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(index["name"])}</title>
<style>
:root {{ color-scheme: light dark; --fg: #222; --muted: #666; --bg: #fff; --side: #f6f6f6; --line: #ddd; --accent: #1565c0; }}
@media (prefers-color-scheme: dark) {{ :root {{ --fg: #eee; --muted: #aaa; --bg: #121212; --side: #1c1c1c; --line: #333; --accent: #64b5f6; }} }}
* {{ box-sizing: border-box; }}
html, body {{ height: 100%; }}
body {{ margin: 0; font: 15px/1.4 system-ui, sans-serif; color: var(--fg); background: var(--bg);
  display: grid; grid-template-columns: 260px 1fr; overflow: hidden; }}
aside {{ background: var(--side); border-right: 1px solid var(--line); overflow-y: auto; padding: 16px 8px; }}
aside h1 {{ font-size: 18px; margin: 0 8px 12px; }}
aside a {{ display: block; padding: 4px 8px; border-radius: 4px; color: inherit; text-decoration: none; }}
aside a:hover {{ background: var(--line); }}
main {{ overflow-y: auto; padding: 16px 24px 48px; scroll-behavior: smooth; }}
main a {{ color: var(--accent); }}
.intro {{ max-width: 760px; }} .intro p, .by {{ color: var(--muted); margin: 0 0 8px; }}
.how {{ border: 1px solid var(--line); border-radius: 8px; padding: 4px 16px; margin: 12px 0 8px; }}
.how h2 {{ font-size: 17px; margin: 12px 0 4px; }} .how li {{ margin: 8px 0; }} .how ol ol {{ padding-left: 20px; }} .how ol ol li {{ margin: 4px 0; }}
.copy {{ display: flex; gap: 6px; margin-top: 6px; max-width: 520px; }}
.copy input {{ flex: 1; min-width: 0; font: 14px ui-monospace, monospace; padding: 6px 8px; border: 1px solid var(--line);
  border-radius: 4px; background: var(--bg); color: inherit; }}
button {{ font: inherit; padding: 6px 12px; border: 1px solid var(--line); border-radius: 4px; background: var(--side);
  color: inherit; cursor: pointer; }}
section h2 {{ margin: 24px 0 2px; border-top: 1px solid var(--line); padding-top: 16px; }}
section h2 span {{ color: var(--muted); font-weight: normal; font-size: .8em; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }}
figure {{ margin: 0; }} img, .sw {{ width: 100%; aspect-ratio: 1; object-fit: cover; border-radius: 6px; display: block; border: 1px solid var(--line); }}
figcaption {{ font-size: 12px; margin-top: 4px; overflow-wrap: anywhere; }} figcaption small {{ display: block; color: var(--muted); }}
dialog {{ border: none; padding: 0; background: transparent; color: #fff; max-width: 100vw; max-height: 100vh;
  width: 100vw; height: 100vh; }}
dialog::backdrop {{ background: rgba(0, 0, 0, .88); }}
.view {{ height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px; }}
.view img {{ width: auto; height: auto; max-width: min(92vw, 1024px); max-height: calc(100vh - 120px); aspect-ratio: auto;
  object-fit: contain; border: none; }}
.view p {{ margin: 10px 0 0; text-align: center; }} .view small {{ color: #bbb; }}
.nav {{ position: fixed; top: 50%; transform: translateY(-50%); font-size: 28px; line-height: 1; padding: 12px 16px;
  background: rgba(0, 0, 0, .5); color: #fff; border: none; border-radius: 50%; }}
.prev {{ left: 12px; }} .next {{ right: 12px; }}
.close {{ position: fixed; top: 12px; right: 12px; background: rgba(0, 0, 0, .5); color: #fff; border: none; font-size: 20px; }}
@media (max-width: 700px) {{
  body {{ display: flex; flex-direction: column; }}
  aside {{ max-height: 30vh; border-right: none; border-bottom: 1px solid var(--line); flex: none; }}
  main {{ flex: 1; padding: 12px 16px 48px; }}
}}
</style></head><body>
<aside><h1>{esc(index["name"])}</h1><nav aria-label="Collections">{nav}</nav></aside>
<main>
<div class="intro"><h1>{esc(index["name"])}</h1>
<p>{esc(index.get("description", ""))} {len(index["packs"])} packs, {total} colors and fabrics.</p>
{how_to(repo)}</div>
{"".join(sections)}</main>
<dialog id="carousel" aria-label="Fabric images">
<div class="view"><img alt=""><p><span class="name"></span><br><small class="meta"></small></p></div>
<button type="button" class="nav prev" aria-label="Previous">‹</button>
<button type="button" class="nav next" aria-label="Next">›</button>
<button type="button" class="close" aria-label="Close">✕</button>
</dialog>
<script>
function copyAddress(b) {{
  const input = b.previousElementSibling;
  input.select();
  (navigator.clipboard ? navigator.clipboard.writeText(input.value) : Promise.reject())
    .catch(() => document.execCommand('copy'))
    .finally(() => {{ b.textContent = 'Copied'; setTimeout(() => (b.textContent = 'Copy'), 1500); }});
}}
// Carousel: a collection's fabrics, opened at the one clicked.
const dlg = document.getElementById('carousel');
const img = dlg.querySelector('img');
let items = [], at = 0;
function show(i) {{
  at = (i + items.length) % items.length;
  const a = items[at];
  img.src = a.href;
  img.alt = a.dataset.name;
  dlg.querySelector('.name').textContent = a.dataset.name;
  dlg.querySelector('.meta').textContent = `${{a.dataset.size}} · ${{at + 1}} of ${{items.length}}`;
}}
document.querySelector('main').addEventListener('click', (e) => {{
  const a = e.target.closest('a.zoom');
  if (!a) return;
  e.preventDefault();
  items = [...a.closest('section').querySelectorAll('a.zoom')];
  show(items.indexOf(a));
  dlg.showModal();
}});
dlg.querySelector('.prev').onclick = () => show(at - 1);
dlg.querySelector('.next').onclick = () => show(at + 1);
dlg.querySelector('.close').onclick = () => dlg.close();
dlg.addEventListener('click', (e) => {{ if (e.target === dlg || e.target.classList.contains('view')) dlg.close(); }});
dlg.addEventListener('keydown', (e) => {{
  if (e.key === 'ArrowLeft') show(at - 1);
  if (e.key === 'ArrowRight') show(at + 1);
}});
let x0 = null;
dlg.addEventListener('touchstart', (e) => (x0 = e.touches[0].clientX), {{ passive: true }});
dlg.addEventListener('touchend', (e) => {{
  const dx = e.changedTouches[0].clientX - (x0 ?? e.changedTouches[0].clientX);
  if (Math.abs(dx) > 40) show(at + (dx < 0 ? 1 : -1));
  x0 = null;
}});
</script>
</body></html>
'''
    (SITE / 'index.html').write_text(page, encoding='utf-8')
    print(f'site/index.html: {len(index["packs"])} packs, {total} tiles')


if __name__ == '__main__':
    main()
