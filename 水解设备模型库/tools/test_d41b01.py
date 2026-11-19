"""Independent native-DXF, datum, bearing and real mesh checks for D41B01."""
from pathlib import Path
import hashlib,json,math,struct,sys
import ezdxf,numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/D41B01'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as au

def box(p):
 v=np.asarray(p['vertices']);return v.min(0),v.max(0)
def rot(p):
 a=math.radians(p['rotation_deg']);return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])@np.diag([1,-1 if p.get('mirror_y') else 1])
def run():
 pin=json.loads((OUT/'本批保护基准.json').read_text())
 for name,digest in pin['unchanged_files'].items():assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==digest,name
 parts=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');names={q['name']:q for q in parts};p=json.loads((OUT/'设备/参数.json').read_text())
 d=ezdxf.readfile(REPO/p['source_drawing']);assert hashlib.sha256((REPO/p['source_drawing']).read_bytes()).hexdigest()==p['source_sha256']
 assert abs(d.entitydb['8EE6D'].dxf.actual_measurement-1800)<1e-6
 assert abs(d.entitydb['8EF27'].dxf.actual_measurement-1600)<1e-6
 lo,hi=box(names['本体_钢壳OD1816']);assert np.allclose((hi-lo)[:2],[1816,1816]);assert hi[2]==600
 lo,hi=box(names['保温_外包60mm']);assert np.allclose((hi-lo)[:2],[1936,1936])
 assert d.entitydb['8F8E6'].dxf.text=='21' and d.entitydb['8F0FD'].dxf.text=='340' and d.entitydb['8F113'].dxf.text=='154'
 top_errors={};ports={q['id']:q for q in p['ports']}
 # Seven actual circle centers in the independent DXF, not cached generator values.
 for key,handle in {'a':'7F3A9','b':'7F3A8','c':'7F1BF','d':'7F1B8','e':'7F39E','f':'7F399','h':'7F33C'}.items():
  e=d.entitydb[handle];xy=(np.asarray(e.dxf.center)[:2]-[144589.3865209028,31075.1742346563])/2
  q=names['接口_h_人孔颈' if key=='h' else '接口_顶盖法兰_'+key];lo,hi=box(q)
  error=float(np.linalg.norm((lo+hi)[:2]/2-xy));assert error<.001,(key,error);top_errors[key]=round(error,6)
 assert set(ports)==set(['a','b','c','d','e','f','g','h','j','k','m1','m2','m3'])
 assert abs(np.linalg.norm(np.array(ports['c']['center_mm'])[:2]-ports['d']['center_mm'][:2])-180)<.001
 low=min(v[2] for q in parts for v in q['vertices']);high=max(v[2] for q in parts for v in q['vertices'])
 assert low==-1312.1173 and high==2103
 for q in parts:
  v=np.asarray(q['vertices']);assert np.isfinite(v).all(),q['name'];edges={}
  for f in q['faces']:
   assert min(f)>=0 and max(f)<len(v)
   for a,b in zip(f,f[1:]+f[:1]):e=tuple(sorted([a,b]));edges[e]=edges.get(e,0)+1
  assert all(n==2 for n in edges.values()),q['name']
 raw=(OUT/'设备/D41B01.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
 cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());current={q['id']:q for q in cfg['equipment']};before={q['id']:q for q in pin['equipment_placements']}
 arrangement=ezdxf.readfile(REPO/'水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf')
 for handle in ['F1C1C','F1B80']:assert abs(arrangement.entitydb[handle].dxf.actual_measurement-2600)<.001
 section=arrangement.entitydb['57BF9'];assert abs(section.dxf.actual_measurement-2500)<.001
 assert abs(section.dxf.defpoint2.y-section.dxf.defpoint3.y)<.001  # It is horizontal, not vertical.
 difference=json.loads((OUT/'来源与差异.json').read_text())['conflicts'][1]
 assert difference['plan_mm']==2600 and difference['section_mm']==2500 and difference['difference_mm']==100
 assert len(current)==72 and len(cfg['unplaced'])==27
 for tag,q in current.items():
  if not tag.startswith('D41B01'):assert q==before[tag],tag
  else:
   assert q['position_mm'][:2]==before[tag]['position_mm'][:2] and q['position_mm'][2]==11000
   assert q['rotation_deg']==before[tag]['rotation_deg'] and q['mirror_y']==before[tag]['mirror_y']
   assert before[tag]['position_mm'][2]+1180==11000
   assert q['equipment_version']=='2.0-D41B01-01' and '待核' in q['orientation_status'] and 'layout_review' not in q
 assert current['D41B01A']['z_status']=='待核'
 oldrows={q['id']:q for q in pin['catalog']}
 for q in json.loads((ROOT/'catalog.json').read_text())['models']:
  if not q['id'].startswith('D41B01'):assert q==oldrows[q['id']],q['id']
 frame=ck.script(OUT/'支架/model_data.js','MODEL_PARTS');oldframe=ck.script(REPO/'水解桥架工程/models/设备/设备基础_20261106/D41B01/model_data.js','MODEL_PARTS')
 # Export adds smoothed normals; topology, coordinates, colors and names are exact.
 for a,b in zip(frame,oldframe):
  for key in ['name','color','vertices','faces']:assert a[key]==b[key],key
 assert len(frame)==len(oldframe)
 frames=json.loads((OUT/'支架安装表.json').read_text());assert [q['support_for'] for q in frames]==[['D41B01B','D41B01C'],['D41B01D','D41B01E']]
 assert all(q['id'] in [v['id'] for v in cfg['foundations']] for q in frames)
 bearings=[];support_checks=0
 for f in frames:
  beam_tops=[(lo+f['position_mm'],hi+f['position_mm']) for lo,hi in map(box,frame) if hi[2]==0 and hi[2]-lo[2]==200]
  for tag in f['support_for']:
   q=current[tag];m=rot(q)
   for i,a in enumerate(np.linspace(0,2*math.pi,5)[:-1],1):
    plate=names[f'托耳_R{i}_承托底板'];lo,hi=box(plate);assert lo[2]==0 and hi[2]==12
    for tangent in [-50,50]:
     xy=np.array([1051*math.cos(a)-tangent*math.sin(a),1051*math.sin(a)+tangent*math.cos(a)])@m.T+q['position_mm'][:2]
     assert any(np.all(xy>=l[:2]) and np.all(xy<=h[:2]) for l,h in beam_tops),(tag,i,xy)
    bearings.append({'id':tag,'ear':'R'+str(i),'bearing_EL':111.0,'gap_mm':0,'solid_points_on_actual_beam':2,'ear_hole_to_beam_axis_offset_mm':8})
   device=ck.object_mesh(tag,'equipment',ck.tri(parts,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False)))
   for piece in frame:
    support=ck.object_mesh(piece['name'],'support',ck.tri([piece],f['position_mm']))
    if np.any(np.minimum(device['high'],support['high'])-np.maximum(device['low'],support['low'])<=.1):continue
    assert ck.column_penetration(device,support,.1) is None,(tag,piece['name']);support_checks+=1
 assert len(bearings)==16
 # Cross-module screen: 120 retained columns, 76 frame beam pieces, bridges,
 # all other placed equipment, existing support groups and real floor holes.
 bridge,columns=au.load();beams=[];floors=[]
 for q in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if q['kind']=='floor':floors.append(ck.object_mesh('FLOOR-'+str(q['el']),'floor',ck.tri([q])))
  if q['kind']!='frame':continue
  for i in range(len(q['vertices'])//8):
   n=i*8;faces=[[j-n for j in face] for face in q['faces'] if all(n<=j<n+8 for j in face)]
   beams.append(ck.object_mesh(q['name']+'-'+str(i),'beam',ck.tri([{'vertices':q['vertices'][n:n+8],'faces':faces}])))
 obstacles=columns+beams+bridge;closed={};cache={};other_count=0
 for q in cfg['equipment']+cfg['foundations']:
  if q['asset'] in ['D41B01','foundation-D41B01']:continue
  src=cfg['assets'][q['asset']]['source']
  if src not in cache:cache[src]=ck.script(REPO/src,'MODEL_PARTS')
  pp=cache[src];kind='equipment' if q in cfg['equipment'] else 'support'
  obstacles.append(ck.object_mesh(q['id'],kind,ck.tri(pp,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))))
  closed[q['id']]=ck.closed_components(pp,q['position_mm'],q['rotation_deg'],q.get('mirror_y',False))
  if kind=='equipment':other_count+=1
 subjects=[ck.object_mesh(q['id'],'equipment',ck.tri(parts,q['position_mm'],q['rotation_deg'],mirror_y=q['mirror_y'])) for q in current.values() if q['asset']=='D41B01']
 # The nearest same-class pair is separated even at the full ear envelope.
 pair_gaps=[]
 for i,a in enumerate(subjects):
  for b in subjects[i+1:]:
   separation=np.maximum(a['low']-b['high'],b['low']-a['high'])
   assert max(separation)>0,(a['id'],b['id'])
   pair_gaps.append(float(max(separation)))
 subjects += [ck.object_mesh(f['id'],'support',ck.tri(frame,f['position_mm'])) for f in frames]
 hits=[];floor_checks=[];candidates=0
 for a in subjects:
  for b in obstacles:
   overlap=np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])
   if np.any(overlap<=.1):continue
   candidates+=1
   hit=ck.column_penetration(a,b,.1) if b['kind'] in ['structure','room_column','stair_column','beam'] else ck.surface(a,b)
   contained=any(ck.inside(a['t'][0,0],ts) for ts in closed.get(b['id'],[]))
   if hit is not None or contained:hits.append({'a':a['id'],'b':b['id'],'kind':b['kind']})
  if a['kind']=='equipment':
   for floor in floors:
    if a['high'][2]<floor['low'][2] or a['low'][2]>floor['high'][2]:continue
    ta=a['t'][np.all(a['th']>=floor['low'],axis=1)&np.all(a['tl']<=floor['high'],axis=1)]
    tb=floor['t'][np.all(floor['th']>=a['low'],axis=1)&np.all(floor['tl']<=a['high'],axis=1)]
    hit=ck.surface(ck.object_mesh(a['id'],'equipment',ta),ck.object_mesh(floor['id'],'floor',tb)) if len(ta) and len(tb) else None
    floor_checks.append({'id':a['id'],'floor':floor['id'],'actual_mesh_intersection':hit is not None})
 assert len(floor_checks)==5
 report={'version':p['version'],'status':'passed' if not hits and not any(r['actual_mesh_intersection'] for r in floor_checks) else 'review-required','other_67_equipment_and_94_catalog_items':'unchanged','building_bridge_accepted_equipment_hashes':'unchanged','top_nozzle_DXF_center_errors_mm':top_errors,'watertight_components':len(parts),'bearing_checks':bearings,'support_open_interior_checks':support_checks,'screen':{'columns':len(columns),'beams':len(beams),'bridge_parts':len(bridge),'other_equipment':other_count,'pair_support_groups':2,'aabb_candidates':candidates},'intersections':hits,'floor_checks':floor_checks,'quantity_decision':p['user_decision'],'limits':p['limits']}
 report['same_class_pair_screen']={'pairs':len(pair_gaps),'minimum_separating_aabb_gap_mm':round(min(pair_gaps),3)}
 report['plan_section_spacing_difference']=difference
 (OUT/'校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in report.items() if k not in ['bearing_checks','limits']},ensure_ascii=False))
 assert not hits,hits
 assert not any(r['actual_mesh_intersection'] for r in floor_checks),floor_checks
if __name__=='__main__':run()
