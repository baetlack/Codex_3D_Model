"""Assemble the approved v1.2 fittings without deforming them.
Coordinates: source CAD mm -> building-local mm -> exported meters (GLB Y-up).
Only straight tray lengths/placements are adjusted to the library interfaces.
"""
from pathlib import Path
import itertools,json,re,math,hashlib,struct,csv,zipfile
import numpy as np
from scipy.optimize import minimize,LinearConstraint
from scipy.linalg import qr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from assembly_revision02 import apply_revision

ROOT=Path(__file__).parent;LIB=ROOT/'连接件模型库';OUT=ROOT/'三层桥架模型'
for d in ['models','previews','reports']:(OUT/d).mkdir(parents=True,exist_ok=True)
CATALOG=json.loads((LIB/'catalog.json').read_text(encoding='utf-8'))
assert CATALOG['version']=='1.2-direction-fix'
SOURCES={o['handle']:o for o in json.loads((ROOT/'tray_objects.json').read_text(encoding='utf-8-sig'))}
LAYERS={1:dict(name='第一层',EL=100,origin=[328715.6375890989,55336.38122544941,0],color='#40c9de'),
        2:dict(name='第二层',EL=106,origin=[397595.0108692109,55336.38122544941,0],color='#edb568'),
        3:dict(name='第三层',EL=112,origin=[532950.3888109655,55336.38122544942,0],color='#b197ef')}
PATHS={}
for line in (ROOT/'tray_paths.txt').read_text().splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)',line)
 if m and SOURCES[m[1]]['type']=='TDbECabletry':PATHS[m[1]]=[np.array([float(v) for v in m[k].split()]) for k in (2,3)]
FITS=sorted(CATALOG['models'],key=lambda m:m['id'])
library_hashes={c['id']:hashlib.sha256((LIB/c['files']['glb']).read_bytes()).hexdigest() for c in FITS}

def layer(x):return 1 if x<390000 else 2 if x<500000 else 3
def unit(v):return np.array(v,float)/np.linalg.norm(v)
def basis(d):
 n=unit(np.cross(d,[0,0,1])) if abs(d[2])<.9 else np.array([1.,0,0])
 return n,unit(np.cross(d,n))
def rotation(k):
 a=k*math.pi/2;return np.round([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]],10)
def port_center(model,p):
 q=np.array(p['position_mm'],float)
 # Funnel outlet's metadata already uses the aperture's geometric center.
 return q if model['kind']=='vertical_tee' and p['name']=='C' else q+np.array(p['section_up'])*p['height_mm']/2
def read_obj(path):
 v=[];f=[]
 for line in path.read_text().splitlines():
  if line.startswith('v '):v.append([float(x)*1000 for x in line.split()[1:]])
  elif line.startswith('f '):f.append([int(x)-1 for x in line.split()[1:]])
 return np.array(v),np.array(f)
def candidates(model):
 lo,hi=np.array(model['source_CAD_bbox_mm']);out=[]
 for handle,ends in PATHS.items():
  if layer(ends[0][0])!=int(model['id'][1]):continue
  prop=SOURCES[handle]['properties']
  for j,q in enumerate(ends):
   distance=np.linalg.norm(np.maximum(0,np.maximum(lo[:2]-q[:2],q[:2]-hi[:2])))
   if distance>125:continue
   d=unit(ends[1-j]-q);target=q.copy()
   if abs(d[2])<.9:target[2]+=prop['Height']/2
   out.append(dict(handle=handle,end=j,p=target,n=d,width=prop['Width'],height=prop['Height'],distance=distance))
 return out

