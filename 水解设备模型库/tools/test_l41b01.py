"""Check L41B01 against native dimensions, reflected DXF geometry and the site."""
from pathlib import Path
import hashlib,json,math,struct,sys
import ezdxf,numpy as np,xlrd
from ezdxf.disassemble import recursive_decompose
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/L41B01'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as au
def box(q):
 v=np.asarray(q['vertices']);return v.min(0),v.max(0)
def run():
 pin=json.loads((OUT/'本批保护基准.json').read_text())
 for name,digest in pin['unchanged_files'].items():assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==digest,name
 p=json.loads((OUT/'设备/参数.json').read_text());parts=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');names={q['name']:q for q in parts}
 drawing=ezdxf.readfile(REPO/p['source_drawing']);assert hashlib.sha256((REPO/p['source_drawing']).read_bytes()).hexdigest()==p['source_sha256']
 assert drawing.entitydb['172806'].dxf.text=='LMBLJC2001-03L4103-1'
 ledger=xlrd.open_workbook(REPO/'水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls').sheet_by_name('水解')
 row=ledger.row_values(102);assert row[1]=='L41B01A-F' and row[8]==6 and 'LMBLJC2001-03L4103' in row[6]
 for handle,value in [('172AB4',1200),('17288E',500),('17288F',350),('172890',450),('1728BA',100),('172AB1',1256),('172AB3',1320),('172A9A',1446),('172AAD',120)]:assert abs(drawing.entitydb[handle].dxf.actual_measurement-value)<.001,handle
 for key in ['本体_下筒体ID1200_OD1216','本体_上筒体ID1200_OD1216']:
  lo,hi=box(names[key]);assert np.allclose((hi-lo)[:2],[1216,1216])
 assert box(names['顶盖_平盖OD1256_t8'])[1][2]==1446
 assert min(v[2] for q in parts for v in q['vertices'])==0 and max(v[2] for q in parts for v in q['vertices'])==1566
 source_center=np.array([133799.3865309714,-47947.96058936445]);errors={}
 for key,h in [('d','17295B'),('e','172956')]:
  xy=np.array(drawing.entitydb[h].dxf.center)[:2]-source_center;lo,hi=box(names['接口_顶盖法兰_'+key]);error=float(np.linalg.norm((lo+hi)[:2]/2-xy));assert error<.001;errors[key]=round(error,6)
 # a is at Y445.5: derive it from the native Ø250/290 ceramic liner dimension,
 # independently of the generator's chosen coordinates. 500 is the lid rib pitch.
 dim=drawing.entitydb['17432D'];y=(dim.dxf.defpoint2.y+dim.dxf.defpoint3.y)/2-source_center[1]
 lo,hi=box(names['接口_a_密封面']);assert abs((lo[1]+hi[1])/2-y)<.001 and lo[0]==-750
 assert abs(y-445.5)<.001
 lo,hi=box(names['接口_b_密封面']);assert lo[1]==-758 and (lo[2]+hi[2])/2==1238
 assert abs(box(names['接口_c_连接法兰'])[1][0]*2-445)<.001
 assert len(p['ports'])==5 and set(q['id'] for q in p['ports'])==set('abcde')
 main_bolts=[q for q in parts if q['name'].startswith('紧固_M20_') and q['name'].endswith('_螺杆')];assert len(main_bolts)==24
 for q in main_bolts:
  lo,hi=box(q);assert abs(np.linalg.norm((lo+hi)[:2]/2)-660)<.001
 ears=[q for q in parts if '承托底板' in q['name']];assert len(ears)==3
 arcs=[e for e in drawing.modelspace().query('ARC') if abs(e.dxf.radius-15)<.001 and abs(np.linalg.norm(np.array(e.dxf.center)[:2]-source_center)-691)<.001]
 ear_centers=np.unique(np.array([np.array(e.dxf.center)[:2]-source_center for e in arcs]).round(5),axis=0);assert len(ear_centers)==3
 for q in ears:
  lo,hi=box(q);assert lo[2]==650 and hi[2]==660
  # Every source hole must actually be empty, with solid material beside it.
  ts=ck.tri([q]);found=0
  for xy in ear_centers:
   theta=math.atan2(xy[1],xy[0]);tangent=np.array([-math.sin(theta),math.cos(theta)])
   if np.all(xy>=lo[:2]) and np.all(xy<=hi[:2]):
    assert not ck.inside(np.r_[xy,655],ts)
    assert ck.inside(np.r_[xy+35*tangent,655],ts);found+=1
  assert found==1,q['name']
 for q in parts:
  v=np.asarray(q['vertices']);assert np.isfinite(v).all(),q['name'];edges={}
  for f in q['faces']:
   assert min(f)>=0 and max(f)<len(v)
   for a,b in zip(f,f[1:]+f[:1]):e=tuple(sorted([a,b]));edges[e]=edges.get(e,0)+1
  assert all(n==2 for n in edges.values()),q['name']
 raw=(OUT/'设备/L41B01.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
 cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());before={q['id']:q for q in pin['equipment_placements']};current={q['id']:q for q in cfg['equipment']};placed=[q for q in current.values() if q['asset']=='L41B01']
 later=set(cfg['equipment_versions'])-{'C41B02','C41B04','D41B01','L41B01'}
 assert len(current)==72 and len(cfg['unplaced'])==27 and len(placed)==6
 assert cfg['foundations']==pin['foundations'],'No new support may be invented or another support moved'
 oldrows={q['id']:q for q in pin['catalog']}
 for q in json.loads((ROOT/'catalog.json').read_text())['models']:
  if q['id'][:6] not in later and not q['id'].startswith('L41B01'):assert q==oldrows[q['id']],q['id']
 for tag,q in current.items():
  if q['asset'] not in later and q['asset']!='L41B01':assert q==before[tag],tag
 layout=ezdxf.readfile(REPO/'水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf');transform_checks=[]
 for q in placed:
  assert q['position_mm']==before[q['id']]['position_mm'] and q['rotation_deg']==0
  assert q['mirror_y']==(q['id'][-1] in 'ACE') and q['z_status']=='待核' and '绝对方位待核' in q['orientation_status']
  witness=q['layout_review']['top_port_witness'];assert witness['matched_within_5mm']==witness['model_features']==2
  e=layout.entitydb[q['source_insert']]
  # WCS, including OCS extrusion after the reflected INSERT. Raw CIRCLE.center
  # alone would put the reflected units at negative global X.
  native=[np.array(c.ocs().to_wcs(c.dxf.center))[:2]-q['source_floor_origin_mm'] for c in recursive_decompose([e]) if c.dxftype()=='CIRCLE' and abs(c.dxf.radius-82.5)<.001]
  errors_unit=[]
  for xy in [[400,200],[400,-200]]:
   point=np.array([xy[0],-xy[1] if q['mirror_y'] else xy[1]])+q['position_mm'][:2]
   error=min(float(np.linalg.norm(point-s)) for s in native);assert error<.001,(q['id'],error);errors_unit.append(round(error,6))
  transform_checks.append({'id':q['id'],'source_insert':q['source_insert'],'rotation_deg':0,'mirror_y':q['mirror_y'],'two_top_circle_WCS_errors_mm':errors_unit,'z_status':'待核'})
 support=json.loads((OUT/'支承待核.json').read_text());assert not support['civil_geometry_created'] and support['installed_civil_instances']==0
 overrides=ck.script(ROOT/'equipment_versions.js','EQUIPMENT_VERSION_OVERRIDES');assert 'L41B01' in overrides['foundation_policy']
 bridge,columns=au.load();beams=[];floors=[]
 for q in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if q['kind']=='floor':floors.append(ck.object_mesh('FLOOR-'+str(q['el']),'floor',ck.tri([q])))
  if q['kind']=='frame':
   for i in range(len(q['vertices'])//8):
    n=i*8;faces=[[j-n for j in f] for f in q['faces'] if all(n<=j<n+8 for j in f)];beams.append(ck.object_mesh(q['name']+'-'+str(i),'beam',ck.tri([{'vertices':q['vertices'][n:n+8],'faces':faces}])))
 obstacles=columns+beams+bridge;closed={};cache={};other_count=0
 for q in cfg['equipment']+cfg['foundations']:
  if q['asset']=='L41B01':continue
  src=cfg['assets'][q['asset']]['source']
  if src not in cache:cache[src]=ck.script(REPO/src,'MODEL_PARTS')
  pp=cache[src];kind='equipment' if q in cfg['equipment'] else 'support';t=ck.tri(pp,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False));obstacles.append(ck.object_mesh(q['id'],kind,t));closed[q['id']]=ck.closed_components(pp,q['position_mm'],q['rotation_deg'],q.get('mirror_y',False))
  if kind=='equipment':other_count+=1
 subjects=[ck.object_mesh(q['id'],'equipment',ck.tri(parts,q['position_mm'],q['rotation_deg'],mirror_y=q['mirror_y'])) for q in placed];hits=[];candidates=0;floor_checks=[]
 for a in subjects:
  for b in obstacles:
   overlap=np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])
   if np.any(overlap<=.1):continue
   candidates+=1;proof=ck.column_penetration(a,b,.1) if b['kind'] in ['structure','room_column','stair_column','beam'] else ck.surface(a,b)
   contained=any(ck.inside(a['t'][0,0],ts) for ts in closed.get(b['id'],[]))
   if proof is not None or contained:hits.append({'a':a['id'],'b':b['id'],'kind':b['kind'],'z_basis':'L41B01安装标高暂用，待承托EL核定后复核'})
  crossed=[]
  for b in floors:
   if a['high'][2]<b['low'][2] or a['low'][2]>b['high'][2]:continue
   ta=a['t'][np.all(a['th']>=b['low'],axis=1)&np.all(a['tl']<=b['high'],axis=1)];tb=b['t'][np.all(b['th']>=a['low'],axis=1)&np.all(b['tl']<=a['high'],axis=1)]
   hit=ck.surface(ck.object_mesh(a['id'],'equipment',ta),ck.object_mesh(b['id'],'floor',tb)) if len(ta) and len(tb) else None
   crossed.append({'floor':b['id'],'actual_mesh_intersection':hit is not None})
  floor_checks.append({'id':a['id'],'crossed_floor_slabs':crossed})
 for i,a in enumerate(subjects):
  for b in subjects[i+1:]:assert np.any(np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])<0)
 report={'version':p['version'],'status':'passed-with-unresolved-support-and-EL' if not hits else 'geometry-passed-current-position-interferences-require-review','native_DXF_and_ledger_applicability':'passed','closed_components':len(parts),'ports':5,'ears':3,'top_nozzle_center_errors_mm':errors,'ear_hole_centers_native_mm':ear_centers.tolist(),'INSERT_transform_checks':transform_checks,'other_66_placed_and_93_catalog_records':'unchanged','existing_foundations':'unchanged; no new L41B01 support','building_bridge_and_accepted_models_hashes':'unchanged','screen':{'columns':len(columns),'beams':len(beams),'bridge_parts':len(bridge),'other_equipment':other_count,'aabb_candidates':candidates},'current_provisional_position_intersections':hits,'floor_checks':floor_checks,'support_and_EL':'unresolved by user decision; no civil support inferred','limits':p['limits']}
 if later:report['other_66_placed_and_93_catalog_records']='unchanged except separately registered revisions: '+','.join(sorted(later))
 (OUT/'校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['INSERT_transform_checks','limits']},ensure_ascii=False))
 assert not any(r['actual_mesh_intersection'] for f in floor_checks for r in f['crossed_floor_slabs']),floor_checks
if __name__=='__main__':run()
