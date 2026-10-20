#!/usr/bin/env python3
"""Upload the staged FNAC webapp into the Radiology 01-Active project area.

Idempotent: creates the destination folder if missing, creates sub-folders, and
updates an existing file in place (by matching name+parent) rather than making a
duplicate. Verifies the result by re-listing afterwards.
"""
import os
import sys
import mimetypes

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SRC = '/tmp/fnac_upload'
DEST_NAME = 'FNAC Webapp'
# My Drive / 20_Projects / Radiology / 01-Active
ACTIVE = '11aw9c6qUUzAQB11b2iPGE5qG2rbRksnC'

creds = Credentials.from_authorized_user_file('/home/alex/.hermes/google_token.json')
svc = build('drive', 'v3', credentials=creds)

FOLDER = 'application/vnd.google-apps.folder'


def find_child(parent, name, mime=None):
    q = "'%s' in parents and name=%r and trashed=false" % (parent, name)
    if mime:
        q += " and mimeType='%s'" % mime
    r = svc.files().list(q=q, fields='files(id,name)').execute().get('files', [])
    return r[0] if r else None


def find_or_create(parent, name):
    hit = find_child(parent, name, FOLDER)
    if hit:
        return hit['id'], False
    md = svc.files().create(
        body={'name': name, 'mimeType': FOLDER, 'parents': [parent]},
        fields='id').execute()
    return md['id'], True


def upload(local, parent, name):
    """Create or update. Updates in place so re-runs do not duplicate."""
    existing = find_child(parent, name)
    mime = mimetypes.guess_type(name)[0] or 'application/octet-stream'
    media = MediaFileUpload(local, mimetype=mime, resumable=False)
    if existing:
        svc.files().update(fileId=existing['id'], media_body=media).execute()
        return existing['id'], 'updated'
    md = svc.files().create(
        body={'name': name, 'parents': [parent]}, media_body=media,
        fields='id').execute()
    return md['id'], 'created'


# --- target folder ---------------------------------------------------------
root, made = find_or_create(ACTIVE, DEST_NAME)
print('%s "%s" under 01-Active' % ('created' if made else 'reusing', DEST_NAME))

# --- walk the staged tree --------------------------------------------------
created = updated = 0
fails = []
folder_ids = {'': root}

for dirpath, dirnames, filenames in os.walk(SRC):
    dirnames.sort()
    rel = os.path.relpath(dirpath, SRC)
    rel = '' if rel == '.' else rel
    parent = folder_ids[rel]
    for d in dirnames:
        sub_rel = os.path.join(rel, d) if rel else d
        folder_ids[sub_rel], _ = find_or_create(parent, d)

for dirpath, dirnames, filenames in os.walk(SRC):
    rel = os.path.relpath(dirpath, SRC)
    rel = '' if rel == '.' else rel
    parent = folder_ids[rel]
    for fn in sorted(filenames):
        if fn.endswith('.pyc'):
            continue
        local = os.path.join(dirpath, fn)
        try:
            _id, action = upload(local, parent, fn)
            if action == 'created':
                created += 1
            else:
                updated += 1
        except Exception as e:                      # keep going, report at end
            fails.append('%s: %s' % (fn, e))

print('uploaded: %d new, %d updated' % (created, updated))
if fails:
    print('FAILURES (%d):' % len(fails))
    for f in fails:
        print('   ', f)
else:
    print('failures: none')

# --- verify by re-listing --------------------------------------------------
def count(fid):
    total, token = 0, None
    while True:
        r = svc.files().list(
            q="'%s' in parents and trashed=false" % fid,
            fields='nextPageToken,files(id,name,mimeType,size)',
            pageSize=200, pageToken=token).execute()
        total += len(r.get('files', []))
        token = r.get('nextPageToken')
        if not token:
            return total

print()
print('VERIFY')
print('  root folder id :', root)
print('  root children  :', count(root), '(folders)')
for sub in ['model', 'audio', 'shots', 'assets']:
    sid = folder_ids.get(sub)
    if sid:
        print('  %-7s files   : %d' % (sub, count(sid)))
print('  webViewLink    : https://drive.google.com/drive/folders/%s' % root)
