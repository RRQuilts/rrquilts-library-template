#!/usr/bin/env -S uv run
"""Build `.rrqlib` files into dist/: the whole library and each pack, per image size —
<name>-256 (Light), <name>-512 (Standard, includes 256), <name>-1024 (Print). Import them in
RRQuilts › Libraries › Import."""
import re, zipfile
from pathlib import Path
from common import ROOT, read_json, slug, write_json

KEEP = {'256': lambda px: px <= 256, '512': lambda px: px <= 512, '1024': lambda px: px > 512}


def zip_files(dest, files):
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_STORED) as z:
        for arc, path in files:
            z.write(path, arc)


def main():
    index = read_json(ROOT / 'library.json')
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)
    name = slug(index['name'], 80)
    for size, keep in KEEP.items():
        files = [('library.json', ROOT / 'library.json')]
        for p in index['packs']:
            pdir = (ROOT / p['path']).parent
            for f in sorted(pdir.rglob('*')):
                if not f.is_file():
                    continue
                rel = f.relative_to(ROOT).as_posix()
                m = re.match(r'packs/[^/]+/(\d+)/', rel)
                if m and not keep(int(m.group(1))):
                    continue
                files.append((rel, f))
        zip_files(dist / f'{name}-{size}.rrqlib', files)
        for p in index['packs']:  # each pack on its own: an index of just that pack
            one = dist / f'.index-{p["id"]}.json'
            write_json(one, {**index, 'packs': [p]})
            pfiles = [('library.json', one)] + [(a, f) for a, f in files if a.startswith(Path(p['path']).parent.as_posix() + '/')]
            zip_files(dist / f'{slug(p["name"], 80)}-{size}.rrqlib', pfiles)
            one.unlink()
    print('\n'.join(sorted(f.name for f in dist.glob('*.rrqlib'))))


if __name__ == '__main__':
    main()
