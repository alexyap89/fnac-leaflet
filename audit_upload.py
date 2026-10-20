#!/usr/bin/env python3
"""Audit the uploaded folder against the local stage, file by file."""
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SRC = '/tmp/fnac_upload'
ROOT = '1ZazGhen6MJnuBa8cuuqKUvNV5DQoMaL0'
FOLDER = 'application/vnd.google-apps.folder'

creds = Credentials.from_authorized_user_file('/home/alex/.hermes/google_token.json')
svc = build('drive', 'v3', credentials=creds)


def list_all(parent):
    out, token = [], None
    while True:
        r = svc.files().list(
            q="'%s' in parents and trashed=false" % parent,
            fields='nextPageToken,files(id,name,mimeType,size)',
            pageSize=500, pageToken=token).execute()
        out += r.get('files', [])
        token = r.get('nextPageToken')
        if not token:
            return out


def walk(pid, prefix=''):
    """Return {relative_path: (id, size)} for every file, recursing folders."""
    files, dirs = {}, {}
    for f in list_all(pid):
        p = prefix + f['name']
        if f['mimeType'] == FOLDER:
            dirs[p] = f['id']
        else:
            files[p] = (f['id'], int(f.get('size', 0)))
    for d, did in dirs.items():
        files.update(walk(did, d + '/'))
    return files


remote = walk(ROOT)

local = {}
for dp, dn, fn in os.walk(SRC):
    for f in fn:
        if f.endswith('.pyc'):
            continue
        full = os.path.join(dp, f)
        rel = os.path.relpath(full, SRC)
        local[rel] = os.path.getsize(full)

print('remote files: %d    local files: %d' % (len(remote), len(local)))
print()

missing = sorted(set(local) - set(remote))
extra = sorted(set(remote) - set(local))
size_mismatch = []
for p in sorted(set(local) & set(remote)):
    rs = remote[p][1]
    if rs and rs != local[p]:
        size_mismatch.append((p, local[p], rs))

print('MISSING on Drive (%d):' % len(missing))
for m in missing:
    print('   ', m)
print()
print('EXTRA on Drive (%d):' % len(extra))
for e in extra:
    print('   ', e)
print()
print('SIZE MISMATCH (%d):' % len(size_mismatch))
for p, ls, rs in size_mismatch:
    print('    %-40s local %d  remote %d' % (p, ls, rs))

print()
print('audio/ on Drive:')
for p in sorted(remote):
    if p.startswith('audio/'):
        print('    %-46s %d bytes' % (p, remote[p][1]))
