from pathlib import Path
from collections import Counter
import json
p=Path('0241B_二期水解仪表桥架布局_1031_t3.dxf')
lines=p.read_text(encoding='gb18030',errors='replace').splitlines()
entities=[]; ent=None
for a,b in zip(lines[::2],lines[1::2]):
    c=a.strip()
    if c=='0':
        if ent: entities.append(ent)
        ent={'type':b,'data':{}}
    elif ent: ent['data'].setdefault(c,[]).append(b)
if ent: entities.append(ent)
tray=[e for e in entities if any('CABLETRAY' in v.upper() for v in e['data'].get('8',[]))]
zs=Counter(); examples=[]
for e in tray:
    for c in ['30','31','32','33','38']:
        for v in e['data'].get(c,[]): zs[(c,v)]+=1
    if e['type']=='INSERT': examples.append(e)
print('tray types',Counter(e['type'] for e in tray))
print('z values',zs)
print('insert samples',json.dumps(examples[:5],ensure_ascii=True))
print('extended data entities',sum(any(int(c)>=1000 for c in e['data'] if c.isdigit()) for e in tray))
for e in entities:
    if e['type'] in ['TEXT','MTEXT']:
        s=''.join(e['data'].get('1',[])+e['data'].get('3',[]))
        if 'EL' in s.upper(): print('label',s)
