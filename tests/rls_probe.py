"""Probe the live Supabase project as an anonymous visitor and check that
everything schema.sql is meant to forbid really is forbidden.

    python tests/rls_probe.py

Reads SUPABASE_URL / SUPABASE_ANON_KEY from config.js. Leaves ONE pending
event titled "RLS probe - reject me" (with a poster): reject it in the admin
page afterwards, which also deletes its poster.
"""
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
import uuid

cfg = (pathlib.Path(__file__).resolve().parent.parent / 'config.js').read_text(encoding='utf-8')
URL = re.search(r"SUPABASE_URL:\s*'([^']+)'", cfg).group(1).rstrip('/')
KEY = re.search(r"SUPABASE_ANON_KEY:\s*'([^']+)'", cfg).group(1)
if 'YOUR-PROJECT' in URL or KEY.startswith('YOUR-'):
    sys.exit('config.js still has a placeholder Supabase URL or key.')

BASE_HEADERS = {'apikey': KEY, 'Authorization': f'Bearer {KEY}'}


def call(method, path, body=None, headers=None, raw=None):
    h = dict(BASE_HEADERS, **(headers or {}))
    data = raw
    if body is not None:
        data = json.dumps(body).encode()
        h['Content-Type'] = 'application/json'
    req = urllib.request.Request(URL + path, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            txt = r.read().decode() or 'null'
            return r.status, json.loads(txt) if txt.strip()[:1] in '[{"n' else txt
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


results = []


def check(name, ok, detail=''):
    results.append(ok)
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else f'   -> {detail}'))


probe_id = str(uuid.uuid4())
event = {
    'id': probe_id, 'kind': 'meetup', 'title': 'RLS probe - reject me',
    'start_at': '2030-01-01T18:00:00Z', 'address': '1 Probe Street',
    'submitter_email': 'probe@example.com',
}
JPEG = bytes.fromhex('ffd8ffe000104a46494600010100000100010000ffd9')
minimal = {'Prefer': 'return=minimal'}

s, b = call('POST', '/storage/v1/object/posters/approved/probe.jpg', raw=JPEG, headers={'Content-Type': 'image/jpeg'})
check('anon cannot upload outside pending/', s >= 400, f'{s} {b}')

s, b = call('POST', f'/storage/v1/object/posters/pending/{probe_id}.jpg', raw=JPEG, headers={'Content-Type': 'image/jpeg'})
check('anon can upload a poster to pending/', s == 200, f'{s} {b}')

s, b = call('POST', '/rest/v1/events', dict(event, id=str(uuid.uuid4()), status='approved'), minimal)
check('anon cannot insert an already-approved event', s >= 400, f'{s} {b}')

s, b = call('POST', '/rest/v1/events', dict(event, id=str(uuid.uuid4()), approved_at='2030-01-01T00:00:00Z'), minimal)
check('anon cannot set approved_at', s >= 400, f'{s} {b}')

s, b = call('POST', '/rest/v1/events', dict(event, id=str(uuid.uuid4()), poster_path='approved/x.jpg'), minimal)
check('anon cannot point poster_path outside pending/', s >= 400, f'{s} {b}')

s, b = call('POST', '/rest/v1/events', dict(event, poster_path=f'pending/{probe_id}.jpg'), minimal)
check('anon can submit a pending event', s == 201, f'{s} {b}')

s, b = call('GET', f'/rest/v1/events?select=id,status&id=eq.{probe_id}')
check('anon cannot read pending rows', s == 200 and b == [], f'{s} {b}')

s, b = call('GET', '/rest/v1/events?select=submitter_email&limit=1')
check('anon cannot read submitter_email', s >= 400, f'{s} {b}')

s, b = call('GET', '/rest/v1/public_events?select=*&limit=5')
check('anon can read public_events', s == 200 and isinstance(b, list), f'{s} {b}')
check('public_events has no submitter_email', s == 200 and all('submitter_email' not in r for r in b), f'{b}')

s, b = call('PATCH', f'/rest/v1/events?id=eq.{probe_id}', {'status': 'approved'}, {'Prefer': 'return=representation'})
check('anon cannot approve (update)', s >= 400 or b == [], f'{s} {b}')

s, b = call('DELETE', f'/rest/v1/events?id=eq.{probe_id}', headers={'Prefer': 'return=representation'})
check('anon cannot delete', s >= 400 or b == [], f'{s} {b}')

s, b = call('GET', '/rest/v1/rsvps?select=*&limit=1')
check('anon cannot read rsvps', s >= 400, f'{s} {b}')

s, b = call('GET', '/rest/v1/admins?select=*')
check('anon cannot list admins', s >= 400 or b == [], f'{s} {b}')

s, b = call('POST', '/rest/v1/rpc/set_going',
            {'p_event': probe_id, 'p_date': '2030-01-01', 'p_device': str(uuid.uuid4()), 'p_going': True})
check('cannot RSVP to an unapproved event', s >= 400, f'{s} {b}')

s, b = call('POST', '/rest/v1/rpc/going_counts', {})
check('anon can read going counts', s == 200, f'{s} {b}')

print(f'\n{sum(results)}/{len(results)} passed. Reject "RLS probe - reject me" in the admin page to clean up.')
sys.exit(0 if all(results) else 1)
