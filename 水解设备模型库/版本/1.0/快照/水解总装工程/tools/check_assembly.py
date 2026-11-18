"""Geometry-based cross-module interference screening, not AABB-only claims.
Triangle SAT plus closed-component containment; contacts are review items.
"""
from pathlib import Path
import json, re, hashlib, sys
import numpy as np
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parent

def script(path,variable):
 s=path.read_text(encoding='utf-8-sig');match=re.search(r'window\.'+variable+r'\s*=',s);return json.JSONDecoder().raw_decode(s[match.end():].lstrip())[0]
def tri(parts,translation=(0,0,0),angle=0,scale=1,mirror_y=False):
 result=[];a=np.deg2rad(angle);rot=np.array([[np.cos(a),-np.sin(a),0],[np.sin(a),np.cos(a),0],[0,0,1]])
 for p in parts:
  v=np.asarray(p['vertices'],float)*scale
  if mirror_y:v[:,1]*=-1
  v=v@rot.T+translation
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
def closed_components(parts,position,angle,mirror_y=False):
 out=[]
 for p in parts:
  edges={}
  for f in p['faces']:
   for i in range(len(f)):
    e=tuple(sorted((f[i],f[(i+1)%len(f)])));edges[e]=edges.get(e,0)+1
  if edges and all(n==2 for n in edges.values()):out.append(tri([p],position,angle,mirror_y=mirror_y))
 return out

def clip_polygon(points, axis, value, keep_above):
 result=[]
 for a,b in zip(points,points[1:]+points[:1]):
  da=(a[axis]-value)*(1 if keep_above else -1);db=(b[axis]-value)*(1 if keep_above else -1)
  if da>=0:result.append(a)
  if (da>=0)!=(db>=0):result.append(a+(b-a)*da/(da-db))
 return result

def column_penetration(other,column,tolerance=0.1):
 """Clip actual surfaces against the open box interior, excluding face contact."""
 low=column['low']+tolerance;high=column['high']-tolerance
 candidates=np.flatnonzero(np.all(other['th']>low,axis=1)&np.all(other['tl']<high,axis=1))
 best=None
 for i in candidates:
  poly=list(other['t'][i])
  for axis in range(3):
   poly=clip_polygon(poly,axis,low[axis],True)
   if not poly:break
   poly=clip_polygon(poly,axis,high[axis],False)
   if not poly:break
  if len(poly)<3:continue
  area=sum(np.linalg.norm(np.cross(poly[j]-poly[0],poly[j+1]-poly[0])) for j in range(1,len(poly)-1))/2
  if area<1e-6:continue
  point=np.mean(poly,axis=0);depth=float(np.min(np.r_[point-column['low'],column['high']-point]))
  if best is None or depth>best['interior_sample_depth_mm']:
   best={'triangle':int(i),'interior_sample_mm':point.round(4).tolist(),'interior_sample_depth_mm':round(depth,4)}
 return best

def run():
 cfg=json.loads((OUT/'assembly.json').read_text());hashes=json.loads((OUT/'data/来源与哈希.json').read_text())['sources']
 for path,digest in hashes.items():assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
 objects=[];cache={};closed={}
 for p in cfg['equipment']:
  source=cfg['assets'][p['asset']]['source'];parts=cache.setdefault(source,script(ROOT/source,'MODEL_PARTS'))
  t=tri(parts,p['position_mm'],p['rotation_deg'],mirror_y=p.get('mirror_y',False));objects.append(object_mesh(p['id'],'equipment',t,p['z_status']))
  closed[p['id']]=closed_components(parts,p['position_mm'],p['rotation_deg'],p.get('mirror_y',False))
 for g in script(ROOT/'水解桥架工程/models/整体/viewer_data.js','GEOMETRY'):
  parts=[{'vertices':g['v'],'faces':g['f']}];objects.append(object_mesh(g['id'],'bridge',tri(parts,scale=1000)))
 for p in script(ROOT/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if p['kind']=='structure':
   t=tri([p]);objects.append(object_mesh(p['name'],'structure',t,'上部柱截面待核'));closed[p['name']]=[t]
 candidates=0;hits=[];contacts=[]
 for i,a in enumerate(objects):
  for b in objects[i+1:]:
   if a['kind']==b['kind'] and a['kind']!='equipment':continue
   overlap=np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])
   if np.any(overlap<0):continue
   candidates+=1
   record={'a':a['id'],'b':b['id'],'kind':a['kind']+'/'+b['kind'],'overlap_aabb_mm':overlap.round(3).tolist(),'position_mm':((np.maximum(a['low'],b['low'])+np.minimum(a['high'],b['high']))/2).round(3).tolist(),'placement_status':[a['status'],b['status']]}
   if b['kind']=='structure':
    interior=column_penetration(a,b)
    if interior:
     record.update(method='triangle-clipped-to-column-open-interior',status='构件穿入柱体内部',**interior);hits.append(record)
    elif surface(a,b) is not None:
     record.update(method='surface-contact-without-open-interior-penetration',status='表面接触（正常）');contacts.append(record)
    elif any(inside((b['low']+b['high'])/2,t) for t in closed.get(a['id'],[])):
     record.update(method='closed-component-contains-column-center',status='柱体进入设备闭合实体，待复核');hits.append(record)
    continue
   proof=surface(a,b);method='triangle-SAT'
   if proof is None:
    contains=any(inside(b['t'][0,0],t) for t in closed.get(a['id'],[])) or any(inside(a['t'][0,0],t) for t in closed.get(b['id'],[]))
    if not contains:continue
    method='closed-component-ray-containment'
   record.update(method=method,triangles=proof,status='几何相交，需核对安装/接触关系')
   if overlap.min()<0.1:
    record['status']='表面接触（正常）';contacts.append(record)
   else:hits.append(record)
 report={'version':'0.3','status':'存在待复核项' if hits else '已检查范围未发现几何相交','object_count':len(objects),'aabb_candidates':candidates,'intersections':hits,'normal_contacts':contacts,'contact_tolerance_mm':0.1,
  'unplaced_excluded':len(cfg['unplaced']),'scope':'桥架/设备、桥架/柱、设备/柱、设备/设备；支持面与设备基础不参与报错',
  'limits':['相交是几何证据，不自动认定施工冲突','部分安装标高、管口朝向及上层柱截面待核','本报告仍限原主体柱/设备/桥架；新增房间、楼梯及梁架未纳入检查','不检查检修空间；不将相接桥架端口列为冲突']}
 (OUT/'data/碰撞报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 (OUT/'data/collisions.js').write_text('window.ASSEMBLY_COLLISIONS='+json.dumps(report,ensure_ascii=False,separators=(',',':'))+';\n')
 special={'version':'0.3','contact_tolerance_mm':0.1,'columns_retained':sum(o['kind']=='structure' for o in objects),'penetrations':[r for r in hits if r['kind']=='bridge/structure'],'normal_contacts':[r for r in contacts if r['kind']=='bridge/structure'],'rule':'真实三角面进入柱体开内部才报穿入；仅表面接触为正常；当前引用桥架2.0，整改记录位于桥架源模块'}
 (OUT/'data/桥架立柱核对.json').write_text(json.dumps(special,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ('intersections','normal_contacts')},ensure_ascii=False));print('intersections',len(hits),'contacts',len(contacts))
if __name__=='__main__':run()
