"""Fetch entries newer than the last digest from the configured Miniflux feeds.

Usage: fetch_entries.py STATE_FILE OUT_DIR

Writes OUT_DIR/entries.json (for the recipe) and OUT_DIR/last-entry-id (for the
wrapper to save once the EPUB is in Calibre), and prints the entry count.
Read/unread status in Miniflux is ignored and never changed.
"""
import json
import os
import re
import sys
import time
from urllib.request import Request, urlopen

PAGE = 100   # entries asked per feed

base = os.environ['MINIFLUX_URL']
feed_ids = [f.strip() for f in os.environ.get('MINIFLUX_FEED_IDS', '').split(',') if f.strip()]
initial_days = int(os.environ.get('MINIFLUX_INITIAL_DAYS', '7'))
max_entries = int(os.environ.get('MINIFLUX_MAX_ENTRIES', '100'))
# Skip entries whose text is shorter than this, e.g. link-only posts or
# tweets the crawler could not extract. They still count as sent.
min_chars = int(os.environ.get('MINIFLUX_MIN_CHARS', '0'))
token = open(os.path.expanduser('~/.config/miniflux-token')).read().strip()
state_file, out_dir = sys.argv[1:]

try:
    last_id = int(open(state_file).read())
    since = f'after_entry_id={last_id}'
except FileNotFoundError:
    # First run: no backlog dump, only the last few days.
    since = f'after={int(time.time()) - initial_days * 86400}'

entries = []
cutoff = None
for fid in feed_ids:
    url = (f'{base}/v1/feeds/{fid}/entries?status=unread&status=read'
           f'&order=id&direction=asc&limit={PAGE}&{since}')
    page = json.load(urlopen(Request(url, headers={'X-Auth-Token': token}), timeout=30))['entries']
    entries += page
    if len(page) == PAGE:
        # This feed has more entries above its last id; anything from other
        # feeds past that id must wait too, or the saved id would skip them.
        cutoff = min(cutoff or page[-1]['id'], page[-1]['id'])

entries.sort(key=lambda e: e['id'])
entries = [e for e in entries if cutoff is None or e['id'] <= cutoff][:max_entries]

if entries:
    with open(os.path.join(out_dir, 'last-entry-id'), 'w') as f:
        f.write(str(entries[-1]['id']))
entries = [e for e in entries if len(re.sub(r'<[^>]+>', '', e['content']).strip()) >= min_chars]

with open(os.path.join(out_dir, 'entries.json'), 'w') as f:
    json.dump(entries, f)
print(len(entries))