placements=[]
for model in FITS:
 cand=candidates(model);best=None;count=min(len(model['ports']),len({c['handle'] for c in cand}))
 # Missing straight neighbors can be a direct fitting-to-fitting junction.
 for nmatch in range(count,0,-1):
  for slots in itertools.combinations(range(len(model['ports'])),nmatch):
   for selected in itertools.permutations(cand,nmatch):
    if len({c['handle'] for c in selected})<nmatch:continue
    # A handed XY offset may be installed as a mirrored instance. Preserve the
    # approved asset and record the instance reflection explicitly.
    for k in range(8 if model['id']=='L2-C18' else 4):
     R=rotation(k%4)@(np.diag([1.,-1.,1.]) if k>=4 else np.eye(3));A=[];b=[];dims=0;valid=True;anchors=[]
     for pi,target in zip(slots,selected):
      p=model['ports'][pi];normal=R@np.array(p['outward_normal'])
      if np.dot(normal,target['n'])<.98:valid=False;break
      q=R@port_center(model,p);d=target['n'];weight=np.eye(3)-np.outer(d,d)+.06*np.outer(d,d)
      if abs(d[2])>.9:weight*=.3
      A.extend(weight);b.extend(weight@(target['p']-q))
      dims+=(abs(p['width_mm']-target['width'])+abs(p['height_mm']-target['height']))*.015
      anchors.append(dict(port=pi,target=target,local_center=q))
     if not valid:continue
     t=np.linalg.lstsq(np.array(A),np.array(b),rcond=None)[0]
     residual=np.linalg.norm(np.array(A)@t-b)
     # Break ties using the source object's nominal elevation and location.
     bbox=np.array(model['source_CAD_bbox_mm']);nominal=bbox[0,2]
     score=residual+dims+abs(t[2]-nominal)*.015+(.5 if k>=4 else 0)
     record=dict(model=model,R=R,t=t,anchors=anchors,score=score,rotation_quarters=k%4,mirrored=k>=4)
     if best is None or score<best['score']:best=record
  if best is not None:break
 if best is None:raise RuntimeError('Cannot place '+model['id'])
 placements.append(best)

# Each original endpoint has one owner at most. Prefer a geometrically coincident
# boundary over an endpoint of a neighboring 50mm straight on the other side.
claims={}
for i,p in enumerate(placements):
 for a in p['anchors']:
  target=a['target'];key=(target['handle'],target['end'])
  distance=np.linalg.norm(p['t']+a['local_center']-target['p'])
  quality=target['distance']*10+distance*.01+p['score']*.001
  if key not in claims or quality<claims[key][2]:claims[key]=(i,a,quality)
for i,p in enumerate(placements):p['anchors']=[a for a in p['anchors'] if claims[(a['target']['handle'],a['target']['end'])][0]==i]

# Direct fitting contact (e.g. L3-C14 reducer -> L3-C13 tee).
unclaimed=[]
for i,p in enumerate(placements):
 used={a['port'] for a in p['anchors']}
 for pi,port in enumerate(p['model']['ports']):
  if pi not in used:unclaimed.append((i,pi,p['t']+p['R']@port_center(p['model'],port),p['R']@np.array(port['outward_normal'])))
direct=[];used=set()
for j,a in enumerate(unclaimed):
 if j in used:continue
 options=[]
 for k,b in enumerate(unclaimed[j+1:],j+1):
  if a[0]==b[0] or k in used or int(placements[a[0]]['model']['id'][1])!=int(placements[b[0]]['model']['id'][1]):continue
  dist=np.linalg.norm(a[2]-b[2])
  if dist<1200 and np.dot(a[3],b[3])<-.98:options.append((dist,k,b))
 if options:
  dist,k,b=min(options,key=lambda x:x[0]);direct.append((a[0],a[1],b[0],b[1],dist));used.update([j,k])

# Global translation solve. Geometry and rotations are fixed; adjacent straight
# trays may change length/offset to meet the approved fittings exactly.
N=len(placements)*3;H=np.eye(N)*.01;g=np.zeros(N);eq=[];eqb=[];ineq=[];ineqb=[]
for i,p in enumerate(placements):
 for a in p['anchors']:
  q=p['t']+a['local_center'];target=a['target'];d=target['n'];W=np.eye(3)-np.outer(d,d)+.05*np.outer(d,d)
  H[i*3:i*3+3,i*3:i*3+3]+=W;g[i*3:i*3+3]+=W@(q-target['p'])
for handle,ends in PATHS.items():
 if (handle,0) not in claims or (handle,1) not in claims:continue
 i,a,_=claims[(handle,0)];j,b,_=claims[(handle,1)];pa=placements[i]['t']+a['local_center'];pb=placements[j]['t']+b['local_center'];d=unit(ends[1]-ends[0])
 for normal in basis(d):
  row=np.zeros(N);row[j*3:j*3+3]+=normal;row[i*3:i*3+3]-=normal;eq.append(row);eqb.append(-np.dot(pb-pa,normal))
 row=np.zeros(N);row[j*3:j*3+3]+=d;row[i*3:i*3+3]-=d;ineq.append(row);ineqb.append(10-np.dot(pb-pa,d))
