#!/usr/bin/env python3
import urllib.request, json, sys
base = sys.argv[1] if len(sys.argv)>1 else 'http://localhost:40602'
paths = ['/', '/dashboard', '/static/css/style.css', '/static/images/hero-illustration.svg']
results = {}
for p in paths:
    url = base + p
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            results[p] = {'code': r.getcode(), 'len': len(r.read())}
    except Exception as e:
        results[p] = {'error': str(e)}
print(json.dumps(results, indent=2))
