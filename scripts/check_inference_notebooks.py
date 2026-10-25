#!/usr/bin/env python3
"""Execute the two study notebooks without modifying their source files or kernel registry."""
import argparse
from pathlib import Path
import os
import json
import sys
import tempfile
import time
import nbformat
from nbclient import NotebookClient
from inference_tools import sha256

ROOT = Path(__file__).resolve().parents[1]

def execute(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = []
    with tempfile.TemporaryDirectory(prefix='jetscape-notebook-kernel-') as temporary:
        data = Path(temporary)
        kernel = data/'kernels/jetscape-resource-check'
        kernel.mkdir(parents=True)
        (kernel/'kernel.json').write_text(json.dumps({'argv':[sys.executable,'-m','ipykernel_launcher','-f','{connection_file}'],
                                                       'display_name':'Resource check','language':'python'}))
        previous = {k:os.environ.get(k) for k in ['JUPYTER_PATH','MPLBACKEND','MPLCONFIGDIR','IPYTHONDIR']}
        try:
            os.environ['JUPYTER_PATH'] = str(data)
            os.environ['MPLBACKEND'] = 'Agg'
            os.environ['MPLCONFIGDIR'] = str(data/'matplotlib')
            os.environ['IPYTHONDIR'] = str(data/'ipython')
            for path in [ROOT/'soft/soft_sector.ipynb', ROOT/'hard/hard_sector.ipynb']:
                notebook = nbformat.read(path, as_version=4)
                start = time.monotonic()
                NotebookClient(notebook, timeout=180, kernel_name='jetscape-resource-check',
                               resources={'metadata':{'path':str(path.parent)}}).execute()
                nbformat.write(notebook, output/path.name)
                report.append({'notebook':str(path.relative_to(ROOT)), 'elapsed_s':time.monotonic()-start,
                               'errors':0, 'source_sha256':sha256(path),
                               'included_soft_posterior':path.parent.name=='soft'})
                print('Executed '+str(path.relative_to(ROOT)), flush=True)
        finally:
            for key, value in previous.items():
                if value is None: os.environ.pop(key, None)
                else: os.environ[key] = value
    (output/'execution_report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'outputs/executed-notebooks')
    args = parser.parse_args()
    execute(args.output_dir)
