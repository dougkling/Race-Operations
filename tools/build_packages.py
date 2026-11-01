"""Build deterministic source/deployment ZIPs from reviewed tracked files only."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from validate import ROOT, source_checks


def build(output):
    source_checks()
    output.mkdir(parents=True, exist_ok=True)
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    files = {name: (ROOT/name).read_bytes() for name in paths if (ROOT/name).is_file()}
    groups = {
        'RaceOperations-Standalone-Source': files,
        'RaceOperations-Cloud-Source-v0.9.0': {p:b for p,b in files.items() if p.startswith(('cloud/', 'docs/')) or p=='README.md'},
        'RaceOperations-DVR-Source-v0.8.0': {p:b for p,b in files.items() if p.startswith(('dvr/', 'docs/')) or p=='README.md'},
        'RaceOperations-Dashboard-Map-v0.9.2': {p.removeprefix('cloud/'):files[p] for p in ('cloud/web/index.html','cloud/web/app.js','cloud/Update-Dashboard.ps1','cloud/UI-MANIFEST.json')},
    }
    groups['RaceOperations-Dashboard-Map-v0.9.2']['README.md']=files['docs/dashboard-map-v0.9.2.md']
    hashes = {}
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT, text=True).strip())
    for name, members in groups.items():
        archive = output/(name+'.zip')
        with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
            for path, data in sorted(members.items()):
                info = zipfile.ZipInfo(name+'/'+path, date_time=(2026,11,1,0,0,0))
                info.compress_type=zipfile.ZIP_DEFLATED
                info.external_attr=0o100644<<16
                z.writestr(info,data)
        with zipfile.ZipFile(archive) as z:
            if z.testzip():
                raise SystemExit('ZIP verification failed: '+name)
        hashes[archive.name]=hashlib.sha256(archive.read_bytes()).hexdigest()
    (output/'SHA256SUMS.json').write_text(json.dumps(hashes,indent=2)+'\n')
    (output/'BUILD.json').write_text(json.dumps({'sourceCommit': revision, 'trackedChangesPresent': dirty, 'sha256': hashes}, indent=2)+'\n')
    print(json.dumps(hashes,indent=2))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    build(parser.parse_args().output.resolve())
