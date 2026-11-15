from pathlib import Path
import re, collections
p=Path('0241B_二期水解仪表桥架布局_1031_t3.dxf')
lines=p.read_text('utf-8',errors='ignore').splitlines()
pairs=list(zip(lines[0::2],lines[1::2]))
layers=collections.Counter(); types=collections.Counter(); texts=[]; coords=[]; dims=[]
i=0
while i<len(pairs):
    code,val=pairs[i];
    if code.strip()=='0' and val.strip() not in ('SECTION','ENDSEC','EOF'):
        typ=val.strip(); types[typ]+=1; j=i+1; ent={}
        while j<len(pairs) and pairs[j][0].strip()!='0':
            c,v=pairs[j]; ent.setdefault(c.strip(),[]).append(v); j+=1
        lay=ent.get('8',[''])[0]; layers[lay]+=1
        if typ in ('TEXT','MTEXT','ATTRIB','ATTDEF'):
            s=''.join(ent.get('1',[])+ent.get('3',[])); texts.append((typ,lay,s,ent.get('10',[''])[0],ent.get('20',[''])[0]))
        for c in ('10','11','12','13','14','15','16','17','18','19','20','21','22','23','24','25','26','27','28','29'):
            for v in ent.get(c,[]):
                try: coords.append((float(v),c,lay,typ))
                except: pass
        if typ in ('DIMENSION','LEADER'): dims.append((typ,lay,ent))
        i=j
    else: i+=1
print('TYPES',types)
print('LAYERS')
for k,v in layers.most_common(): print(v,k)
print('TEXTS',len(texts))
for x in texts[:500]: print(x)
print('COORDRANGE', min((x[0] for x in coords),default=None), max((x[0] for x in coords),default=None))
print('DIMS',len(dims))
for d in dims[:100]: print(d[0],d[1],d[2].get('1',['']))
for key in ['CABLETRAY','A-Wall','A-Strs','S-Cols','A-Roof','Flor','A-Anno-Levl']:
    vals=[x[0] for x in coords if key.lower() in x[2].lower()]
    if vals: print('RANGE',key,min(vals),max(vals),len(vals))
for key in ['CABLETRAY_WEAK','A-Wall','A-Strs','S-Cols','A-Roof','Flor']:
    valsx=[x[0] for x in coords if key.lower() in x[2].lower() and x[1] in ('10','11','12','13','14','15','16','17','18','19')]
    valsy=[x[0] for x in coords if key.lower() in x[2].lower() and x[1] in ('20','21','22','23','24','25','26','27','28','29')]
    if valsx or valsy: print('XYRANGE',key, (min(valsx),max(valsx)) if valsx else None, (min(valsy),max(valsy)) if valsy else None)
print('MATCHED TEXT')
for x in texts:
    if any(k.lower() in x[2].lower() for k in ['el','f01','f02','f03','楼','层','标高','hydro']): print(x)
