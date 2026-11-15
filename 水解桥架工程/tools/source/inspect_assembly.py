import json,re
from pathlib import Path
import numpy as np
root=Path(__file__).parent
objs={o['handle']:o for o in json.loads((root/'tray_objects.json').read_text(encoding='utf-8-sig'))}
catalog=json.loads((root/'连接件模型库'/'catalog.json').read_text(encoding='utf-8'))['models']
paths={}
for s in (root/'tray_paths.txt').read_text().splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)',s)
 if m:paths[m[1]]=[np.array([float(v) for v in m[i].split()]) for i in (2,3)]
for c in catalog:
 o=objs[c['dwg_handle']];lo,hi=np.array(o['bounds']);cand=[]
 for handle,ends in paths.items():
  if objs[handle]['type']!='TDbECabletry':continue
  for j,p in enumerate(ends):
   d=np.linalg.norm(np.maximum(0,np.maximum(lo[:2]-p[:2],p[:2]-hi[:2])))
   if d<125:
    prop=objs[handle]['properties'];unit=(ends[1-j]-p)/np.linalg.norm(ends[1-j]-p)
    cand.append([handle,j,np.round(p-(lo+hi)/2,1).tolist(),np.round(unit,2).tolist(),prop['Width'],prop['Height'],round(d)])
 print(c['id'],c['kind'],'bbox',np.round(hi-lo,1).tolist(),'candidates',cand)
