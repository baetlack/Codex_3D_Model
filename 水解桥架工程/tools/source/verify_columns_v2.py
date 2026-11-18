"""Verify actual exported 2.0 geometry against the immutable 1.0 model and all columns."""
import json
import numpy as np
from rectify_columns_v2 import Rectification,PROJECT,REPO,ck,audit,frozen_check,sha

def verify():
 frozen_check()
 archive=PROJECT/'版本/2.0';manifest=json.loads((archive/'版本清单.json').read_text())
 for name,digest in manifest['files'].items():assert sha(archive/name)==digest,name
 assert sha(archive/'models/整体/viewer_data.js')==sha(PROJECT/'models/整体/viewer_data.js')
 r=Rectification();out=PROJECT/'models/整体';d=json.loads((out/'assembly.json').read_text());report=json.loads((out/'reports/2.0整改核对.json').read_text())
 assert d['version']=='2.0-column-contact'
 for name,digest in report['basis_sha256'].items():assert sha(REPO/name)==digest,name
 x=np.concatenate([p['reference_translation_mm'][:2] for p in report['changes']]);expected,_=r.rebuild(x)
 obj=np.array([[float(x)*1000 for x in line.split()[1:]] for line in (out/'models/三层桥架.obj').read_text().splitlines() if line.startswith('v ')])
 assert np.max(abs(obj-np.vstack([p['v'] for p in expected])))<.000051
 actual={p['id']:p for p in d['parts']};geo=ck.script(out/'viewer_data.js','GEOMETRY');bridges=[];max_error=0
 for e,g in zip(expected,geo):
  a=actual[e['id']];assert a['id']==g['id'];v=np.array(g['v'])*1000;faces=np.array(g['f'])
  error=float(np.max(abs(v-e['v'])));max_error=max(error,max_error);assert error<.00051,e['id'];assert np.array_equal(faces,e['f'])
  old=r.parts[r.ix[e['id']]]
  if e['category']=='fitting':
   for key in ['orientation','scale','mirrored_local_Y']:assert a['placement'][key]==old['placement'][key]
   for op,ap in zip(old['ports'],a['ports']):
    for key in ['normal','up','width_mm','height_mm']:assert op[key]==ap[key]
    assert np.allclose(np.array(ap['center_mm'])-op['center_mm'],r.delta(x,a['id']),atol=1e-6)
  else:
   line=np.array(a['assembled_centerline_mm']);oldline=np.array(old['assembled_centerline_mm']);assert np.allclose(line[:,2],oldline[:,2],atol=1e-6)
   assert a['width_mm']==old['width_mm'] and a['height_mm']==old['height_mm'] and a['up']==old['up']
   assert np.linalg.norm(np.cross(line[1]-line[0],oldline[1]-oldline[0]))<.01
   assert a['length_mm']>=9.999 and np.allclose(line,e['assembled_centerline_mm'],atol=1e-5)
  bridges.append(ck.object_mesh(g['id'],'bridge',v[faces]))
 hits=r.penetrations(bridges);assert len(r.columns)==120 and len(bridges)==112 and not hits,[(b['id'],c['id']) for b,c in hits]
 # Independently check every actual interface, including accepted offsets and splice.
 for c in d['connections']:
  if c.get('kind')=='straight_splice':
   assert np.allclose(actual[c['straight']]['assembled_centerline_mm'][c['straight_end']],actual[c['other_straight']]['assembled_centerline_mm'][c['other_straight_end']],atol=1e-5)
  elif 'other_fitting' in c:
   get=lambda key,port:next(p for p in actual[c[key]]['ports'] if p['name']==c[port])['center_mm']
   assert np.allclose(get('fitting','port'),get('other_fitting','other_port'),atol=1e-5)
  else:
   op=next(p for p in r.parts[r.ix[c['fitting']]]['ports'] if p['name']==c['port']);ap=next(p for p in actual[c['fitting']]['ports'] if p['name']==c['port'])
   oldpoint=r.parts[r.ix[c['straight']]]['assembled_centerline_mm'][c['straight_end']];newpoint=actual[c['straight']]['assembled_centerline_mm'][c['straight_end']]
   assert np.allclose(np.array(newpoint)-ap['center_mm'],np.array(oldpoint)-op['center_mm'],atol=1e-5)
 after,scope=r.other_collisions(bridges);new=set(after)-{tuple(p) for p in report['other_geometry_pairs_before']};assert not new,new
 result={'status':'passed','version':'2.0','frozen_1_0_hashes':'passed','parts':112,'columns':120,'penetrations':0,'interfaces':len(d['connections']),'max_viewer_rounding_error_mm':max_error,'unchanged_fitting_shape_orientation_section_elevation':True,'straight_interfaces_and_direction':'passed','new_other_geometry_pairs':[],**scope}
 (out/'reports/2.0独立验证.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':verify()
