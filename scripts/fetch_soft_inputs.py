#!/usr/bin/env python3
"""Download only the four pinned public inputs, checking SHA-256; or use a matching local source."""
import argparse
from pathlib import Path
import json
import shutil
import urllib.request
from inference_tools import sha256

ROOT = Path(__file__).resolve().parents[1]

def fetch(cache, source=None):
    manifest = json.loads((ROOT/'soft/upstream_manifest.json').read_text())
    cache = Path(cache)
    for item in manifest['files']:
        relative = Path(item['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path')
        output = cache/relative
        if output.exists():
            if sha256(output) != item['sha256']:
                raise ValueError('Existing cached bytes differ: '+str(output))
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        temporary = output.with_suffix(output.suffix+'.partial')
        try:
            if source is not None:
                shutil.copyfile(Path(source)/relative, temporary)
            else:
                with urllib.request.urlopen(item['url'], timeout=60) as response, temporary.open('wb') as target:
                    shutil.copyfileobj(response, target)
            if temporary.stat().st_size != item['bytes'] or sha256(temporary) != item['sha256']:
                raise ValueError('Downloaded bytes fail size/hash check: '+str(relative))
            temporary.replace(output)
        finally:
            if temporary.exists(): temporary.unlink()
    return manifest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, default=ROOT/'.cache/soft-sector')
    parser.add_argument('--from-source', type=Path, help='Matching local public repository or downloaded mirror')
    args = parser.parse_args()
    result = fetch(args.cache, args.from_source)
    print('Verified %d files at upstream commit %s in %s' % (len(result['files']), result['commit'], args.cache))
