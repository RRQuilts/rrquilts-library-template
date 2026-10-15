#!/usr/bin/env -S uv run
"""Build `.rrqlib` files into dist/: the whole library, per image size —
<name>-256 (Light), <name>-512 (Standard, includes 256), and <name>-1024 (Print) when the library
was built with 1024 px images (build.py --print). Import them in
RRQuilts › Libraries › Import."""
import re, zipfile
from common import ROOT, read_json, repo_url, slug, write_json

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
    # The index inside names the repository, so RRQuilts can connect a downloaded file to it.
    repo = repo_url()
    index_file = dist / '.library.json'
    write_json(index_file, {**index, **({'repository': repo} if repo else {})})
    large = any(d.name.isdigit() and int(d.name) > 512 for d in (ROOT / 'packs').glob('*/*'))
    for size, keep in KEEP.items():
        if size == '1024' and not large:
            continue
        files = [('library.json', index_file)]
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
    index_file.unlink()
    print('\n'.join(sorted(f.name for f in dist.glob('*.rrqlib'))))


if __name__ == '__main__':
    main()
