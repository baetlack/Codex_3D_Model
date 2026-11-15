from pathlib import Path
from collections import Counter
import json, hashlib, sys

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'原始资料'/'20251027 B系列结晶冷却厂房建施图_t3.dxf'
floor=int(sys.argv[1]) if len(sys.argv)>1 else 1
plans={
 1:('CH202511DE-5J-41B-04',4388240.0,171772.0,4432890.0,244422.0),
 2:('CH202511DE-5J-41B-05',4528663.5,167930.4,4573313.5,240580.4),
 3:('CH202511DE-5J-41B-06',4684213.0,163771.5,4728863.0,236421.5),
}
if floor not in plans: raise SystemExit('floor must be 1, 2, or 3')
drawing_id,x0,y0,x1,y1=plans[floor]
prefix=('一','二','三')[floor-1]
OUT=ROOT/f'{prefix}层设备基础.json'
data=SRC.read_bytes().decode('cp936',errors='replace').splitlines()
pairs=list(zip(data[::2],data[1::2])); entities=[]; current=None; inside=False
for code,value in pairs:
    code=code.strip();value=value.strip()
    if code=='2' and value=='ENTITIES': inside=True;continue
    if inside and code=='0' and value=='ENDSEC': break
    if not inside: continue
    if code=='0':
        if current: entities.append(current)
        current={'type':value,'data':[]}
    elif current: current['data'].append((code,value))
if current: entities.append(current)

# First-floor plan frame in drawing 04, at source CAD coordinates.
foundations=[]
for entity in entities:
    d=entity['data'];layer=next((v for c,v in d if c=='8'),'')
    if layer!='基础线': continue
    if entity['type']=='CIRCLE':
        x=float(next(v for c,v in d if c=='10'));y=float(next(v for c,v in d if c=='20'));r=float(next(v for c,v in d if c=='40'))
        if x0<=x<=x1 and y0<=y<=y1:
            foundations.append({'kind':'circle','cx':round(x-x0,2),'cy':round(y-y0,2),'r':round(r,2)})
    elif entity['type']=='LWPOLYLINE':
        if not (int(next((v for c,v in d if c=='70'),'0'))&1): continue
        pts=[];x=None
        for c,v in d:
            if c=='10': x=float(v)
            elif c=='20' and x is not None: pts.append((x,float(v)));x=None
        if len(pts)<4: continue
        if not all(x0-100<=x<=x1+100 and y0-100<=y<=y1+100 for x,y in pts): continue
        w=max(x for x,y in pts)-min(x for x,y in pts);h=max(y for x,y in pts)-min(y for x,y in pts)
        if w<500 or h<500: continue
        foundations.append({'kind':'polygon','points':[[round(x-x0,2),round(y-y0,2)] for x,y in pts],
                            'size':[round(w,2),round(h,2)]})

# Remove identical repeated CAD circles while preserving distinct foundation outlines.
seen=set();clean=[]
for f in foundations:
    if f['kind']=='circle':
        key=(f['kind'],f['cx'],f['cy'],f['r'])
        if key in seen: continue
        seen.add(key)
    clean.append(f)
doc={'floor':floor,'drawing_id':drawing_id,'source':SRC.name,
     'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),
     'units':'mm','axes':{'east':'+X','north':'+Y','up':'+Z'},
     'origin_source_xy':[x0,y0],'plan_bounds_mm':[x1-x0,y1-y0],
     'display_thickness_mm':500,
     'thickness_note':'仅为三维展示厚度，平面图未标基础高度；待基础剖面/详图核对。',
     'items':clean,
     'counts':dict(Counter(f['kind'] for f in clean))}
OUT.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(ROOT/f'{prefix}层设备基础.js').write_text(f'window.FOUNDATIONS_{floor}='+json.dumps(doc,ensure_ascii=False,separators=(',',':'))+';window.FOUNDATIONS=window.FOUNDATIONS_'+str(floor)+';',encoding='utf-8')
print('drawing',doc['drawing_id'],'foundations',doc['counts'],'bounds',doc['plan_bounds_mm'])
