"""Create missing annotated provenance tags; never move an existing tag."""
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args, check=True):
    return subprocess.run(['git', *args], cwd=ROOT, text=True, capture_output=True, check=check)


def main():
    history = json.loads((ROOT/'docs/SOURCE_HISTORY.json').read_text())
    pending = []
    # Validate the entire plan before creating or pushing any tag.
    for item in history:
        original, commit, tag = item['original_commit'], item['remote_import_commit'], item['tag']
        if not re.fullmatch(r'[0-9a-f]{40}', original) or not re.fullmatch(r'[0-9a-f]{40}', commit):
            raise SystemExit('Invalid source commit identifier')
        if tag != 'source-revision/'+original[:12]:
            raise SystemExit('Unexpected source tag name')
        git('merge-base', '--is-ancestor', commit, 'HEAD')
        existing = git('rev-parse', '--verify', 'refs/tags/'+tag+'^{commit}', check=False)
        if existing.returncode == 0:
            if existing.stdout.strip() != commit:
                raise SystemExit('Existing tag differs; refusing to move '+tag)
        else:
            pending.append((original, commit, tag))
    for original, commit, tag in pending:
        git('-c', 'user.name=github-actions[bot]', '-c', 'user.email=41898282+github-actions[bot]@users.noreply.github.com',
            'tag', '-a', tag, commit, '-m', 'Authentic source snapshot from dougkling/DroneRaceTools@'+original+'; not a historical deployment certification.')
        git('push', 'origin', 'refs/tags/'+tag)
        print('Preserved '+tag)


if __name__ == '__main__':
    main()
