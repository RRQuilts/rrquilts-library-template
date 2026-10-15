#!/usr/bin/env -S uv run
"""Build site/: a static page showing every pack of the library (fabric images and colors), for
GitHub Pages. The Pages workflow runs this on each push to main.

    uv run tools/site.py          # writes site/index.html and copies the images it shows
    python -m http.server -d site # preview at http://localhost:8000
"""
import html, re, shutil
from urllib.parse import quote
from pathlib import Path
from common import ROOT, read_json, repo_url

SITE = ROOT / 'site'
# Material "menu" icon, for the collections list on phones.
MENU_ICON = ('<svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true"><path fill="currentColor" '
             'd="M3 18h18v-2H3v2zm0-5h18v-2H3v2zm0-7v2h18V6H3z"/></svg>')
# Material "share" icon, for the Share buttons.
SHARE_ICON = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M18 16.08c-.76 '
              '0-1.44.3-1.96.77L8.91 12.7c.05-.23.09-.46.09-.7s-.04-.47-.09-.7l7.05-4.11c.54.5 1.25.81 2.04.81 1.66 0 3-1.34 '
              '3-3s-1.34-3-3-3-3 1.34-3 3c0 .24.04.47.09.7L8.04 9.81C7.5 9.31 6.79 9 6 9c-1.66 0-3 1.34-3 3s1.34 3 3 3c.79 0 '
              '1.5-.31 2.04-.81l7.12 4.16c-.05.21-.08.43-.08.65 0 1.61 1.31 2.92 2.92 2.92s2.92-1.31 2.92-2.92-1.31-2.92-2.92-2.92z"/></svg>')
# Material "link" icon, for the Copy link buttons.
LINK_ICON = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M3.9 12c0-1.71 '
             '1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 '
             '0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg>')
APP = 'https://ragingroosevelt.github.io/RRQuilts/'


def esc(s):
    return html.escape(str(s or ''), quote=True)


def file_mb(index, *px):
    """About how big a release file is: the index, pack documents and images of sizes `px`, in MB
    rounded to 10."""
    n = (ROOT / 'library.json').stat().st_size + sum(
        (ROOT / p['path']).stat().st_size + sum(p.get('sizes', {}).get(str(x), 0) for x in px)
        for p in index['packs'])
    return max(10, round(n / 1e7) * 10)


def about_links(index):
    """The library's web pages: home page first, then the others (not the gallery: this is it)."""
    lk = index.get('links') or {}
    pages = ([('Home page', lk['homepage'])] if lk.get('homepage') else []) + [
        (o.get('name') or o['url'], o['url']) for o in lk.get('others', []) if o.get('url')]
    pages = [(n, u) for n, u in pages if re.match(r'https?://', u)]
    if not pages:
        return ''
    return '<ul class="links">' + ''.join(f'<li><a href="{esc(u)}">{esc(n)}</a></li>' for n, u in pages) + '</ul>'


