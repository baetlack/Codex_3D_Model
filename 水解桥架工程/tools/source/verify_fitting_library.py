from pathlib import Path
import json,struct,hashlib,math,zipfile
import numpy as np
root=Path(__file__).parent;lib=root/'连接件模型库'
c=json.loads((lib/'catalog.json').read_text(encoding='utf-8'))
assert c['count']==47==len(c['models'])
assert len({m['id'] for m in c['models']})==47
assert len({m['source_screenshot_SHA256'] for m in c['models']})==47
reports=[]
for m in c['models']:
 p=lib/m['files']['glb'];raw=p.read_bytes();magic,ver,size=struct.unpack_from('<III',raw)
 assert magic==0x46546c67 and ver==2 and size==len(raw)
 jsize,jtype=struct.unpack_from('<II',raw,12);assert jtype==0x4e4f534a
 g=json.loads(raw[20:20+jsize]);offset=20+jsize;bsize,btype=struct.unpack_from('<II',raw,offset)
 assert btype==0x004e4942 and bsize==len(raw)-(offset+8)
 blob=raw[offset+8:];bv=g['bufferViews'];ac=g['accessors']
 for view in bv:assert view['byteOffset']+view['byteLength']<=len(blob)
 pts=np.frombuffer(blob[bv[0]['byteOffset']:bv[0]['byteOffset']+bv[0]['byteLength']],dtype='<f4').reshape(-1,3)
 normals=np.frombuffer(blob[bv[1]['byteOffset']:bv[1]['byteOffset']+bv[1]['byteLength']],dtype='<f4').reshape(-1,3)
 ids=np.frombuffer(blob[bv[2]['byteOffset']:bv[2]['byteOffset']+bv[2]['byteLength']],dtype='<u4').reshape(-1,3)
 assert np.all(np.isfinite(pts)) and len(pts)>0 and ids.min()>=0 and ids.max()<len(pts)
 assert np.allclose(np.linalg.norm(normals,axis=1),1,atol=1e-5)
 area=np.linalg.norm(np.cross(pts[ids[:,1]]-pts[ids[:,0]],pts[ids[:,2]]-pts[ids[:,0]]),axis=1)
 assert np.all(area>1e-13)
 assert np.allclose(pts.min(0),ac[0]['min']) and np.allclose(pts.max(0),ac[0]['max'])
 for port in m['ports']:
  assert all(math.isfinite(v) for v in port['position_mm']) and port['width_mm']>0 and port['height_mm']>0
  assert abs(np.linalg.norm(port['outward_normal'])-1)<1e-7
  assert abs(np.dot(port['outward_normal'],port['section_up']))<1e-7
 assert len(m['ports'])==(3 if m['kind'] in ('tee','vertical_tee') else 2)
 for key in ['obj','parameters']:assert (lib/m['files'][key]).is_file()
 assert (lib/'previews'/f'{m["id"]}.png').is_file()
 assert hashlib.sha256((lib/m['source_screenshot']).read_bytes()).hexdigest()==m['source_screenshot_SHA256']
 reports.append({'id':m['id'],'triangles':len(ids),'ports':len(m['ports']),'glb_bytes':len(raw),'checks':'passed'})
result={'models':47,'GLB_structure':'passed','finite_nonzero_triangles':'passed','unit_normals':'passed','interface_metadata':'passed','all_screenshots_preserved':'passed','scope':'File and mesh structure only; not dimensional validation against CAD, not manifold/boolean validation. Browser UI not manually tested.','details':reports}
byid={m['id']:m for m in c['models']}
def obj_geometry(ident):
 return '\n'.join(line for line in (lib/byid[ident]['files']['obj']).read_text().splitlines() if line.startswith(('v ','f ')))
for a,b in [('L2-C04','L2-C07'),('L3-C02','L3-C15')]:
 assert obj_geometry(a)==obj_geometry(b),(a,b,'geometry differs')
 assert byid[a]['ports']==byid[b]['ports']
result['identical_geometry_pairs']=[['L2-C04','L2-C07'],['L3-C02','L3-C15']]
for m in c['models']:
 for view in m.get('source_views',[]):assert hashlib.sha256((lib/view['path']).read_bytes()).hexdigest()==view['SHA256']
for key in ['run_mm','offset_mm','straight_in_mm','straight_out_mm','diagonal_projection_mm']:
 value=byid['L2-C18']['parameters'][key];assert value==int(value)
assert byid['L2-C18']['parameters']['run_mm']==1175
assert byid['L2-C18']['parameters']['offset_mm']==-850
offset_ports=byid['L2-C18']['ports']
assert offset_ports[1]['position_mm'][1]-offset_ports[0]['position_mm'][1]==-850
for ident,bounds in [('L3-C02',[800,200,400]),('L3-C04',[1100,500,500]),('L1-C07',[480,400,400]),('L3-C10',[350,500,400])]:
 lo,hi=byid[ident]['mesh']['bbox_mm'];assert np.allclose(np.array(hi)-lo,bounds),(ident,'projection envelope mismatch')
for ident in ['L1-C07','L3-C10']:
 params=byid[ident]['parameters'];assert params['diagonal_projection_mm']==params['rise_mm']==200
for ident in ['L2-C02','L2-C05']:
 params=byid[ident]['parameters'];assert (params['w1'],params['w2'],params['w3'])==(500,200,500)
source_images=list((root/'连接件').glob('*.png'))
for p in source_images:assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256((lib/'screenshots'/p.name).read_bytes()).digest()
result['preserved_source_images']=len(source_images)
result['revision_envelopes_and_dimensions']='passed'
(lib/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
archive=root/'连接件模型库_v1.2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in lib.rglob('*'):
  if p.is_file():z.write(p,p.relative_to(root))
print(f'47 models passed structure, triangle, normal, port, source checks. ZIP {archive.stat().st_size} bytes')
