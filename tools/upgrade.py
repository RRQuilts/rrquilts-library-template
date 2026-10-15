#!/usr/bin/env -S uv run
"""Keep the library current with RRQuilts.

    uv run tools/upgrade.py --check   # exit 1 (with a message) if RRQuilts has newer formats
    uv run tools/upgrade.py           # refresh tools/ from the template, then rebuild every pack

New format versions so far only add fields, so upgrading is: fetch the latest tools (which write
the new versions) and rebuild. Migrations that change fields will be added to these tools.
"""
import argparse, json, subprocess, sys, urllib.request
from common import FORMATS, ROOT, TEMPLATE_RAW, FORMATS_URL

TOOLS = ['common.py', 'build.py', 'validate.py', 'release.py', 'upgrade.py']


def latest():
    with urllib.request.urlopen(FORMATS_URL, timeout=30) as r:
        return json.loads(r.read())


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    newest = latest()
    behind = {k: (v, newest[k]) for k, v in FORMATS.items() if newest.get(k, v) > v}
    if a.check:
        if behind:
            print('RRQuilts has newer library formats: ' + ', '.join(f'{k} {v} → {n}' for k, (v, n) in behind.items())
                  + '. Run `uv run tools/upgrade.py` and commit.')
            sys.exit(1)
        print('Library formats are current.')
        return
    for t in TOOLS:
        with urllib.request.urlopen(TEMPLATE_RAW + 'tools/' + t, timeout=30) as r:
            (ROOT / 'tools' / t).write_bytes(r.read())
    print('Tools refreshed; rebuilding…')
    subprocess.run([sys.executable, str(ROOT / 'tools' / 'build.py'), '--rebuild', '--note', 'Upgraded to the current RRQuilts formats.'], check=True)


if __name__ == '__main__':
    main()
