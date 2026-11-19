"""First-class acceptance: preserve prior modules, check real support and installation geometry."""
from pathlib import Path
import sys,json,hashlib,struct
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/C41B02';BASE=ROOT/'版本/1.0/快照'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as au

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run():
 frozen=json.loads((ROOT/'版本/1.0/冻结清单.json').read_text())
 for name,digest in frozen['files'].items():assert sha(BASE/name)==digest,name
 # None of the previous actual model files may be rewritten, including the bridge
 # geometry, building mesh and the other 94 equipment instances' source assets.
 for name,digest in frozen['original_source_hashes'].items():
  if name.endswith(('.obj','.glb','model_data.js')):assert sha(REPO/name)==digest,name
 p=json.loads((OUT/'设备/参数.json').read_text());new=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');old=ck.script(BASE/'水解桥架工程/models/设备/设备基础_20261106/设备净模/C41B02/model_data.js','MODEL_PARTS')
 assert sha(REPO/p['source_drawing'])==p['source_sha256']
 assert p['tank']['outside_diameter_mm']==5500 and p['tank']['straight_shell_height_mm']==5000
 assert p['mixer']['height_above_shell_top_mm']==2185
 catalog=json.loads((ROOT/'catalog.json').read_text());oldcatalog=json.loads((BASE/'水解设备模型库/catalog.json').read_text());oldrows={p['id']:p for p in oldcatalog['models']}
 for row in catalog['models']:
  if row['id'].startswith('C41B02'):
   assert row['w']==5500 and row['h']==5000 and row['pos_el']==112.15
   assert row['current_files']['model']=='版本/2.0/C41B02/设备/model_data.js'
  else:assert row==oldrows[row['id']],row['id']
 byname={a['name']:a for a in new};preserved=0
 from collections import defaultdict
 candidates=defaultdict(list)
 for a in new:candidates[a['name']].append(a)
 for part in old:
  if part['name'].startswith(('接口_','06_')) or part['name'] in ['Lid_edge_rim','Tank_cover_lid']:continue
  match=candidates[part['name']].pop(0)
  assert match['faces']==part['faces']
  assert np.allclose(match['vertices'],np.array(part['vertices'])+[0,0,160],atol=1e-8,rtol=0),part['name'];preserved+=1
 # Exposed rim and cover meet at one edge; no coincident cylindrical skin.
 assert max(v[2] for v in byname['Lid_edge_rim']['vertices'])==min(v[2] for v in byname['Lid_gasket']['vertices'])
 assert max(v[2] for v in byname['Lid_gasket']['vertices'])==min(v[2] for v in byname['Tank_cover_lid']['vertices'])
 previous=OUT/'历史/2.0-C41B02-01'
 frozen02=json.loads((previous/'冻结清单.json').read_text())
 for name,digest in frozen02['files'].items():assert sha(previous/name)==digest,name
 for file in (previous/'基础').iterdir():assert sha(OUT/'基础'/file.name)==sha(file),file.name
 old02=ck.script(previous/'设备/model_data.js','MODEL_PARTS')
 for part in old02:
  if part['name'].startswith('设备支撑_'):assert byname[part['name']]==part,part['name']
 from test_c41b02_topside import verify_topside
 topside=verify_topside(new)
 caps=[q for q in new if '盘管检修盖' in q['name']];assert len(caps)==8
 assert len(p['ports'])==33
 for label in ['k','b','j']:assert sum(q['id'].startswith(label) for q in p['ports'])==8
 assert not any('顶盖法兰' in q['name'] for q in new)
 support=[q for q in new if q['name'].startswith('设备支撑_')];assert len(support)==27
 sv=np.vstack([q['vertices'] for q in support]);assert sv[:,2].min()==0 and sv[:,2].max()==160
 assert np.max(np.linalg.norm(sv[:,:2],axis=1))<2850
 for name in ['model_data.js','C41B02.glb','C41B02.obj','C41B02.mtl']:
  assert sha(OUT/'基础'/name)==sha(BASE/'水解桥架工程/models/设备/设备基础_20261106/C41B02'/name),name
 base=ck.script(OUT/'基础/model_data.js','MODEL_PARTS');bv=np.vstack([q['vertices'] for q in base]);assert bv[:,2].max()==0 and bv[:,2].min()==-150
 assert max(q[2] for q in byname['Tank_shell_OD5500_H5000']['vertices'])==5160
 assert max(v[2] for q in new for v in q['vertices'])==7345
 for q in new:
  v=np.asarray(q['vertices']);assert np.isfinite(v).all()
  for f in q['faces']:assert min(f)>=0 and max(f)<len(v)
 raw=(OUT/'设备/C41B02.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
 size=struct.unpack_from('<I',raw,12)[0];g=json.loads(raw[20:20+size]);assert len(g['meshes'])==len(new)
 assert all(np.isfinite(a['min']).all() and np.isfinite(a['max']).all() for a in g['accessors'] if 'min' in a)
 before=json.loads((BASE/'水解总装工程/assembly.json').read_text());after=json.loads((REPO/'水解总装工程/assembly.json').read_text())
 assert before['unplaced']==after['unplaced'] and len(after['equipment'])==72
 b={q['id']:q for q in before['equipment']};actual={q['id']:q for q in after['equipment']};install=json.loads((OUT/'安装表.json').read_text());assert len(install)==5
 for ident,q in actual.items():
  if q['asset']!='C41B02':assert q==b[ident],ident
  else:
   for key in ['position_mm','rotation_deg','mirror_y']:assert q[key]==b[ident][key],(ident,key)
   assert '待核' in q['orientation_status'] and '待核' in q['z_status']
 assert after['assets']['C41B02']['source']=='水解设备模型库/版本/2.0/C41B02/设备/model_data.js'
 # Actual new mesh against the complete 120-column scope, 76 beams, all bridge
 # pieces, and the other equipment, without treating intended bearing contact as a clash.
 bridge,columns=au.load();beams=[]
 for q in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if q['kind']!='frame':continue
  for i in range(len(q['vertices'])//8):
   off=i*8;faces=[[j-off for j in f] for f in q['faces'] if all(off<=j<off+8 for j in f)]
   beams.append(ck.object_mesh(q['name']+'-'+str(i),'beam',ck.tri([{'vertices':q['vertices'][off:off+8],'faces':faces}])))
 others=[];closed={};cache={}
 for q in after['equipment']:
  if q['asset']=='C41B02':continue
  source=after['assets'][q['asset']]['source'];parts=cache.setdefault(source,ck.script(REPO/source,'MODEL_PARTS'))
  others.append(ck.object_mesh(q['id'],'equipment',ck.tri(parts,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))))
  closed[q['id']]=ck.closed_components(parts,q['position_mm'],q['rotation_deg'],q.get('mirror_y',False))
 hits=[];rows=[]
 for q in install:
  mesh=ck.object_mesh(q['id'],'equipment',ck.tri(new,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False)))
  for obstacle in columns+beams+bridge+others:
   overlap=np.minimum(mesh['high'],obstacle['high'])-np.maximum(mesh['low'],obstacle['low'])
   if np.any(overlap<=.1):continue
   proof=ck.column_penetration(mesh,obstacle,.1) if obstacle['kind'] in ['structure','room_column','stair_column','beam'] else ck.surface(mesh,obstacle)
   contains=any(ck.inside(mesh['t'][0,0],t) for t in closed.get(obstacle['id'],[]))
   if proof is not None or contains:hits.append([q['id'],obstacle['id'],obstacle['kind']])
  z=q['position_mm'][2];rows.append({'id':q['id'],'foundation_top_EL':100+z/1000,'support_bottom_EL':100+z/1000,'support_gap_mm':float(sv[:,2].min()-bv[:,2].max()),'tank_bottom_EL':100+(z+160)/1000,'tank_top_EL':100+(z+5160)/1000,'mixer_top_EL':100+(z+7345)/1000,'new_orientation_status':q['orientation_status']})
 assert not hits,hits
 report={'status':'passed_with_declared_pending_installation_basis','revision':'2.0-C41B02-02','topside_reference_check':topside,'class':'C41B02','parts':len(new),'preserved_rigid_parts':preserved,'new_port_records':33,'k_covers':8,'items':5,'other_items_unchanged':94,'columns_checked':len(columns),'beams_checked':len(beams),'bridge_parts_checked':len(bridge),'other_placed_equipment_checked':len(others),'intersections':hits,'support_records':rows,'confirmed_tank_and_mixer_dimensions':'passed','foundation_geometry_unchanged':True,'original_models_and_1_0_hashes':'passed','limits':['POS EL承托面定义待确认，5台安装Z状态未标确认。','新接口绝对方位待工艺图，原旋转/镜像只作暂用。','未标法兰厚度、踏步板层位及缺失零件详图仍有外观假设，见参数。']}
 (OUT/'校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='support_records'},ensure_ascii=False))
if __name__=='__main__':run()
