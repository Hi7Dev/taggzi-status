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
    if kind == 'ssl':
        # Certificate valid for the hostname and not expiring soon.
        t = time.time()
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((c['host'], 443), timeout=c.get('timeout', 10)) as sock:
                with ctx.wrap_socket(sock, server_hostname=c['host']) as tls:
                    cert = tls.getpeercert()
            ms = int((time.time() - t) * 1000)
            left = (datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(cert['notAfter']), datetime.timezone.utc) - NOW).days
            if left < 0:
                return 'down', ms, 'certificate expired'
            if left < c.get('warn_days', 21):
                return 'degraded', ms, f'certificate expires in {left} days'
            return 'up', ms, ''
        except ssl.SSLCertVerificationError as e:
            return 'down', int((time.time() - t) * 1000), 'certificate not valid (' + str(getattr(e, 'verify_message', '') or 'verify failed') + ')'
        except Exception as e:
            return 'down', int((time.time() - t) * 1000), type(e).__name__
    return 'down', 0, 'unknown check type'


def whatsapp(msg):
    phone, key = os.environ.get('CALLMEBOT_PHONE'), os.environ.get('CALLMEBOT_APIKEY')
    if not phone or not key:
        return
    url = 'https://api.callmebot.com/whatsapp.php?' + urllib.parse.urlencode({'phone': phone, 'text': msg, 'apikey': key})
    fetch(url, 20)


COLOURS = {'up': '#22c55e', 'degraded': '#f59e0b', 'down': '#ef4444'}
WORDS = {'up': 'Operational', 'degraded': 'Degraded', 'down': 'Outage'}


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')


def status_svg(comps, overall, uptime):
    """Live, animated status card for the GitHub README (regenerated every run)."""
    W, row, top = 820, 46, 150
    H = top + row * len(comps) + 58
    try:
        from zoneinfo import ZoneInfo
        uk = NOW.astimezone(ZoneInfo('Europe/London')).strftime('%d/%m/%Y %H:%M')
    except Exception:
        uk = NOW.strftime('%d/%m/%Y %H:%M UTC')
    head = {'up': 'All systems operational', 'degraded': 'Some systems degraded', 'down': 'Partial outage'}[overall]
    c = COLOURS[overall]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif">',
           '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#171412"/><stop offset="1" stop-color="#0C0A09"/></linearGradient>',
           '<linearGradient id="gold" x1="0" x2="1"><stop offset="0" stop-color="#F0BF4A"/><stop offset="1" stop-color="#c6a85b"/></linearGradient>',
           '<linearGradient id="shine" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".08"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient></defs>',
           f'<rect width="{W}" height="{H}" rx="18" fill="url(#bg)" stroke="#2a2521"/>',
           f'<rect x="18" y="0" width="{W-36}" height="4" rx="2" fill="url(#gold)"/>',
           '<text x="32" y="52" font-size="24" font-weight="800" fill="#F2EDE8">Taggzi <tspan fill="#F0BF4A">Status</tspan></text>',
           f'<text x="{W-32}" y="52" font-size="13" fill="#9C968C" text-anchor="end">Live · updated {uk} UK</text>',
           f'<rect x="24" y="74" width="{W-48}" height="52" rx="12" fill="{c}" fill-opacity=".12" stroke="{c}" stroke-opacity=".45"/>',
           f'<rect x="24" y="74" width="160" height="52" rx="12" fill="url(#shine)"><animate attributeName="x" from="-160" to="{W}" dur="4s" repeatCount="indefinite"/></rect>',
           f'<circle cx="52" cy="100" r="7" fill="{c}"/><circle cx="52" cy="100" r="7" fill="none" stroke="{c}" stroke-width="2">'
           '<animate attributeName="r" values="7;15;7" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values=".9;0;.9" dur="2s" repeatCount="indefinite"/></circle>',
           f'<text x="72" y="106" font-size="18" font-weight="700" fill="#F2EDE8">{esc(head)}</text>']
    for i, comp in enumerate(comps):
        y = top + i * row
        col = COLOURS[comp['status']]
        hist = uptime.get(comp['id'], {})
        up = sum(d['up'] for d in hist.values()); tot = sum(d['total'] for d in hist.values())
        pct = f'{up / tot * 100:.2f}%' if tot else '—'
        delay = f'{i * 0.15:.2f}s'
        out += [f'<g opacity="0"><animate attributeName="opacity" from="0" to="1" begin="{delay}" dur=".6s" fill="freeze"/>',
                f'<line x1="32" y1="{y + row - 8}" x2="{W-32}" y2="{y + row - 8}" stroke="#2a2521"/>',
                f'<circle cx="44" cy="{y + 16}" r="6" fill="{col}"><animate attributeName="opacity" values="1;.45;1" dur="2.4s" begin="{delay}" repeatCount="indefinite"/></circle>',
                f'<text x="62" y="{y + 21}" font-size="15" font-weight="650" fill="#F2EDE8">{esc(comp["name"])}</text>',
                f'<text x="{W-190}" y="{y + 21}" font-size="13" fill="#9C968C" text-anchor="end">{pct} uptime</text>',
                f'<rect x="{W-172}" y="{y + 4}" width="140" height="24" rx="12" fill="{col}" fill-opacity=".14" stroke="{col}" stroke-opacity=".5"/>',
                f'<text x="{W-102}" y="{y + 21}" font-size="12" font-weight="700" fill="{col}" text-anchor="middle">{WORDS[comp["status"]]}</text></g>']
    out += [f'<text x="32" y="{H-22}" font-size="12" fill="#9C968C">Checked every 5 minutes from outside Taggzi’s servers · status.taggzi.com</text>', '</svg>']
    return '\n'.join(out)