for i,pi,j,pj,dist in direct:
 p=placements[i];q=placements[j];delta=q['t']+q['R']@port_center(q['model'],q['model']['ports'][pj])-p['t']-p['R']@port_center(p['model'],p['model']['ports'][pi])
 for k in range(3):
  row=np.zeros(N);row[j*3+k]=1;row[i*3+k]-=1;eq.append(row);eqb.append(-delta[k])
constraints=[]
if eq:
 A=np.array(eq);b=np.array(eqb);_,rr,piv=qr(A.T,pivoting=True);rank=np.sum(abs(np.diag(rr))>1e-8);keep=piv[:rank]
 constraints.append(LinearConstraint(A[keep],b[keep],b[keep]))
if ineq:constraints.append(LinearConstraint(np.array(ineq),np.array(ineqb),np.inf))
res=minimize(lambda x:float(.5*x@H@x+g@x),np.zeros(N),jac=lambda x:H@x+g,method='SLSQP',constraints=constraints,options=dict(maxiter=500,ftol=1e-7))
if not res.success:raise RuntimeError('Assembly placement solve failed: '+res.message)
for i,p in enumerate(placements):p['t']+=res.x[i*3:i*3+3]

def world_mm(p,level):return np.array(p)-np.array(LAYERS[level]['origin'])+np.array([0,0,(LAYERS[level]['EL']-100)*1000])
parts=[];connections=[];problems=[]
for i,p in enumerate(placements):
 model=p['model'];level=int(model['id'][1]);v,f=read_obj(LIB/model['files']['obj']);t=world_mm(p['t'],level)
 verts=v@p['R'].T+t
 if p['mirrored']:f=f[:,::-1].copy()
 ports=[]
 for pi,port in enumerate(model['ports']):
  ports.append(dict(name=port['name'],center_mm=(p['R']@port_center(model,port)+t).tolist(),normal=(p['R']@np.array(port['outward_normal'])).tolist(),up=(p['R']@np.array(port['section_up'])).tolist(),width_mm=port['width_mm'],height_mm=port['height_mm']))
 parts.append(dict(id=model['id'],category='fitting',layer=level,kind=model['kind'],label=model['shape'],handle=model['dwg_handle'],v=verts,f=f,ports=ports,
  placement=dict(rotation=rotation(p['rotation_quarters']).tolist(),orientation=p['R'].tolist(),mirrored_local_Y=p['mirrored'],translation_mm=t.tolist(),CAD_translation_mm=p['t'].tolist(),scale=[1,-1 if p['mirrored'] else 1,1]),source_library_glb_SHA256=library_hashes[model['id']],
  source_obj=model['files']['obj'],library_revision=model['revision']))

class Mesh:
 def __init__(self):self.v=[];self.f=[]
 def tri(self,a,b,c):
  if np.linalg.norm(np.cross(np.array(b)-a,np.array(c)-a))<1e-8:return
  i=len(self.v);self.v.extend([a,b,c]);self.f.append([i,i+1,i+2])
 def quad(self,a,b,c,d):self.tri(a,b,c);self.tri(a,c,d)
def straight_mesh(a,b,w,h,up):
 d=unit(b-a);up=unit(up-d*np.dot(up,d));side=unit(np.cross(up,d));t=2
 section=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(w/2-t,h/2),(w/2-t,-h/2+t),(-w/2+t,-h/2+t),(-w/2+t,h/2),(-w/2,h/2)]
 rings=[[p+side*x+up*y for x,y in section] for p in (a,b)];m=Mesh()
 for j in range(8):m.quad(rings[0][j],rings[0][(j+1)%8],rings[1][(j+1)%8],rings[1][j])
 # U-shaped end rims (three rectangles), leaving cable space open.
 for ring in rings:
  for ids in [(0,1,4,5),(1,2,3,4),(0,5,6,7)]:m.quad(*[ring[j] for j in ids])
 return np.array(m.v),np.array(m.f)

