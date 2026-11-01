"""Portable validation. Browser/Windows checks are explicitly separate."""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def source_checks():
    manifest = json.loads((ROOT/'cloud/UI-MANIFEST.json').read_text())
    for name in ('index.html', 'app.js'):
        if hashlib.sha256((ROOT/'cloud/web'/name).read_bytes()).hexdigest() != manifest[name]:
            raise SystemExit('UI manifest mismatch: '+name)
    if (ROOT/'cloud/dvr_actions.py').read_bytes() != (ROOT/'dvr/dvr_actions.py').read_bytes():
        raise SystemExit('Backend/DVR action catalogs differ')
    paths = subprocess.check_output(['git', 'ls-files'], cwd=ROOT, text=True).splitlines()
    patterns = [re.compile(r'AKIA[A-Z0-9]{16}'), re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{24,}'),
                re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----')]
    for name in paths:
        path = ROOT/name
        if not path.is_file():
            continue
        if path.suffix in ('.sqlite', '.sqlite3', '.db', '.pem', '.pfx', '.p12') or path.name in ('administrator-token.txt', 'email-alerts.json', 'cloud-agent.json', 'server.json', 'config.json'):
            raise SystemExit('Private/runtime file is tracked: '+name)
        text = path.read_text(encoding='utf-8')
        if any(p.search(text) for p in patterns):
            raise SystemExit('Possible credential in tracked file: '+name)
    print('Manifest, action catalog and tracked-source credential checks passed.', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    source_checks()
    if args.source_only:
        return
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True)
    subprocess.run(['node', '--check', 'cloud/web/app.js'], cwd=ROOT, check=True)
    subprocess.run(['node', 'tests/test_connector_ui.js'], cwd=ROOT, check=True)
    if args.browser:
        subprocess.run(['node', 'tests/test_dashboard_browser.js'], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
