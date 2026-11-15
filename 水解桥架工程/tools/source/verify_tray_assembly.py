from pathlib import Path
import json,struct,hashlib,zipfile
import numpy as np
ROOT=Path(__file__).parent;OUT=ROOT/'三层桥架模型';LIB=ROOT/'连接件模型库'
manifest=json.loads((OUT/'assembly.json').read_text(encoding='utf-8'));parts={p['id']:p for p in manifest['parts']}
assert len(parts)==112
assert sum(p['category']=='fitting' for p in parts.values())==48
assert sum(p['category']=='straight' for p in parts.values())==64
for level,expected in [(1,(9,13)),(2,(21,27)),(3,(18,24))]:
 assert tuple(sum(p['layer']==level and p['category']==category for p in parts.values()) for category in ('fitting','straight'))==expected
def read_obj(path):
 vertices=[];faces=[]
 for line in path.read_text().splitlines():
  if line.startswith('v '):vertices.append([float(v) for v in line.split()[1:]])
  elif line.startswith('f '):faces.append([int(v)-1 for v in line.split()[1:]])
 return np.array(vertices),np.array(faces)
allv,allf=read_obj(OUT/'models'/'三层桥架.obj');cursor=0
library_catalog={p['id']:p for p in json.loads((LIB/'catalog.json').read_text(encoding='utf-8'))['models']}
for p in manifest['parts']:
 if p['category']=='fitting' and 'source_library_glb_SHA256' in p:
  source=library_catalog[p['id']];v,f=read_obj(LIB/source['files']['obj']);placement=p['placement'];R=np.array(placement['orientation']);t=np.array(placement['translation_mm'])/1000
  assert np.allclose(R.T@R,np.eye(3),atol=1e-9)
  assert np.allclose(allv[cursor:cursor+len(v)],v@R.T+t,atol=1e-7)
  assert hashlib.sha256((LIB/source['files']['glb']).read_bytes()).hexdigest()==p['source_library_glb_SHA256']
  cursor+=len(v)
 else:cursor+=p['triangles']*3
assert cursor==len(allv)
assert np.all(np.isfinite(allv))
for conn in manifest['connections']:
 assert conn['gap_mm']<1e-3
 if conn.get('kind')=='straight_splice':
  a=parts[conn['straight']]['assembled_centerline_mm'][conn['straight_end']];b=parts[conn['other_straight']]['assembled_centerline_mm'][conn['other_straight_end']];assert np.allclose(a,b,atol=1e-5)
 elif 'straight' in conn:
  source=parts[conn['fitting']];port=next(p for p in source['ports'] if p['name']==conn['port']);straight=parts[conn['straight']]
  assert np.allclose(conn['contact_on_fitting_mm'],conn['contact_on_straight_mm'],atol=1e-5)
  if conn.get('alignment','center')=='center':assert np.allclose(port['center_mm'],straight['assembled_centerline_mm'][conn['straight_end']],atol=1e-5)
  assert conn['normal_error_deg']<.2
 else:
  a=next(p for p in parts[conn['fitting']]['ports'] if p['name']==conn['port'])
  b=next(p for p in parts[conn['other_fitting']]['ports'] if p['name']==conn['other_port'])
  assert np.allclose(a['center_mm'],b['center_mm'],atol=1e-5)
assert manifest['issues']==[]
rules={(c.get('fitting'),c.get('port')):c for c in manifest['connections'] if c.get('accepted_alignment')}
assert set(rules)=={('L3-C03','A'),('L3-C17','A'),('L3-C04','C')}
assert np.allclose(parts['L3-S-37C11']['up'],parts['L2-S-37C18']['up'])
assert np.allclose(np.array(parts['L3-S-37C11']['assembled_centerline_mm'])[:,:2],np.array(parts['L2-S-37C18']['assembled_centerline_mm'])[:,:2])
offset=parts['L3-X01']['parameters'];path=np.array(offset['path_centerline_mm']);diagonal=path[2]-path[1]
assert abs(np.degrees(np.arctan2(diagonal[2],np.linalg.norm(diagonal[:2])))-45)<1e-9
assert np.allclose(path[0],parts['L3-S-37C11']['assembled_centerline_mm'][0])
assert np.allclose(path[-1],parts['L3-S-37C12']['assembled_centerline_mm'][1])
for p in parts.values():
 if p['category']=='straight':assert p['length_mm']>=9.999
glb_checks=[]
for file in (OUT/'models').glob('*.glb'):
 raw=file.read_bytes();magic,version,total=struct.unpack_from('<III',raw);assert magic==0x46546c67 and version==2 and total==len(raw)
 size,tag=struct.unpack_from('<II',raw,12);assert tag==0x4e4f534a;g=json.loads(raw[20:20+size]);offset=20+size
 bsize,btag=struct.unpack_from('<II',raw,offset);assert btag==0x004e4942;blob=raw[offset+8:];assert len(blob)==bsize
 counts=0
 for mesh in g['meshes']:
  primitive=mesh['primitives'][0];pa=g['accessors'][primitive['attributes']['POSITION']];na=g['accessors'][primitive['attributes']['NORMAL']];ia=g['accessors'][primitive['indices']]
  def values(accessor,dtype,width):
   bv=g['bufferViews'][accessor['bufferView']];start=bv['byteOffset'];assert start+bv['byteLength']<=len(blob)
   return np.frombuffer(blob[start:start+bv['byteLength']],dtype=dtype).reshape(-1,width)
  p=values(pa,'<f4',3);n=values(na,'<f4',3);i=values(ia,'<u4',3)
  assert np.all(np.isfinite(p)) and np.all(np.isfinite(n)) and np.max(i)<len(p)
  area=np.linalg.norm(np.cross(p[i[:,1]]-p[i[:,0]],p[i[:,2]]-p[i[:,0]]),axis=1)
  assert np.all(area>1e-12),(file,mesh['name'],'zero triangle')
  assert np.allclose(np.linalg.norm(n,axis=1),1,atol=2e-5)
  counts+=len(i)
 expected=112 if file.stem=='三层桥架' else 1 if file.stem.startswith('L3-X01') else {1:22,2:48,3:42}[int(file.stem[1])]
 assert len(g['meshes'])==expected
 glb_checks.append(dict(file=file.name,parts=len(g['meshes']),triangles=counts,status='passed'))
report=dict(status='passed',parts=112,library_fittings=47,derived_fittings=1,straights=64,connections=len(manifest['connections']),library_assets_unchanged=True,
 fitting_shapes_isometric=True,mirrored_instances=[p['id'] for p in parts.values() if p['category']=='fitting' and p['placement']['mirrored_local_Y']],
 contacts_aligned=True,accepted_edge_alignment_rules=3,unresolved_contact_issues=0,continuous_riser_axis_and_orientation=True,new_offset_diagonal_angle_deg=45,files=glb_checks,
 scope='Checks confirm files, geometric reuse and user-defined floor/side contacts and riser connectivity, not full-scene clash detection or fabrication status.')
(OUT/'reports'/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
