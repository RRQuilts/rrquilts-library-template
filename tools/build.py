#!/usr/bin/env -S uv run
"""Build the library from `sources/`: each folder is a pack holding one palette of its images.

    uv run tools/build.py                # build new or changed packs
    uv run tools/build.py --rebuild      # rebuild every pack
    uv run tools/build.py --note "Added Spring 2027"   # changelog note for this revision
    uv run tools/build.py --print --rebuild   # also 1024 px images, for printing

A folder may hold `pack.json` (name, designer, description, tags, size_inches, crop, and `fabrics`:
per-file overrides `{"<file>": {"name", "sku", "size": [w, h]}}`), a `palette.rrqplt` whose
colors become the pack's (a solids pack needs no images), and a `blocks.rrqlib` (a pack made in
RRQuilts, Libraries › Make a pack) whose blocks and their categories join the pack. Images (JPEG, PNG, WebP)
are cropped to a centred square (unless crop is false) and saved as WebP at 256 and 512 px (and 1024 px
with --print: about three times the size, used only when printing), never enlarged. Writes `packs/<pack>/rrqlib.json`, the images beside it, and `library.json`.
"""
import argparse, datetime, io, shutil, sys
from PIL import Image, ImageStat

Image.MAX_IMAGE_PIXELS = 300_000_000  # manufacturers' photos can be print resolution
from common import FORMATS, ROOT, SIZES, name_from_file, read_json, sha256, slug, write_json


def webp(im, px):
    w, h = im.size
    k = min(1, px / max(w, h))
    out = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS) if k < 1 else im
    buf = io.BytesIO()
    out.save(buf, 'WEBP', quality=80, method=6)
    return buf.getvalue(), out.size



def contents_of(fabrics, colors=()):
    """What a pack's update would change: its fabrics (names, images) and colors (names, values)."""
    return (sorted((f['id'], f['notecard']['name'], tuple(i['sha256'] for i in f.get('sizes', [])))
                   for f in fabrics),
            sorted((c['id'], c['notecard']['name'], tuple(c['rgb'])) for c in colors))


def contents(doc):
    if not doc:
        return None
    pal = [it['data'] for it in doc['items'] if it['type'] == 'colors']
    blocks = sorted((it['data']['id'], it['data'].get('version', '')) for it in doc['items'] if it['type'] == 'block')
    return contents_of([f for d in pal for f in d.get('fabrics', [])], [c for d in pal for c in d.get('colors', [])]), blocks


def exported(path, fmt):
    """A file exported from RRQuilts (`palette.rrqplt`, `blocks.rrqlib`), or None. Its items go into the
    pack as they are, so one from a newer RRQuilts than these tools is refused (its fields could be
    lost or mislabeled); an older one is used, with a warning to export it again."""
    doc = read_json(path, None)
    if doc is None:
        return None
    rel = path.relative_to(ROOT)
    if doc.get('format') != fmt or not isinstance(doc.get('version'), int):
        sys.exit(f'{rel}: not an RRQuilts {fmt} file.')
    if doc['version'] > FORMATS[fmt]:
        sys.exit(f'{rel}: made by a newer RRQuilts ({fmt} {doc["version"]}; these tools know {FORMATS[fmt]}). '
                 'Run `uv run tools/upgrade.py` first.')
    if doc['version'] < FORMATS[fmt]:
        print(f'    ! {rel}: {fmt} {doc["version"]} is older than {FORMATS[fmt]}; used as is. '
              'Export it again from RRQuilts to bring it up to date.')
    return doc


def links(cfg):
    """The library's web pages (config `links`: homepage, gallery, others), for its documents."""
    return {'links': cfg['links']} if cfg.get('links') else {}


def relink(cfg, path):
    """An unchanged pack takes the library's current links (no rebuild, no new revision)."""
    doc = read_json(path)
    if doc.get('links') != cfg.get('links'):
        doc.pop('links', None)
        write_json(path, {**doc, **links(cfg)})


