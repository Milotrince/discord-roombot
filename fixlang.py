import json
from pathlib import Path

with open('text/en.json', 'r', encoding='utf-8') as inf:
    data = json.load(inf)
    out = {}
    for name in data['_name']:
        out[name] = {
            "_name": name,
            "_aliases": data['_aliases'][name],
            "_help": data['_help'][name]
        }

    with open('text/output.json', 'w', encoding='utf-8') as outf:
        outf.write(json.dumps(out))
        outf.close()