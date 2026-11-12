"""Read-only fingerprint of the original blog data."""
import hashlib
import json
import sqlite3
from pathlib import Path
import sys
root = Path(__file__).resolve().parents[1]
result = {}
with sqlite3.connect(root / 'db.sqlite3') as db:
    for table in ('blog_author', 'blog_tag', 'blog_post', 'blog_post_tags', 'blog_comment'):
        digest = hashlib.sha256()
        count = 0
        for row in db.execute(f'SELECT * FROM {table} ORDER BY id'):
            digest.update(json.dumps(row, ensure_ascii=False).encode('utf-8'))
            count += 1
        result[table] = {'rows': count, 'sha256': digest.hexdigest()}
output = root / 'evidence' / sys.argv[1]
output.write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