def build_pack(cfg, folder, listed):
    meta = read_json(folder / 'pack.json', {})
    name = meta.get('name') or folder.name.replace('-', ' ').title()
    designer = meta.get('designer') or cfg['author']['name']
    inches = meta.get('size_inches') or cfg.get('default_size_inches') or 8
    approximate = not (meta.get('size_inches') or cfg.get('default_size_inches'))
    lib, pack_id = cfg['id'], f"{cfg['id']}-{slug(folder.name, 120)}"
    pdir = ROOT / 'packs' / pack_id
    # RRQuilts exports first: a refused one stops the build before the earlier one is removed.
    plt = exported(folder / 'palette.rrqplt', 'rrqplt')
    made = exported(folder / 'blocks.rrqlib', 'rrqlib') or {}
    old = read_json(pdir / 'rrqlib.json', None)  # the earlier build, for its revision and contents
    shutil.rmtree(pdir, ignore_errors=True)  # no images left from an earlier build
    fabrics, ids, preview = [], set(), []
    sizes_bytes = {str(s): 0 for s in SIZES}
    maker = cfg.get('manufacturer')
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        try:
            im = Image.open(f).convert('RGB')
        except Exception:
            print(f'    ! unreadable: {f.name}')
            continue
        im.thumbnail((2048, 2048))  # plenty for the largest image (1024 px), and quick
        over = meta.get('fabrics', {}).get(f.name, {})
        if meta.get('crop', True):
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        fname, sku = name_from_file(f.name)
        fname, sku = over.get('name', fname), over.get('sku', sku)
        fid, n = f'{lib}.{slug(sku or fname)}', 2
        while fid in ids:
            fid, n = f'{lib}.{slug(sku or fname, 58)}-{n}', n + 1
        ids.add(fid)
        images = []
        for px in SIZES:
            data, (iw, ih) = webp(im, px)
            if images and images[-1]['width'] == iw:
                continue
            real = max(iw, ih)
            rel = f"{real}/{fid.split('.', 1)[1]}.webp"
            (pdir / str(real)).mkdir(parents=True, exist_ok=True)
            (pdir / rel).write_bytes(data)
            images.append({'px': real, 'sha256': sha256(data), 'type': 'image/webp', 'width': iw, 'height': ih, 'path': rel})
            sizes_bytes[str(min(s for s in SIZES if real <= s))] += len(data)
        avg = [round(c) for c in ImageStat.Stat(im.resize((64, 64), Image.BOX)).mean]
        w, h = im.size
        main = [i for i in images if i['px'] <= 512][-1]
        fabrics.append({
            'id': fid,
            'notecard': {'name': fname, **({'reference': f'{maker} {sku}'} if maker and sku else {})},
            'author': designer, 'license': cfg['license'],
            'image': {k: main[k] for k in ('sha256', 'type', 'width', 'height')},
            'size': over.get('size') or [inches, round(inches * h / w, 2)],
            **({'approximate': True} if approximate else {}),
            'average': avg, **({'manufacturer': maker} if maker else {}),
            **({'sku': sku} if sku else {}), 'sizes': images,
        })
        preview.append({'id': fid, 'name': fname, 'average': avg})
    colors = plt['collection']['colors'] if plt else []
    # ponytail: blocks only; fabric images inside blocks aren't copied out yet (paint blocks with colors)
    block_items = [it for it in made.get('items', []) if it.get('type') == 'block']
    used = {it.get('category') for it in block_items}
    categories = [c for c in made.get('categories', []) if c.get('id') in used]
    if not fabrics and not colors and not block_items:
        return None
    # A pack whose fabrics or images change gets the next revision, so apps download it again.
    # Without the earlier build, go on from the revision library.json lists.
    base = (old or listed or {}).get('revision', 0)
    palette = [{'type': 'colors', 'data': {
        'id': f'{lib}.{slug(folder.name, 58)}', 'author': designer, 'license': cfg['license'],
        'notecard': {'name': name, **({'tags': meta['tags']} if meta.get('tags') else {})},
        'colors': colors, 'fabrics': fabrics}}] if fabrics or colors else []
    new = {'items': palette + block_items}
    revision = base + (1 if old is None or contents(old) != contents(new) else 0)
    doc = {
        'format': 'rrqlib', 'version': FORMATS['rrqlib'], 'units': 'in', 'kind': 'pack',
        'id': pack_id, 'revision': revision, 'name': name,
        'description': meta.get('description') or cfg.get('description', ''),
        'author': {'name': designer}, 'license': cfg['license'], **links(cfg), 'categories': categories,
        'library': {'id': lib, 'name': cfg['name']},
        'items': new['items'],
    }
    write_json(pdir / 'rrqlib.json', doc)
    return {'id': pack_id, 'name': name, 'kind': 'palettes' if palette else 'blocks',
            'path': f'packs/{pack_id}/rrqlib.json',
            'items': len(fabrics) or len(colors) or len(block_items), 'revision': revision, 'sizes': sizes_bytes, 'fabrics': preview}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--note', help='changelog note for this revision')
    ap.add_argument('--print', action='store_true', help='also make 1024 px images (for printing)')
    a = ap.parse_args()
    global SIZES
    SIZES = (256, 512, 1024) if a.print else (256, 512)
    cfg = read_json(ROOT / 'library.config.json')
    if not cfg:
        sys.exit('library.config.json is missing.')
    index = read_json(ROOT / 'library.json', {}) or {}
    packs = {p['id']: p for p in index.get('packs', [])}
    changed = False
    for folder in sorted(p for p in (ROOT / 'sources').iterdir() if p.is_dir()):
        pack_id = f"{cfg['id']}-{slug(folder.name, 120)}"
        newest = max((f.stat().st_mtime for f in folder.iterdir()), default=0)
        built = ROOT / 'packs' / pack_id / 'rrqlib.json'
        if pack_id in packs and built.exists() and built.stat().st_mtime >= newest and not a.rebuild:
            print(f'  = {folder.name}')
            continue
        entry = build_pack(cfg, folder, packs.get(pack_id))
        if entry:
            changed |= entry['revision'] != packs.get(pack_id, {}).get('revision')
            packs[pack_id] = entry
            print(f'  + {folder.name} ({entry["items"]} items)')
    for p in packs.values():  # every pack, built now or not, names the library's current pages
        if (ROOT / p['path']).exists():
            relink(cfg, ROOT / p['path'])
    revision = index.get('revision', 0) + (1 if changed else 0)
    changelog = index.get('changelog', [])
    if changed and a.note:
        changelog.append({'revision': revision, 'date': datetime.date.today().isoformat(), 'notes': a.note})
    write_json(ROOT / 'library.json', {
        'format': 'rrqlib-index', 'version': FORMATS['rrqlib-index'],
        'id': cfg['id'], 'name': cfg['name'], 'description': cfg.get('description', ''),
        'author': cfg['author'], 'license': cfg['license'], **links(cfg), 'revision': max(revision, 1),
        'changelog': changelog, 'packs': sorted(packs.values(), key=lambda p: p['name']),
    })
    print(f'library.json: revision {max(revision, 1)}, {len(packs)} packs')


if __name__ == '__main__':
    main()
