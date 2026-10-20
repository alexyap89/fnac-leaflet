#!/usr/bin/env python3
"""Upload the REMAINDER of the FNAC project folder to Drive.

Additive only - nothing local is touched. Mirrors the whole source tree into the
already-populated Drive folder, skipping only files that are already there with a
matching size, so a re-run costs nothing.

Dest: My Drive / 20_Projects / Radiology / 01-Active / FNAC Webapp
"""
import os
import mimetypes

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SRC = '/home/alex/Documents/FNAC_Webapp'
ROOT = '1ZazGhen6MJnuBa8cuuqKUvNV5DQoMaL0'      # FNAC Webapp on Drive
FOLDER = 'application/vnd.google-apps.folder'
SKIP_DIRS = {'node_modules', '__pycache__', '.git'}

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


def remote_map(pid, prefix=''):
    files, dirs = {}, {}
    for f in list_all(pid):
        p = prefix + f['name']
        if f['mimeType'] == FOLDER:
            dirs[p] = f['id']
        else:
            files[p] = (f['id'], int(f.get('size', 0)))
    for d, did in dirs.items():
        files.update(remote_map(did, d + '/'))
    return files


def find_child(parent, name, mime=None):
    q = "'%s' in parents and name=%r and trashed=false" % (parent, name)
    if mime:
        q += " and mimeType='%s'" % mime
    r = svc.files().list(q=q, fields='files(id,name)').execute().get('files', [])
    return r[0] if r else None


def ensure_folder(parent, name):
    hit = find_child(parent, name, FOLDER)
    if hit:
        return hit['id']
    return svc.files().create(
        body={'name': name, 'mimeType': FOLDER, 'parents': [parent]},
        fields='id').execute()['id']


print('indexing Drive...')
remote = remote_map(ROOT)
print('  %d files already on Drive' % len(remote))

created = skipped = failed = 0
errors = []
folder_ids = {'': ROOT}

# create the folder skeleton first
for dp, dn, fn in os.walk(SRC):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    rel = os.path.relpath(dp, SRC)
    rel = '' if rel == '.' else rel
    parent = folder_ids.setdefault(rel, ROOT)
    if rel:
        parent = ensure_folder(folder_ids.get(os.path.dirname(rel), ROOT),
                               os.path.basename(rel))
        folder_ids[rel] = parent
    for d in sorted(dn):
        sub = os.path.join(rel, d) if rel else d
        folder_ids[sub] = ensure_folder(parent, d)

# then upload the files
for dp, dn, fn in os.walk(SRC):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    rel = os.path.relpath(dp, SRC)
    rel = '' if rel == '.' else rel
    parent = folder_ids.get(rel, ROOT)
    for name in sorted(fn):
        local = os.path.join(dp, name)
        relpath = os.path.join(rel, name) if rel else name
        try:
            size = os.path.getsize(local)
        except OSError:
            continue
        hit = remote.get(relpath)
        if hit and hit[1] == size:
            skipped += 1
            continue
        mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        media = MediaFileUpload(local, mimetype=mime, resumable=False)
        try:
            if hit:                                  # size differs -> replace
                svc.files().update(fileId=hit[0], media_body=media).execute()
            else:
                svc.files().create(
                    body={'name': name, 'parents': [parent]},
                    media_body=media, fields='id').execute()
            created += 1
        except Exception as e:
            failed += 1
            errors.append('%s: %s' % (relpath, str(e)[:120]))

print()
print('uploaded : %d' % created)
print('skipped  : %d  (already present, same size)' % skipped)
print('failed   : %d' % failed)
for e in errors[:15]:
    print('   ', e)

# ---- verify ---------------------------------------------------------------
after = remote_map(ROOT)
local_files = {}
for dp, dn, fn in os.walk(SRC):
    dn[:] = [d for d in dn if d not in SKIP_DIRS]
    for f in fn:
        full = os.path.join(dp, f)
        local_files[os.path.relpath(full, SRC)] = os.path.getsize(full)

missing = sorted(set(local_files) - set(after))
mismatch = [p for p in set(local_files) & set(after)
            if after[p][1] and after[p][1] != local_files[p]]

print()
print('VERIFY')
print('  local files      : %d' % len(local_files))
print('  Drive files      : %d' % len(after))
print('  missing on Drive : %d' % len(missing))
for m in missing[:15]:
    print('      ', m)
print('  size mismatches  : %d' % len(mismatch))
for m in mismatch[:10]:
    print('      ', m, local_files[m], 'vs', after[m][1])
print('  folder           : https://drive.google.com/drive/folders/%s' % ROOT)
