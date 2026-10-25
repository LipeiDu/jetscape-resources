#!/usr/bin/env python3
"""Check reader links; optionally request external URLs without authentication."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {'.git', '.venv', '.cache', 'outputs', '__pycache__', '.ipynb_checkpoints'}
MARKDOWN = re.compile(r'!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+["\'][^\n]*?["\'])?\s*\)')
HTML = re.compile(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', re.I)
URL = re.compile(r'https?://[^\s<>"\'`\\]+')


def links(path):
    text = path.read_text()
    if path.suffix == '.ipynb':
        notebook = json.loads(text)
        parts = []
        for cell in notebook['cells']:
            if cell['cell_type'] == 'markdown':
                parts.append(''.join(cell['source']))
            for output in cell.get('outputs', []):
                for mime, value in output.get('data', {}).items():
                    if mime in ('text/html', 'text/markdown'):
                        parts.append(''.join(value))
        text = '\n'.join(parts)
    if path.suffix in ('.md', '.ipynb'):
        found = [a or b for a, b in MARKDOWN.findall(text)] + HTML.findall(text)
        found += [u.rstrip('.,;)') for u in URL.findall(text)]
        return set(found)
    # JSON source catalogs also carry outward links, not only prose files.
    def walk(value):
        if isinstance(value, str):
            yield from (u.rstrip('.,;)') for u in URL.findall(value))
        elif isinstance(value, dict):
            for item in value.values():
                yield from walk(item)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)
    return set(walk(json.loads(text)))


def external(url):
    # GitHub clone endpoints have browser-readable repository equivalents.
    checked = url[:-4] if url.startswith('https://github.com/') and url.endswith('.git') else url
    try:
        request = Request(checked, headers={'User-Agent': 'jetscape-resources-link-check/1.0'})
        with urlopen(request, timeout=30) as response:
            response.read(1)
            return {'url': url, 'checked_url': checked, 'status': response.status, 'ok': True}
    except Exception as error:
        return {'url': url, 'checked_url': checked, 'ok': False, 'error': str(error)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--external', action='store_true', help='Also request public URLs without cookies or credentials')
    parser.add_argument('--report', type=Path, help='Optional JSON report (put generated reports in outputs/)')
    args = parser.parse_args()
    failures, outward = [], set()
    local_count = 0
    for path in sorted(ROOT.rglob('*')):
        if set(path.relative_to(ROOT).parts) & IGNORED or path.suffix not in ('.md', '.ipynb', '.json'):
            continue
        for target in links(path):
            parsed = urlsplit(target)
            if parsed.scheme in ('https', 'http'):
                outward.add(target)
            elif parsed.scheme or parsed.netloc:
                failures.append(f'{path.relative_to(ROOT)}: unsupported link {target}')
            else:
                resolved = (path.parent / unquote(parsed.path)).resolve()
                local_count += 1
                if not resolved.is_relative_to(ROOT) or not resolved.exists():
                    failures.append(f'{path.relative_to(ROOT)}: missing or outside export: {target}')
    results = []
    if args.external:
        with ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(external, sorted(outward)))
        failures += [f'{r["url"]}: {r["error"]}' for r in results if not r['ok']]
    report = {'local_links': local_count, 'external_urls': len(outward), 'external_checks': results, 'failures': failures}
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{local_count} local links; {len(outward)} external URLs; {len(failures)} unresolved checks')
    for failure in failures:
        print(failure)
    if failures:
        print('An HTTP failure can reflect throttling or a server restriction; verify it separately before concluding a resource is unavailable.')
    return bool(failures)


if __name__ == '__main__':
    sys.exit(main())
