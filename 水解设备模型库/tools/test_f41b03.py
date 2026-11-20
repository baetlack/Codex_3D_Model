"""Native-plan validation, real empty holes and a proof of non-bearing for F41B03."""
from pathlib import Path
import hashlib,json,math,struct,sys
import ezdxf,numpy as np,xlrd
from ezdxf.disassemble import recursive_decompose
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/F41B03'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as au
def box(q):
 v=np.asarray(q['vertices']);return v.min(0),v.max(0)
def run():
 pin=json.loads((OUT/'本批保护基准.json').read_text())
 for name,digest in pin['unchanged_files'].items():assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==digest,name
 p=json.loads((OUT/'设备/参数.json').read_text());parts=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');old=ck.script(REPO/'水解设备模型库/示图建模_20260521/模型/F41B03/model_data.js','MODEL_PARTS')
 assert len(parts)==5 and parts[0]==old[0],'The straight-section mesh, normals and materials must remain exact'
 assert sum(q['name']=='本体_端缘' for q in old)==2 and not any(q['name']=='本体_端缘' for q in parts)
 row=xlrd.open_workbook(REPO/p['ledger_source']).sheet_by_name('水解').row_values(50)
 assert row[1]=='F41B03' and '1000' in row[3] and row[8]==1,row
 d=ezdxf.readfile(REPO/p['source_drawing']);assert hashlib.sha256((REPO/p['source_drawing']).read_bytes()).hexdigest()==p['source_sha256']
 assert d.entitydb['3623'].dxf.radius==500 and d.entitydb['3626'].dxf.radius==550 and d.entitydb['3626'].dxf.layer=='中心线'
 center=np.array(d.entitydb['3623'].dxf.center)[:2]
 native=[np.array(c.ocs().to_wcs(c.dxf.center))[:2]-center for c in recursive_decompose([d.entitydb['3625']]) if c.dxftype()=='CIRCLE']
 assert len(native)==4
 for xy in native:assert abs(np.linalg.norm(xy)-550)<.00001
 assert p['ports']==[] and '直筒段' in p['modeled_scope']
 for q in parts:
  v=np.asarray(q['vertices']);assert np.isfinite(v).all(),q['name'];edges={}
  for f in q['faces']:
   assert min(f)>=0 and max(f)<len(v)
   for a,b in zip(f,f[1:]+f[:1]):edge=tuple(sorted([a,b]));edges[edge]=edges.get(edge,0)+1
  assert all(n==2 for n in edges.values()),q['name']
 foundation=ck.script(OUT/'基础/model_data.js','MODEL_PARTS');base_src=REPO/'水解桥架工程/models/设备/设备基础_20261106/F41B03'
 for path in base_src.iterdir():
  if path.suffix in ['.js','.glb','.obj','.mtl']:assert (OUT/'基础'/path.name).read_bytes()==path.read_bytes(),path.name
 foundation_dxf=ezdxf.readfile(REPO/'水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf')
 for h in ['2B06','2B07','2B08','2B09']:assert abs(foundation_dxf.entitydb[h].dxf.actual_measurement-750)<.001
 for h in ['2B10','2B11']:assert abs(foundation_dxf.entitydb[h].dxf.actual_measurement-300)<.001
 assert foundation_dxf.entitydb['2B52'].dxf.text=='板厚'  # Never promote stale block graphics 500 to a real slab thickness.
 tops=[q for q in foundation if q['name'].startswith('预埋板_')];assert len(tops)==4
 checks=[];plate_radius=0
 for i,degrees in enumerate([0,90,180,270],1):
  q=next(q for q in parts if q['name']==f'托耳_R{i}_带孔底板');lo,hi=box(q);assert lo[2]==0 and hi[2]==24
  theta=math.radians(degrees);u=np.array([math.cos(theta),math.sin(theta)]);tangent=np.array([-u[1],u[0]])
  hole=min(native,key=lambda xy:np.linalg.norm(xy-u*550));assert np.linalg.norm(hole-u*550)<.00001
  tri=ck.tri([q]);assert not ck.inside(np.r_[hole,12],tri);assert ck.inside(np.r_[hole+20*tangent,12],tri)
  plate_radius=max(plate_radius,float(np.linalg.norm(np.asarray(q['vertices'])[:,:2],axis=1).max()))
  support=min(tops,key=lambda b:np.linalg.norm((sum(box(b))/2)[:2]-u*750));blo,bhi=box(support)
  projected=np.asarray(q['vertices'])[:,:2]@u;sp=np.asarray(support['vertices'])[:,:2]@u
  gap=float(sp.min()-projected.max());offset=float(np.linalg.norm((blo+bhi)[:2]/2-hole))
  assert abs(gap-8.75)<.00001 and abs(offset-200)<.00001,(i,gap,offset)
  for b in tops:
   l,h=box(b);overlap=np.minimum(hi[:2],h[:2])-np.maximum(lo[:2],l[:2]);assert np.any(overlap<0)
  checks.append({'direction_deg':degrees,'measured_axis_gap_mm':round(gap,6),'measured_hole_to_embedded_center_mm':round(offset,6),'direct_bearing_area_mm2':0})
 assert plate_radius<600,'No rotation about the nominal vessel centre can reach the nearest support radius'
 relation=json.loads((OUT/'支承差异.json').read_text());assert relation['direct_contact_area_mm2']==0 and relation['axis_outer_edge_gap_mm']==8.75 and not relation['rotation_can_close_gap']
 raw=(OUT/'设备/F41B03.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
 cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());current={q['id']:q for q in cfg['equipment']};before={q['id']:q for q in pin['equipment_placements']}
 later=set(cfg['equipment_versions'])-{'C41B02','C41B04','D41B01','L41B01','F41B03'}
 from revision_scope import unchanged_outside
 assert len(current)==72 and len(cfg['unplaced'])==27 and unchanged_outside(pin['foundations'],cfg['foundations'],later)
 unit=current['F41B03'];assert unit['position_mm']==before['F41B03']['position_mm']==[40000,41750,12200] and unit['rotation_deg']==before['F41B03']['rotation_deg']==0
 assert unit['z_status']=='待核' and '待核' in unit['orientation_status'] and unit['equipment_version']==p['version']
 for tag,q in current.items():
  if tag!='F41B03' and q['asset'] not in later:assert q==before[tag],tag
 oldrows={q['id']:q for q in pin['catalog']}
 later=set(cfg['equipment_versions'])-{'C41B02','C41B04','D41B01','L41B01','F41B03'}
 for q in json.loads((ROOT/'catalog.json').read_text())['models']:
  if q['id']!='F41B03' and q['id'][:6] not in later:assert q==oldrows[q['id']],q['id']
 circle=ezdxf.readfile(REPO/'水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf').entitydb['D9737']
 assert np.allclose(np.array(circle.dxf.center)[:2]-unit['source_floor_origin_mm'],unit['position_mm'][:2],atol=.001)
 bridge,columns=au.load();beams=[];floors=[]
 for q in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if q['kind']=='floor':floors.append(ck.object_mesh('FLOOR-'+str(q['el']),'floor',ck.tri([q])))
  if q['kind']=='frame':
   for i in range(len(q['vertices'])//8):
    n=i*8;faces=[[j-n for j in f] for f in q['faces'] if all(n<=j<n+8 for j in f)];beams.append(ck.object_mesh(q['name']+'-'+str(i),'beam',ck.tri([{'vertices':q['vertices'][n:n+8],'faces':faces}])))
 obstacles=columns+beams+bridge;closed={};cache={};other_count=0
 for q in cfg['equipment']+cfg['foundations']:
  if q['asset']=='F41B03':continue
  src=cfg['assets'][q['asset']]['source']
  if src not in cache:cache[src]=ck.script(REPO/src,'MODEL_PARTS')
  pp=cache[src];kind='equipment' if q in cfg['equipment'] else 'support';obstacles.append(ck.object_mesh(q['id'],kind,ck.tri(pp,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))));closed[q['id']]=ck.closed_components(pp,q['position_mm'],q['rotation_deg'],q.get('mirror_y',False))
  if kind=='equipment':other_count+=1
 subject=ck.object_mesh('F41B03','equipment',ck.tri(parts,unit['position_mm'],unit['rotation_deg']));hits=[];candidates=0
 for b in obstacles:
  overlap=np.minimum(subject['high'],b['high'])-np.maximum(subject['low'],b['low'])
  if np.any(overlap<=.1):continue
  candidates+=1;proof=ck.column_penetration(subject,b,.1) if b['kind'] in ['structure','room_column','stair_column','beam'] else ck.surface(subject,b)
  if proof is not None or any(ck.inside(subject['t'][0,0],t) for t in closed.get(b['id'],[])):hits.append({'other':b['id'],'kind':b['kind']})
 crossed=[b['id'] for b in floors if subject['high'][2]>=b['low'][2] and subject['low'][2]<=b['high'][2]]
 assert not crossed,crossed
 report={'version':p['version'],'status':'geometry-validated-bearing-unresolved','straight_section_dictionary':'unchanged including normals/material','unsupported_end_rings_removed':2,'real_holes':4,'watertight_components':len(parts),'source_hole_centres_mm':[xy.round(7).tolist() for xy in native],'support_checks':checks,'ear_corner_max_radius_mm':round(plate_radius,6),'support_min_radius_mm':600,'rotation_cannot_make_direct_contact':True,'direct_bearing_area_mm2':0,'support_geometry_bytes':'unchanged','other_71_placed_and_98_catalog_records':'unchanged','building_bridge_previous_models_hashes':'unchanged','current_xyz_rotation':'unchanged; Z/absolute orientation still provisional','screen':{'columns':len(columns),'beams':len(beams),'bridge_parts':len(bridge),'other_equipment':other_count,'aabb_candidates':candidates},'current_provisional_position_intersections':hits,'floor_slabs_crossed':crossed,'civil_instances_added':0,'limits':p['limits']}
 if later:report['other_71_placed_and_98_catalog_records']='unchanged except separately registered revisions: '+','.join(sorted(later))
 (OUT/'校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['limits','support_checks']},ensure_ascii=False));assert not hits,hits
if __name__=='__main__':run()