endpoint_report=[]
for handle,ends in PATHS.items():
 prop=SOURCES[handle]['properties'];w=prop['Width'];h=prop['Height'];level=layer(ends[0][0]);d=unit(ends[1]-ends[0]);is_vertical=abs(d[2])>.9
 linked=[]
 for j in (0,1):
  if (handle,j) in claims:
   i,a,_=claims[(handle,j)];p=placements[i];linked.append((j,i,a,p['t']+a['local_center']))
 up=np.array([0.,0,1])
 if is_vertical:
  # Prefer a U-shaped elbow interface over a rectangular funnel outlet.
  preferred=sorted(linked,key=lambda v:placements[v[1]]['model']['kind']=='vertical_tee')
  up=placements[preferred[0][1]]['R']@np.array(placements[preferred[0][1]]['model']['ports'][preferred[0][2]['port']]['section_up']) if preferred else np.array([1.,0,0])
 centers=[p+up*h/2 for p in ends]
 if len(linked)==2:
  for j,i,a,q in linked:centers[j]=q
 elif linked:
  j,i,a,q=linked[0];old=centers[j];perp=(q-old)-d*np.dot(q-old,d);centers[1-j]+=perp;centers[j]=q
  if np.dot(centers[1]-centers[0],d)<10:centers[1-j]=q+(1 if j==0 else -1)*d*10
 start,end=centers
 if np.linalg.norm(end-start)<1:raise RuntimeError('Degenerate straight '+handle)
 a_world,b_world=world_mm(start,level),world_mm(end,level);v,f=straight_mesh(a_world,b_world,w,h,up)
 part_id=f'L{level}-S-{handle}'
 parts.append(dict(id=part_id,category='straight',layer=level,kind='vertical_straight' if is_vertical else 'horizontal_straight',label='竖向直段' if is_vertical else '水平直段',handle=handle,v=v,f=f,width_mm=w,height_mm=h,
  original_path_mm=[p.tolist() for p in ends],assembled_centerline_mm=[a_world.tolist(),b_world.tolist()],length_mm=float(np.linalg.norm(end-start)),
  up=up.tolist(),links=[dict(end=j,fitting=placements[i]['model']['id'],port=placements[i]['model']['ports'][a['port']]['name']) for j,i,a,q in linked]))
 for j in (0,1):
  baseline=ends[j]+up*h/2;adjust=float(np.linalg.norm(centers[j]-baseline))
  report=dict(straight=part_id,end=j,endpoint_adjustment_mm=round(adjust,3),original_reference_mm=baseline.tolist(),assembled_CAD_center_mm=centers[j].tolist(),connected=(handle,j) in claims)
  endpoint_report.append(report)
 for j,i,a,q in linked:
  fit=placements[i]['model'];port=fit['ports'][a['port']];normal=placements[i]['R']@np.array(port['outward_normal']);expected=d if j==0 else -d
  actual_gap=float(np.linalg.norm(centers[j]-q));mismatch=abs(port['width_mm']-w)>1 or abs(port['height_mm']-h)>1
  conn=dict(fitting=fit['id'],port=port['name'],straight=part_id,straight_end=j,gap_mm=actual_gap,normal_error_deg=float(np.degrees(np.arccos(np.clip(np.dot(normal,expected),-1,1)))),
            fitting_section_mm=[port['width_mm'],port['height_mm']],straight_section_mm=[w,h],section_mismatch=mismatch)
  connections.append(conn)
  if mismatch:problems.append(dict(type='section_mismatch',**conn))
for i,pi,j,pj,initial_distance in direct:
 p,q=parts[i],parts[j];pa=p['ports'][pi];pb=q['ports'][pj];dist=float(np.linalg.norm(np.array(pa['center_mm'])-pb['center_mm']))
 connections.append(dict(fitting=p['id'],port=pa['name'],other_fitting=q['id'],other_port=pb['name'],gap_mm=dist))
 if dist>1:problems.append(dict(type='direct_fitting_gap',a=p['id'],b=q['id'],gap_mm=dist))
for i,pi,q,n in unclaimed:
 if any((a==i and api==pi) or (b==i and bpi==pi) for a,api,b,bpi,_ in direct):continue
 problems.append(dict(type='unmatched_fitting_port',fitting=placements[i]['model']['id'],port=placements[i]['model']['ports'][pi]['name']))