def how_to(repo, index):
    """Brief instructions for adding the library to RRQuilts."""
    if not repo:
        return (f'<p>Add it in <a href="{APP}">RRQuilts</a>: <b>Libraries › Add from the web…</b> with this '
                'library\'s address, or import its <code>.rrqlib</code> file in <b>Libraries › Import</b>.</p>')
    return f'''<div class="how">
<p>Add it to <a href="{APP}">RRQuilts</a> in one of three ways:</p>
<ol>
<li><b>Follow <a href="{APP}libraries?add={quote(repo, safe='')}">this link</a></b> to add this library
in RRQuilts, then enable the collections you want. New collections reach you as they're added.</li>
<li><b>Or add it by hand.</b>
<ol type="a">
<li>Copy this address:
<div class="copy"><input readonly value="{esc(repo)}" aria-label="Library address"
onfocus="this.select()"><button type="button" onclick="copyAddress(this)">Copy</button></div></li>
<li>In RRQuilts, open <b>Libraries › Add from the web…</b></li>
<li>Paste the address and click <b>Connect</b>.</li>
<li>Enable the collections you want.</li>
</ol></li>
<li><b>Or import it</b> as a file.
<ol type="a">
<li>Download a file from the <a href="{esc(repo)}/releases/latest">latest release</a>: <code>-256</code> is
smaller (about {file_mb(index, 256)} MB), <code>-512</code> is larger with sharper images (about
{file_mb(index, 256, 512)} MB).</li>
<li>In RRQuilts, open <b>Libraries › Import</b> and choose the file.</li>
</ol>
An imported file doesn't update itself. To get new collections, import a newer release.</li>
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
            f'<section id="{esc(p["id"])}"><div class="head"><h2>{esc(p["name"])} <span>{len(tiles)}</span></h2>'
            f'<button type="button" class="link icon" data-act="copy" aria-label="Copy link" title="Copy link">{LINK_ICON}</button>'
            f'<button type="button" class="link icon share" data-act="share" aria-label="Share" title="Share" hidden>{SHARE_ICON}</button></div>'
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
aside h1 {{ font-size: 24px; line-height: 1.2; margin: 0 8px 12px; }}
.bar {{ display: flex; align-items: center; justify-content: space-between; }}
.menu {{ display: none; padding: 4px; border: none; background: none; }}
aside h1 a {{ padding: 0; font-weight: inherit; }} aside h1 a:hover {{ background: none; text-decoration: underline; }}
aside a {{ display: block; padding: 4px 8px; border-radius: 4px; color: inherit; text-decoration: none; }}
aside a:hover {{ background: var(--line); }}
main {{ overflow-y: auto; padding: 16px 24px 48px; scroll-behavior: smooth; position: relative; }}
#top {{ position: absolute; top: 0; }}
aside a[aria-current] {{ background: var(--line); font-weight: 600; }}
main a {{ color: var(--accent); }}
.intro {{ max-width: 760px; }} .intro p, .by {{ color: var(--muted); margin: 0 0 8px; }}
.intro h1 {{ font-size: 22px; margin: 8px 0 6px; }} .intro h1 + p {{ margin-top: 0; }}
.links {{ margin: 0 0 16px; padding-left: 20px; }} .links li {{ margin: 2px 0; }}
.how {{ border: 1px solid var(--line); border-radius: 8px; padding: 4px 16px; margin: 0 0 8px; }}
.how h2 {{ font-size: 17px; margin: 12px 0 4px; }} .how li {{ margin: 8px 0; }} .how ol ol {{ padding-left: 20px; }} .how ol ol li {{ margin: 4px 0; }}
.copy {{ display: flex; gap: 6px; margin-top: 6px; max-width: 520px; }}
.copy input {{ flex: 1; min-width: 0; font: 14px ui-monospace, monospace; padding: 6px 8px; border: 1px solid var(--line);
  border-radius: 4px; background: var(--bg); color: inherit; }}
button {{ font: inherit; padding: 6px 12px; border: 1px solid var(--line); border-radius: 4px; background: var(--side);
  color: inherit; cursor: pointer; }}
section .head {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 24px;
  border-top: 1px solid var(--line); padding-top: 16px; }}
section h2 {{ margin: 0 auto 2px 0; }}
button.link {{ font-size: 13px; padding: 3px 10px; }}
button.icon {{ display: inline-flex; align-items: center; padding: 4px; }}
button[hidden] {{ display: none; }}
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
#toast {{ position: fixed; left: 50%; bottom: 24px; transform: translate(-50%, 12px); opacity: 0; pointer-events: none;
  background: #323232; color: #fff; padding: 10px 18px; border-radius: 6px; box-shadow: 0 2px 8px rgba(0, 0, 0, .3);
  transition: opacity .2s, transform .2s; }}
#toast.on {{ opacity: 1; transform: translate(-50%, 0); }}
@media (max-width: 700px) {{
  body {{ display: flex; flex-direction: column; }}
  aside {{ border-right: none; border-bottom: 1px solid var(--line); flex: none; padding: 8px; overflow: visible;
    position: relative; z-index: 5; }}
  aside h1 {{ font-size: 22px; margin: 0 8px; }}
  .menu {{ display: inline-flex; }}
  aside nav {{ display: none; position: absolute; top: 100%; left: 0; right: 0; max-height: 70vh; overflow-y: auto;
    padding: 8px; background: var(--side); border-bottom: 1px solid var(--line); box-shadow: 0 8px 16px rgba(0, 0, 0, .25); }}
  aside.open nav {{ display: block; }}
  main {{ flex: 1; padding: 12px 16px 48px; }}
}}
</style></head><body>
<aside><div class="bar"><h1><a href="#top" title="Back to the top">{esc(index["name"])}</a></h1>
<button type="button" class="menu" aria-expanded="false" aria-controls="toc" aria-label="Collections">{MENU_ICON}</button></div>
<nav id="toc" aria-label="Collections">{nav}</nav></aside>
<main>
<span id="top"></span>
<div class="intro">
<h1>About</h1>
<p>{esc(index.get("description", ""))} {len(index["packs"])} packs, {total} colors and fabrics.</p>
{about_links(index)}
<h1>Installing</h1>
{how_to(repo, index)}</div>
{"".join(sections)}</main>
<div id="toast" role="status" aria-live="polite"></div>
<dialog id="carousel" aria-label="Fabric images">
<div class="view"><img alt=""><p><span class="name"></span><br><small class="meta"></small></p></div>
<button type="button" class="nav prev" aria-label="Previous">‹</button>
<button type="button" class="nav next" aria-label="Next">›</button>
<button type="button" class="close" aria-label="Close">✕</button>
</dialog>
<script>
const toastEl = document.getElementById('toast');
let toastTimer;
function toast(message) {{
  toastEl.textContent = message;
  toastEl.classList.add('on');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('on'), 2000);
}}
/** Copy `text`, then say so in a toast. */
function copyText(text, message) {{
  (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
    .catch(() => {{
      const t = Object.assign(document.createElement('textarea'), {{ value: text }});
      document.body.append(t);
      t.select();
      document.execCommand('copy');
      t.remove();
    }})
    .finally(() => toast(message));
}}
function copyAddress(b) {{
  b.previousElementSibling.select();
  copyText(b.previousElementSibling.value, 'Address copied');
}}
// Each collection: copy its link, or share it (where the system share sheet exists).
const pageUrl = location.href.split('#')[0];
if (navigator.share) for (const b of document.querySelectorAll('button.share')) b.hidden = false;
document.querySelector('main').addEventListener('click', (e) => {{
  const b = e.target.closest('button[data-act]');
  if (!b) return;
  const s = b.closest('section');
  const url = `${{pageUrl}}#${{s.id}}`;
  if (b.dataset.act === 'copy') copyText(url, 'Link copied');
  else navigator.share({{ title: s.querySelector('h2').firstChild.textContent.trim(), url }}).catch(() => {{}});
}});
// The address follows the collection being looked at (replaced, so Back isn't filled with them),
// and the sidebar marks it.
const main = document.querySelector('main');
const sections = [...main.querySelectorAll('section')];
let current = location.hash.slice(1);
function follow() {{
  const y = main.scrollTop + 48;
  const s = sections.filter((x) => x.offsetTop <= y).pop();
  const id = s ? s.id : 'top';
  if (id === current) return;
  current = id;
  history.replaceState(null, '', '#' + id);
  for (const a of document.querySelectorAll('aside nav a'))
    a.toggleAttribute('aria-current', a.getAttribute('href') === '#' + id);
}}
let ticking = false;
main.addEventListener('scroll', () => {{
  if (!ticking) requestAnimationFrame(() => {{ follow(); ticking = false; }});
  ticking = true;
}});
// Phones: the collections list opens from the menu button, and closes on picking one.
const aside = document.querySelector('aside');
const menu = aside.querySelector('.menu');
menu.addEventListener('click', () => {{
  menu.setAttribute('aria-expanded', String(aside.classList.toggle('open')));
}});
function closeMenu() {{
  aside.classList.remove('open');
  menu.setAttribute('aria-expanded', 'false');
}}
aside.querySelector('nav').addEventListener('click', (e) => {{
  if (e.target.closest('a')) closeMenu();
}});
document.addEventListener('click', (e) => {{
  if (aside.classList.contains('open') && !aside.contains(e.target)) closeMenu();
}});
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
