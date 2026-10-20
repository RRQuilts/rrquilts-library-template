"""Shared helpers for the library tools."""
import hashlib, io, json, os, re, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SIZES = (256, 512)  # build.py --print adds 1024
FORMATS_URL = 'https://ragingroosevelt.github.io/RRQuilts/schemas/formats.json'
TEMPLATE_RAW = 'https://raw.githubusercontent.com/RRQuilts/rrquilts-library-template/main/'
# Format versions these tools write. `tools/upgrade.py` moves a library to newer ones.
FORMATS = {'rrqlib': 5, 'rrqlib-index': 1}


def slug(s, n=64):
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')[:n].strip('-') or 'x'


def read_json(p, default=None):
    return json.loads(Path(p).read_text(encoding='utf-8')) if Path(p).exists() else default


def write_json(p, data):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(data, indent=1, ensure_ascii=False) + '\n', encoding='utf-8')


def sha256(b):
    return hashlib.sha256(b).hexdigest()


def name_from_file(file):
    """"SGF-40300-Gilded-Ginko-Ice_500px.jpg" → ("Gilded Ginko Ice", "SGF-40300")."""
    base = re.sub(r'\.[a-z0-9]+$', '', file.split('/')[-1], flags=re.I)
    base = re.sub(r'[-_ ]?\d{2,4}px$', '', base, flags=re.I)
    m = re.match(r'^([A-Z]{1,6}-?\d{2,6}(?:-\d{1,4})?)(?=[-_ ]|$)', base)
    sku = m.group(1) if m else None
    rest = re.sub(r'\s+', ' ', re.sub(r'[-_]+', ' ', base[len(sku):] if sku else base)).strip()
    return (rest or sku or base), sku


def repo_url():
    """The library's repository address: library.config.json `repository` if set (for hosts other
    than GitHub), else from GitHub Actions, else the git remote; None if none of them."""
    set_by_hand = (read_json(ROOT / 'library.config.json', {}) or {}).get('repository')
    if set_by_hand:
        return set_by_hand
    if os.environ.get('GITHUB_REPOSITORY'):
        return f"{os.environ.get('GITHUB_SERVER_URL', 'https://github.com')}/{os.environ['GITHUB_REPOSITORY']}"
    try:
        url = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=ROOT, capture_output=True,
                             text=True).stdout.strip()
    except OSError:
        return None
    m = re.match(r'(?:https://github\.com/|git@github\.com:)([^/]+/[^/]+?)(?:\.git)?$', url)
    return f'https://github.com/{m.group(1)}' if m else None
