#!/usr/bin/env -S uv run
"""Check the library: index and pack documents well-formed, every image present and matching its
hash, paths inside the repository, format versions current. Exit code 1 on problems."""
import re, sys
from pathlib import Path
from common import FORMATS, ROOT, read_json, sha256

problems = []


def check(cond, msg):
    if not cond:
        problems.append(msg)
    return cond


def main():
    index = read_json(ROOT / 'library.json')
    if not check(index, 'library.json is missing (run tools/build.py)'):
        return
    check(index.get('format') == 'rrqlib-index', 'library.json: format must be "rrqlib-index"')
    check(index.get('version') == FORMATS['rrqlib-index'], 'library.json: version is not current (tools/upgrade.py)')
    for key in ('id', 'name', 'license', 'author', 'packs'):
        check(key in index, f'library.json: missing "{key}"')
    lk = index.get('links') or {}
    for name, url in [('homepage', lk.get('homepage')), ('gallery', lk.get('gallery'))] + [
            (o.get('name', '?'), o.get('url')) for o in lk.get('others', [])]:
        if url is not None:
            check(isinstance(url, str) and re.match(r'https?://', url), f'library.json: links: {name} is not a web address')
    for p in index.get('packs', []):
        path = p.get('path', '')
        if not check(path and '..' not in path and not path.startswith('/'), f'{p.get("id")}: bad path'):
            continue
        doc = read_json(ROOT / path)
        if not check(doc, f'{path}: missing'):
            continue
        check(doc.get('format') == 'rrqlib' and doc.get('kind') == 'pack', f'{path}: not a pack document')
        check(doc.get('version') == FORMATS['rrqlib'], f'{path}: version is not current (tools/upgrade.py)')
        check(doc.get('author', {}).get('name') and doc.get('license'), f'{path}: needs author and license')
        base = (ROOT / path).parent
        for item in doc.get('items', []):
            if item.get('type') == 'block':
                d = item.get('data', {})
                check(d.get('id') and d.get('author') and d.get('license'), f'{path}: block {d.get("id")}: needs id, author and license')
            for f in item.get('data', {}).get('fabrics', []) or []:
                for s in f.get('sizes', []):
                    rel = s.get('path', '')
                    if not check(rel and '..' not in rel, f'{path}: {f["id"]}: bad image path'):
                        continue
                    img = base / rel
                    if check(img.exists(), f'{path}: {rel} missing'):
                        check(sha256(img.read_bytes()) == s.get('sha256'), f'{path}: {rel} hash mismatch')
    if problems:
        print('\n'.join(problems))
        sys.exit(1)
    print(f'OK: {len(index["packs"])} packs')


if __name__ == '__main__':
    main()