revision=apply_revision(parts,connections,problems,straight_mesh)
endpoint_report=[]
for p in parts:
 if p['category']!='straight':continue
 for j in (0,1):
  baseline=world_mm(np.array(p['original_path_mm'][j])+np.array(p['up'])*p['height_mm']/2,p['layer']);actual=np.array(p['assembled_centerline_mm'][j]);delta=actual-baseline
  endpoint_report.append(dict(straight=p['id'],end=j,endpoint_adjustment_mm=round(float(np.linalg.norm(delta)),3),original_world_center_mm=baseline.tolist(),assembled_world_center_mm=actual.tolist(),connected=any(link['end']==j for link in p['links'])))

def export_obj(selected,path):
 lines=['# units=m; Z-up; EL100 is local Z=0'];offset=1
 for p in selected:
  lines.append('o '+p['id']);lines+=['v '+' '.join(f'{x/1000:.7f}' for x in v) for v in p['v']]
  lines+=['f '+' '.join(str(int(i)+offset) for i in face) for face in p['f']];offset+=len(p['v'])
 path.write_text('\n'.join(lines)+'\n',encoding='ascii')
def export_glb(selected,path):
 chunks=[];views=[];accessors=[];meshes=[];nodes=[dict(name=f'L{i}_EL{LAYERS[i]["EL"]}',children=[]) for i in range(1,4)];offset=0
 for p in selected:
  v=p['v'].astype(np.float32)/1000;v=v[:,[0,2,1]];v[:,2]*=-1;faces=p['f'];normals=np.zeros_like(v)
  for f in faces:
   n=np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]);n/=np.linalg.norm(n);normals[f]=n
  start=len(accessors)
  for data,ctype,type_,count,target in [(v.astype('<f4').tobytes(),5126,'VEC3',len(v),34962),(normals.astype('<f4').tobytes(),5126,'VEC3',len(v),34962),(faces.astype('<u4').tobytes(),5125,'SCALAR',faces.size,34963)]:
   views.append(dict(buffer=0,byteOffset=offset,byteLength=len(data),target=target));a=dict(bufferView=len(views)-1,componentType=ctype,count=count,type=type_)
   if len(accessors)==start:a.update(min=v.min(0).tolist(),max=v.max(0).tolist())
   accessors.append(a);chunks.append(data);offset+=len(data)
  meshes.append(dict(name=p['id'],primitives=[dict(attributes=dict(POSITION=start,NORMAL=start+1),indices=start+2,material=p['layer']-1)]))
  nodes[p['layer']-1]['children'].append(len(nodes));nodes.append(dict(name=p['id'],mesh=len(meshes)-1,extras=dict(id=p['id'],category=p['category'],source_handle=p['handle'])))
 def color(hex_):return [int(hex_[i:i+2],16)/255 for i in (1,3,5)]+[1]
 g=dict(asset=dict(version='2.0',generator='HydrolysisTrayAssembly 0.1'),scene=0,scenes=[dict(nodes=[0,1,2])],nodes=nodes,meshes=meshes,materials=[dict(name=f'L{i}',doubleSided=True,pbrMetallicRoughness=dict(baseColorFactor=color(LAYERS[i]['color']),metallicFactor=.4,roughnessFactor=.45)) for i in range(1,4)],buffers=[dict(byteLength=offset)],bufferViews=views,accessors=accessors)
 g['asset']['extras']=dict(geographic_axes=dict(east='+X',north='-Z',up='+Y'),elevation_origin_EL=100,assembly_revision='0.2')
 j=json.dumps(g,separators=(',',':')).encode();j+=b' '*((-len(j))%4);b=b''.join(chunks);b+=b'\0'*((-len(b))%4)
 path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b)

for i in [0,1,2,3]:
 selected=parts if i==0 else [p for p in parts if p['layer']==i];name='三层桥架' if i==0 else f'L{i}_桥架'
 export_glb(selected,OUT/'models'/f'{name}.glb');export_obj(selected,OUT/'models'/f'{name}.obj')
