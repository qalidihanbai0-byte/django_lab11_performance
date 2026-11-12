"""Persist exit codes and output of the required final commands."""
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen

root = Path(__file__).resolve().parents[1]
commands = [
    [sys.executable, 'manage.py', 'check'],
    [sys.executable, 'manage.py', 'test', '--verbosity', '2'],
    [sys.executable, 'manage.py', 'makemigrations', '--check', '--dry-run'],
    [sys.executable, 'manage.py', 'verify_performance'],
    [sys.executable, 'tools/data_fingerprint.py', 'data_after.json'],
    ['git', '-c', f'safe.directory={root.as_posix()}', 'log', '--format=%h %s', '-6'],
]
output = []
for command in commands:
    result = subprocess.run(command, cwd=root, capture_output=True, encoding='utf-8',
                            env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, timeout=60)
    output.append('$ ' + ' '.join(command) + '\n' + result.stdout + result.stderr + f'\nExit code: {result.returncode}\n')
    if result.returncode:
        (root / 'evidence/final-checks.txt').write_text('\n'.join(output), encoding='utf-8')
        raise RuntimeError(command)
assert (root / 'evidence/data_before.json').read_bytes() == (root / 'evidence/data_after.json').read_bytes()
output.append('PASS: all original blog table SHA256 fingerprints match.')
for path in ('/posts/', '/stats/', '/static/blog/style.css'):
    with urlopen('http://127.0.0.1:8012' + path, timeout=30) as response:
        assert response.status == 200
        output.append(f'LIVE HTTP 200: {path}')
(root / 'evidence/final-checks.txt').write_text('\n'.join(output), encoding='utf-8')
print('PASS: check, 7 tests, migration consistency, cache, EXPLAIN, fingerprints, live HTTP, Git history.')