def badge(label, status):
    return {'schemaVersion': 1, 'label': label, 'message': WORDS[status].lower(), 'color': {'up': 'brightgreen', 'degraded': 'orange', 'down': 'red'}[status],
            'labelColor': '0C0A09', 'cacheSeconds': 300}


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
    # README assets: animated live card + shields.io endpoint badges.
    with open(os.path.join(DATA, 'status.svg'), 'w', encoding='utf-8') as fh:
        fh.write(status_svg(comps, overall, uptime))
    os.makedirs(os.path.join(DATA, 'badges'), exist_ok=True)
    with open(os.path.join(DATA, 'badges', 'overall.json'), 'w', encoding='utf-8') as fh:
        json.dump(badge('taggzi', overall), fh)
    for comp in comps:
        with open(os.path.join(DATA, 'badges', comp['id'] + '.json'), 'w', encoding='utf-8') as fh:
            json.dump(badge(comp['name'].lower(), comp['status']), fh)
    uptimes = []
    for comp in comps:
        h = uptime.get(comp['id'], {})
        t = sum(d['total'] for d in h.values())
        if t: uptimes.append(sum(d['up'] for d in h.values()) / t)
    avg = (sum(uptimes) / len(uptimes) * 100) if uptimes else 100
    with open(os.path.join(DATA, 'badges', 'uptime.json'), 'w', encoding='utf-8') as fh:
        json.dump({'schemaVersion': 1, 'label': 'uptime (90d)', 'message': f'{avg:.2f}%', 'color': 'brightgreen' if avg >= 99.5 else ('orange' if avg >= 97 else 'red'),
                   'labelColor': '0C0A09', 'cacheSeconds': 300}, fh)

    # Alert only on confirmed outages and recoveries from them — not on slow/blip "degraded".
    changes = [c for c in changes if c[2] == 'down' or c[1] == 'down']
    if changes:
        lines = [f"{'✅' if new == 'up' else ('⚠️' if new == 'degraded' else '🔴')} {name}: {old} → {new}" + (f' ({msg})' if msg and new != 'up' else '')
                 for name, old, new, msg in changes]
        whatsapp('Taggzi status change\n' + '\n'.join(lines) + '\nhttps://status.taggzi.com')
    print(json.dumps({'overall': overall, 'components': {c['id']: c['status'] for c in comps}, 'changes': len(changes)}))


if __name__ == '__main__':
    main()
