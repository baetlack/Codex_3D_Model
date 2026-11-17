"""Geometry-based cross-module interference screening, not AABB-only claims.
Triangle SAT plus closed-component containment; contacts are review items.
"""
from pathlib import Path
import json, re, hashlib, sys
import numpy as np
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parent

def script(path,variable):
 s=path.read_text(encoding='utf-8-sig');match=re.search(r'window\.'+variable+r'\s*=',s);return json.JSONDecoder().raw_decode(s[match.end():].lstrip())[0]
def tri(parts,translation=(0,0,0),angle=0,scale=1):
 result=[];a=np.deg2rad(angle);rot=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
 for p in parts:
  v=np.asarray(p['vertices'],float)*scale;v=v@rot.T+translation
  for f in p['faces']:
   for i in range(1,len(f)-1):result.append(v[[f[0],f[i],f[i+1]]])
 t=np.asarray(result)
 return t[np.linalg.norm(np.cross(t[:,1]-t[:,0],t[:,2]-t[:,0]),axis=1)>1e-8]
def object_mesh(id,kind,t,status='定位有依据'):
 return {'id':id,'kind':kind,'t':t,'low':t.min(axis=(0,1)),'high':t.max(axis=(0,1)),'tl':t.min(axis=1),'th':t.max(axis=1),'status':status}
def sat(a,b):
 ea=np.roll(a,-1,axis=0)-a;eb=np.roll(b,-1,axis=0)-b;na=np.cross(ea[0],ea[1]);nb=np.cross(eb[0],eb[1])
 axes=np.vstack([na,nb,np.cross(ea[:,None,:],eb[None,:,:]).reshape(-1,3),np.cross(na,ea),np.cross(nb,eb)])
 axes=axes[np.linalg.norm(axes,axis=1)>1e-8];axes/=np.linalg.norm(axes,axis=1)[:,None]
 pa=a@axes.T;pb=b@axes.T
 return bool(np.all(pa.max(axis=0)>=pb.min(axis=0)-1e-5) and np.all(pb.max(axis=0)>=pa.min(axis=0)-1e-5))
def surface(a,b):
 for i,t in enumerate(a['t']):
  mask=np.all(b['th']>=a['tl'][i]-1e-5,axis=1)&np.all(b['tl']<=a['th'][i]+1e-5,axis=1)
  for j in np.flatnonzero(mask):
   if sat(t,b['t'][j]):return [int(i),int(j)]
 return None
def inside(point,ts):
 # A non-axis ray avoids repeated hits on the axis-aligned tessellation.
 direction=np.array([1.,.1732050808,.3178372452]);edge1=ts[:,1]-ts[:,0];edge2=ts[:,2]-ts[:,0]
 h=np.cross(direction,edge2);a=np.einsum('ij,ij->i',edge1,h);ok=np.abs(a)>1e-9
 f=np.divide(1,a,out=np.zeros_like(a),where=ok);s=point-ts[:,0];u=f*np.einsum('ij,ij->i',s,h);q=np.cross(s,edge1);v=f*(q@direction);d=f*np.einsum('ij,ij->i',edge2,q)
 hits=np.sort(d[ok&(u>=-1e-8)&(v>=-1e-8)&(u+v<=1+1e-8)&(d>1e-5)])
 hits=hits[np.r_[True,np.diff(hits)>1e-4]] if len(hits) else hits
 return len(hits)%2==1
def closed_components(parts,position,angle):
 out=[]
 for p in parts:
  edges={}
  for f in p['faces']:
   for i in range(len(f)):
    e=tuple(sorted((f[i],f[(i+1)%len(f)])));edges[e]=edges.get(e,0)+1
  if edges and all(n==2 for n in edges.values()):out.append(tri([p],position,angle))
 return out

def run():
 cfg=json.loads((OUT/'assembly.json').read_text());hashes=json.loads((OUT/'data/来源与哈希.json').read_text())['sources']
 for path,digest in hashes.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 objects=[];cache={};closed={}
 for p in cfg['equipment']:
  source=cfg['assets'][p['asset']]['source'];parts=cache.setdefault(source,script(ROOT/source,'MODEL_PARTS'))
  t=tri(parts,p['position_mm'],p['rotation_deg']);objects.append(object_mesh(p['id'],'equipment',t,p['z_status']))
  closed[p['id']]=closed_components(parts,p['position_mm'],p['rotation_deg'])
 for g in script(ROOT/'水解桥架工程/models/整体/viewer_data.js','GEOMETRY'):
  parts=[{'vertices':g['v'],'faces':g['f']}];objects.append(object_mesh(g['id'],'bridge',tri(parts,scale=1000)))
 for p in script(OUT/'data/building.js','ASSEMBLY_BUILDING'):
  if p['kind']=='structure':
   t=tri([p]);objects.append(object_mesh(p['name'],'structure',t,'上部柱截面待核'));closed[p['name']]=[t]
 candidates=0;hits=[];contacts=[]
 for i,a in enumerate(objects):
  for b in objects[i+1:]:
   if a['kind']==b['kind'] and a['kind']!='equipment':continue
   overlap=np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])
   if np.any(overlap<0):continue
   candidates+=1;proof=surface(a,b);method='triangle-SAT'
   if proof is None:
    contains=any(inside(b['t'][0,0],t) for t in closed.get(a['id'],[])) or any(inside(a['t'][0,0],t) for t in closed.get(b['id'],[]))
    if not contains:continue
    method='closed-component-ray-containment'
   record={'a':a['id'],'b':b['id'],'kind':a['kind']+'/'+b['kind'],'method':method,'triangles':proof,'overlap_aabb_mm':overlap.round(3).tolist(),'position_mm':((np.maximum(a['low'],b['low'])+np.minimum(a['high'],b['high']))/2).round(3).tolist(),'status':'几何相交，需核对安装/接触关系','placement_status':[a['status'],b['status']]}
   (contacts if overlap.min()<1 else hits).append(record)
 report={'version':'0.1','status':'存在待复核项' if hits else '已检查范围未发现几何相交','object_count':len(objects),'aabb_candidates':candidates,'intersections':hits,'contacts_under_1mm':contacts,
  'unplaced_excluded':len(cfg['unplaced']),'scope':'桥架/设备、桥架/柱、设备/柱、设备/设备；支持面与设备基础不参与报错',
  'limits':['相交是几何证据，不自动认定施工冲突','部分安装标高、管口朝向及上层柱截面待核','无真实梁板截面与开孔资料，未检查梁板碰撞；墙体为显示假设，不用于碰撞定论','不检查检修空间；不将相接桥架端口列为冲突']}
 (OUT/'data/碰撞报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'data/collisions.js').write_text('window.ASSEMBLY_COLLISIONS='+json.dumps(report,ensure_ascii=False,separators=(',',':'))+';\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('intersections','contacts_under_1mm')},ensure_ascii=False));print('intersections',len(hits),'contacts',len(contacts))
if __name__=='__main__':run()