custom=[p for p in parts if p.get('source_kind')=='computed_from_user_confirmed_riser_connection']
export_glb(custom,OUT/'models'/'L3-X01_45度乙字弯.glb');export_obj(custom,OUT/'models'/'L3-X01_45度乙字弯.obj')
(OUT/'models'/'L3-X01_参数.json').write_text(json.dumps(custom[0]['parameters'],ensure_ascii=False,indent=2),encoding='utf-8')
metadata=[];display=[]
for p in parts:
 meta={k:v for k,v in p.items() if k not in ('v','f')};meta['bbox_mm']=[p['v'].min(0).tolist(),p['v'].max(0).tolist()];meta['triangles']=len(p['f']);metadata.append(meta)
 display.append(dict(id=p['id'],layer=p['layer'],category=p['category'],v=np.round(p['v']/1000,6).tolist(),f=p['f'].tolist()))
manifest=dict(version='0.2-direction-and-riser',units='mm',coordinate_system='East +X, North +Y, Z-up; local Z=0 corresponds to EL100',layers=LAYERS,source_library_version=CATALOG['version'],parts=metadata,revision=revision,
 connections=connections,issues=problems,placement_policy='Approved fitting geometry is reused at unit magnitude scale, with rotation/translation; L2-C18 permits a recorded local-Y mirror instance to follow CAD installation direction. Straight endpoints adjust to interfaces. Layer CAD origins from building block inserts. No invented links between layers.')
(OUT/'assembly.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'viewer_data.js').write_text('window.ASSEMBLY='+json.dumps(manifest,ensure_ascii=False)+';\nwindow.GEOMETRY='+json.dumps(display,separators=(',',':'))+';',encoding='utf-8')
(OUT/'reports'/'endpoint_adjustments.json').write_text(json.dumps(endpoint_report,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'reports'/'接口核对.csv').open('w',encoding='utf-8-sig',newline='') as f:
 keys=['kind','fitting','port','straight','straight_end','other_fitting','other_port','other_straight','other_straight_end','alignment','gap_mm','center_gap_mm','normal_error_deg','fitting_section_mm','straight_section_mm','section_mismatch','accepted_alignment'];w=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore');w.writeheader();w.writerows(connections)
for m in FITS:assert hashlib.sha256((LIB/m['files']['glb']).read_bytes()).hexdigest()==library_hashes[m['id']]
summary=dict(parts=len(parts),library_fittings=len(FITS),derived_fittings=len(custom),straights=len(PATHS),solver=res.message,direct_contacts=len(direct),max_contact_gap_mm=max(c['gap_mm'] for c in connections),issues=problems,revision=revision,
 endpoint_adjustments_over_100mm=sum(r['endpoint_adjustment_mm']>100 for r in endpoint_report),max_endpoint_adjustment_mm=max(r['endpoint_adjustment_mm'] for r in endpoint_report),library_GLBS_unchanged=True)
(OUT/'reports'/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True,indent=2))

# Standalone visual QA: three layer overviews and stacked model, emphasizing the
# actual fitted geometry rather than drawing placeholder connector boxes.
fig=plt.figure(figsize=(17,10))
for n in (1,2,3,0):
 ax=fig.add_subplot(2,2,4 if n==0 else n,projection='3d');subset=parts if n==0 else [p for p in parts if p['layer']==n]
 for p in subset:
  v=p['v']/1000;ax.add_collection3d(Poly3DCollection(v[p['f']],facecolors=LAYERS[p['layer']]['color'],edgecolors='none',alpha=1))
 ax.set_xlim(0,46);ax.set_ylim(0,74);ax.set_zlim(0,20);ax.set_box_aspect([44,72,28]);ax.view_init(28,-57)
 ax.set_title('Stacked | EL100 / 106 / 112' if n==0 else f'L{n} | EL{LAYERS[n]["EL"]} | fittings + straight trays',fontsize=12)
 ax.set_xlabel('X (m)');ax.set_ylabel('Y (m)');ax.set_zlabel('Z above EL100 (m)');ax.tick_params(labelsize=7)
fig.suptitle('Hydrolysis | Three-layer cable tray assembly | v0.2 | East +X / North +Y',fontsize=18);fig.tight_layout(rect=[0,0,1,.95]);fig.savefig(OUT/'previews'/'三层桥架总览.png',dpi=150);plt.close(fig)
