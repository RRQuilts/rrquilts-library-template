#!/usr/bin/env -S uv run
"""Build the library from `sources/`: each folder is a pack holding one palette of its images.

    uv run tools/build.py                # build new or changed packs
    uv run tools/build.py --rebuild      # rebuild every pack
    uv run tools/build.py --note "Added Spring 2027"   # changelog note for this revision

A folder may hold `pack.json` (name, designer, tags, size_inches, crop). Images (JPEG, PNG, WebP)
are cropped to a centred square (unless crop is false) and saved as WebP at 256/512/1024 px, never
enlarged. Writes `packs/<pack>/rrqlib.json`, the images beside it, and `library.json`.
"""
import argparse, datetime, io, sys
from PIL import Image, ImageStat
from common import FORMATS, ROOT, SIZES, name_from_file, read_json, sha256, slug, write_json


def webp(im, px):
    w, h = im.size
    k = min(1, px / max(w, h))
    out = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS) if k < 1 else im
    buf = io.BytesIO()
    out.save(buf, 'WEBP', quality=80, method=6)
    return buf.getvalue(), out.size


def build_pack(cfg, folder, old):
    meta = read_json(folder / 'pack.json', {})
    name = meta.get('name') or folder.name.replace('-', ' ').title()
    designer = meta.get('designer') or cfg['author']['name']
    inches = meta.get('size_inches') or cfg.get('default_size_inches') or 8
    approximate = not (meta.get('size_inches') or cfg.get('default_size_inches'))
    lib, pack_id = cfg['id'], f"{cfg['id']}-{slug(folder.name, 120)}"
    pdir = ROOT / 'packs' / pack_id
    fabrics, ids, preview = [], set(), []
    sizes_bytes = {str(s): 0 for s in SIZES}
    for f in sorted(folder.iterdir()):
        if f.suffix.lower() not in ('.jpg', '.jpeg', '.png', '.webp'):
            continue
        try:
            im = Image.open(f).convert('RGB')
        except Exception:
            print(f'    ! unreadable: {f.name}')
            continue
        if meta.get('crop', True):
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))
        fname, sku = name_from_file(f.name)
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
            rel = f'{real}/{slug(sku or fname, 80)}.webp'
            (pdir / str(real)).mkdir(parents=True, exist_ok=True)
            (pdir / rel).write_bytes(data)
            images.append({'px': real, 'sha256': sha256(data), 'type': 'image/webp', 'width': iw, 'height': ih, 'path': rel})
            sizes_bytes['256' if real <= 256 else '512' if real <= 512 else '1024'] += len(data)
        avg = [round(c) for c in ImageStat.Stat(im.resize((64, 64), Image.BOX)).mean]
        w, h = im.size
        main = [i for i in images if i['px'] <= 512][-1]
        fabrics.append({
            'id': fid, 'notecard': {'name': fname}, 'author': designer, 'license': cfg['license'],
            'image': {k: main[k] for k in ('sha256', 'type', 'width', 'height')},
            'size': [inches, round(inches * h / w, 2)],
            **({'approximate': True} if approximate else {}),
            'average': avg, **({'sku': sku} if sku else {}), 'sizes': images,
        })
        preview.append({'id': fid, 'name': fname, 'average': avg})
    if not fabrics:
        return None
    revision = (old or {}).get('revision', 0) + 1
    doc = {
        'format': 'rrqlib', 'version': FORMATS['rrqlib'], 'units': 'in', 'kind': 'pack',
        'id': pack_id, 'revision': revision, 'name': name, 'description': cfg.get('description', ''),
        'author': {'name': designer}, 'license': cfg['license'], 'categories': [],
        'library': {'id': lib, 'name': cfg['name']},
        'items': [{'type': 'colors', 'data': {
            'id': f'{lib}.{slug(folder.name, 58)}', 'author': designer, 'license': cfg['license'],
            'notecard': {'name': name, **({'tags': meta['tags']} if meta.get('tags') else {})},
            'colors': [], 'fabrics': fabrics}}],
    }
    write_json(pdir / 'rrqlib.json', doc)
    return {'id': pack_id, 'name': name, 'kind': 'palettes', 'path': f'packs/{pack_id}/rrqlib.json',
            'items': len(fabrics), 'revision': revision, 'sizes': sizes_bytes, 'fabrics': preview}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--rebuild', action='store_true')
    ap.add_argument('--note', help='changelog note for this revision')
    a = ap.parse_args()
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
            packs[pack_id] = entry
            changed = True
            print(f'  + {folder.name} ({entry["items"]} fabrics)')
    revision = index.get('revision', 0) + (1 if changed else 0)
    changelog = index.get('changelog', [])
    if changed and a.note:
        changelog.append({'revision': revision, 'date': datetime.date.today().isoformat(), 'notes': a.note})
    write_json(ROOT / 'library.json', {
        'format': 'rrqlib-index', 'version': FORMATS['rrqlib-index'],
        'id': cfg['id'], 'name': cfg['name'], 'description': cfg.get('description', ''),
        'author': cfg['author'], 'license': cfg['license'], 'revision': max(revision, 1),
        'changelog': changelog, 'packs': sorted(packs.values(), key=lambda p: p['name']),
    })
    print(f'library.json: revision {max(revision, 1)}, {len(packs)} packs')


if __name__ == '__main__':
    main()
