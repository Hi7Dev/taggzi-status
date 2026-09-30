"""Taggzi status checker — runs on GitHub Actions every 5 minutes (independent of taggzi.com / 20i).

Reads config.json, runs each component's checks, then updates (in ./data, the `data` branch):
  status.json     current state of every component
  uptime.json     per-component daily {up, total} counts, last 90 days
  incidents.json  automatic incidents (opened when a component goes down/degraded, closed on recovery)
Optional WhatsApp alert on change (CallMeBot) if CALLMEBOT_PHONE / CALLMEBOT_APIKEY secrets are set.
"""
import json, os, socket, time, datetime, urllib.request, urllib.error, urllib.parse, ssl

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
UA = 'TaggziStatus/1.0 (+https://status.taggzi.com)'
RANK = {'up': 0, 'degraded': 1, 'down': 2}
NOW = datetime.datetime.now(datetime.timezone.utc)


def load(name, default):
    try:
        with open(os.path.join(DATA, name), encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save(name, obj):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, name), 'w', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)


def fetch(url, timeout=20):
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': '*/*', 'Cache-Control': 'no-cache'})
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as r:
            body = r.read(400_000).decode('utf-8', 'ignore')
            return r.status, body, int((time.time() - t) * 1000), ''
    except urllib.error.HTTPError as e:
        return e.code, '', int((time.time() - t) * 1000), f'HTTP {e.code}'
    except Exception as e:
        return 0, '', int((time.time() - t) * 1000), type(e).__name__ + ': ' + str(e)[:120]


_health = {}


def health(url):
    """Fetch the site's own health report once per run."""
    if url not in _health:
        code, body, ms, err = fetch(url, 30)
        if code != 200:   # one retry — a deploy or cold cache can make a single request slow
            time.sleep(5)
            code, body, ms, err = fetch(url, 30)
        try:
            _health[url] = (json.loads(body) if code == 200 else None, ms, err or (f'HTTP {code}' if code != 200 else ''))
        except Exception:
            _health[url] = (None, ms, 'unreadable health report')
    return _health[url]


def run_check(c):
    kind = c['type']
    if kind == 'http':
        code, body, ms, err = fetch(c['url'], c.get('timeout', 20))
        if code != c.get('expect', 200):
            return 'down', ms, err or f'HTTP {code}'
        if c.get('contains') and c['contains'] not in body:
            return 'down', ms, 'page loaded but looks wrong'
        return ('degraded' if ms > c.get('slow_ms', 10000) else 'up'), ms, ('slow' if ms > c.get('slow_ms', 10000) else '')
    if kind == 'health':
        rep, ms, err = health(c['url'])
        if rep is None:
            return 'down', ms, err or 'health report unavailable'
        comp = (rep.get('components') or {}).get(c['component'])
        if not comp:
            return 'degraded', ms, 'not reported'
        st = comp.get('status', 'down')
        return (st if st in RANK else 'down'), int(comp.get('ms', ms)), comp.get('message', '')
    if kind == 'tcp':
        t = time.time()
        try:
            with socket.create_connection((c['host'], c['port']), timeout=c.get('timeout', 8)):
                return 'up', int((time.time() - t) * 1000), ''
        except Exception as e:
            return 'down', int((time.time() - t) * 1000), type(e).__name__
    return 'down', 0, 'unknown check type'


def whatsapp(msg):
    phone, key = os.environ.get('CALLMEBOT_PHONE'), os.environ.get('CALLMEBOT_APIKEY')
    if not phone or not key:
        return
    url = 'https://api.callmebot.com/whatsapp.php?' + urllib.parse.urlencode({'phone': phone, 'text': msg, 'apikey': key})
    fetch(url, 20)


def main():
    cfg = json.load(open(os.path.join(HERE, 'config.json'), encoding='utf-8'))
    prev = {c['id']: c for c in load('status.json', {}).get('components', [])}
    uptime = load('uptime.json', {})
    incidents = load('incidents.json', [])
    today = NOW.strftime('%Y-%m-%d')
    comps, changes = [], []

    for comp in cfg['components']:
        results = [(c.get('label', c['type']),) + run_check(c) for c in comp['checks']]
        worst = max(results, key=lambda r: RANK[r[1]])
        status = worst[1]
        # A single failed run can be a blip — only report "down" after two in a row.
        was = prev.get(comp['id'], {})
        if status == 'down' and was.get('raw') not in ('down',):
            shown = 'degraded' if was.get('status') != 'down' else 'down'
        else:
            shown = status
        message = '; '.join(f'{r[0]}: {r[3]}' for r in results if r[1] != 'up' and r[3]) or ''
        comps.append({'id': comp['id'], 'name': comp['name'], 'description': comp.get('description', ''),
                      'status': shown, 'raw': status, 'latency_ms': max(r[2] for r in results), 'message': message})

        day = uptime.setdefault(comp['id'], {}).setdefault(today, {'up': 0, 'total': 0})
        day['total'] += 1
        day['up'] += 0 if shown == 'down' else 1   # slow / partly affected still counts as available
        for d in sorted(uptime[comp['id']])[:-90]:
            del uptime[comp['id']][d]

        old = was.get('status', 'up')
        if shown != old:
            changes.append((comp['name'], old, shown, message))
            open_inc = next((i for i in incidents if i['component'] == comp['id'] and not i.get('resolved')), None)
            if shown == 'down' and not open_inc:   # incidents are confirmed outages only
                incidents.insert(0, {'component': comp['id'], 'name': comp['name'], 'status': shown, 'started': NOW.isoformat(timespec='seconds'),
                                     'resolved': None, 'detail': message})
            elif shown != 'down' and open_inc:
                open_inc['resolved'] = NOW.isoformat(timespec='seconds')
            elif open_inc:
                open_inc['status'] = shown

    overall = max((c['status'] for c in comps), key=lambda s: RANK[s])
    save('status.json', {'updated': NOW.isoformat(timespec='seconds'), 'overall': overall, 'components': comps})
    save('uptime.json', uptime)
    save('incidents.json', incidents[:100])

    # Alert only on confirmed outages and recoveries from them — not on slow/blip "degraded".
    changes = [c for c in changes if c[2] == 'down' or c[1] == 'down']
    if changes:
        lines = [f"{'✅' if new == 'up' else ('⚠️' if new == 'degraded' else '🔴')} {name}: {old} → {new}" + (f' ({msg})' if msg and new != 'up' else '')
                 for name, old, new, msg in changes]
        whatsapp('Taggzi status change\n' + '\n'.join(lines) + '\nhttps://status.taggzi.com')
    print(json.dumps({'overall': overall, 'components': {c['id']: c['status'] for c in comps}, 'changes': len(changes)}))


if __name__ == '__main__':
    main()
