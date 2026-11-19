"""Independently validate C41B04 dimensions, source circles and all 24 ear bearings."""
from pathlib import Path
import hashlib,json,math,struct,sys
import numpy as np
import ezdxf
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/C41B04'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as au

def box(part):
    v=np.asarray(part['vertices']);return v.min(0),v.max(0)
def rotation(angle,mirror):
    a=math.radians(angle);return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])@np.diag([1,-1 if mirror else 1])

def run():
    pinned=json.loads((OUT/'本批保护基准.json').read_text())
    for name,digest in pinned['unchanged_files'].items():assert hashlib.sha256((REPO/name).read_bytes()).hexdigest()==digest,name
    p=json.loads((OUT/'设备/参数.json').read_text());parts=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');names={q['name']:q for q in parts}
    assert hashlib.sha256((REPO/p['source_drawing']).read_bytes()).hexdigest()==p['source_sha256']
    lo,hi=box(names['本体_外壳OD1300']);assert np.allclose((hi-lo)[:2],[1300,1300])
    low=min(v[2] for q in parts for v in q['vertices']);high=max(v[2] for q in parts for v in q['vertices'])
    assert low==-2612 and high==2202  # Retained nozzle fasteners project 2mm.
    assert max(v[2] for v in names['接口_顶盖法兰_N1']['vertices'])-low==4812
    previous=OUT/'历史/2.0-C41B04-01'
    frozen=json.loads((previous/'冻结清单.json').read_text())
    for name,digest in frozen['files'].items():assert hashlib.sha256((previous/name).read_bytes()).hexdigest()==digest,name
    original=ck.script(previous/'设备/model_data.js','MODEL_PARTS')
    def removed(q):
        name=q['name']
        return name in ('本体_上压板','本体_下压板') or name.startswith(('拉杆_','弹簧_')) or (name.startswith('紧固_') and name.endswith(('上螺母','下螺母')))
    assert sum(removed(q) for q in original)==82
    assert parts==[q for q in original if not removed(q)],'Retained equipment components must stay byte-for-byte equivalent'
    for sub in ['支架','支架/单组']:
        for file in (previous/sub).iterdir():
            if file.suffix in ('.glb','.obj','.mtl','.js'):assert (OUT/sub/file.name).read_bytes()==file.read_bytes(),file.name
    assert (OUT/'支架安装表.json').read_bytes()==(previous/'支架安装表.json').read_bytes()
    assert p['exchange_area_m2']==240 and p['ledger_exchange_area_m2']==230
    assert len(p['ports'])==11
    ports={q['id']:q for q in p['ports']};assert set(ports)=={'N1','N2','N3','N4','N5','N6','N7a','N7b','N7c','N7d','N7e'}
    for i,x in [('N1',240),('N2',-240)]:
        v=np.array(names['接口_顶盖法兰_'+i]['vertices']);assert np.allclose((v.min(0)+v.max(0))[:2]/2,[x,390]);assert v[:,2].max()==2200
        assert ports[i]['bolt_circle_mm']==350 and ports[i]['bolt_count']==12
    for i in 'abcde':
        port=ports['N7'+i];assert port['dn']==50 and port['center_mm'][2]==-2612
        assert abs(np.linalg.norm(port['center_mm'][:2])-400)<1e-7
    assert ports['N3']['center_mm']==[-858,0,-1782]
    assert ports['N4']['center_mm']==[-858,0,1398]
    assert ports['N5']['dn']==ports['N6']['dn']==32
    lugs=[q for q in parts if '承托底板' in q['name']];assert len(lugs)==4
    for part in lugs:
        lo,hi=box(part);assert lo[2]==0 and hi[2]==20
        edges={}
        for face in part['faces']:
            for a,b in zip(face,face[1:]+face[:1]):edge=tuple(sorted([a,b]));edges[edge]=edges.get(edge,0)+1
        assert all(n==2 for n in edges.values()),part['name']
    # New nozzle centers must match the independent arrangement DXF, not just
    # copies of values written by the model generator.
    drawing=ezdxf.readfile(REPO/'水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf')
    top=[np.array(e.dxf.center)[:2] for e in drawing.blocks['石墨换热器-顶'].query('CIRCLE') if abs(e.dxf.radius-197.5)<.01]
    bottom=[np.array(e.dxf.center)[:2] for e in drawing.blocks['石墨换热器-底'].query('CIRCLE') if abs(e.dxf.radius-80)<.01]
    errors={}
    for key,centers in [('N1',top),('N2',top),*[(f'N7{i}',bottom) for i in 'abcde']]:
        errors[key]=min(float(np.linalg.norm(np.array(ports[key]['center_mm'][:2])-c)) for c in centers);assert errors[key]<1,(key,errors[key])
    raw=(OUT/'设备/C41B04.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
    cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());before={q['id']:q for q in pinned['equipment_placements']};current={q['id']:q for q in cfg['equipment']}
    later=set(cfg['equipment_versions'])-{'C41B02','C41B04'}
    assert len(current)==72 and len(cfg['unplaced'])==27
    for key,q in current.items():
        if key[:6] in later:continue
        if not key.startswith('C41B04'):assert q==before[key],key
        else:
            assert q['position_mm'][:2]==before[key]['position_mm'][:2]
            assert q['rotation_deg']==before[key]['rotation_deg'] and q['mirror_y']==before[key]['mirror_y']
            assert q['position_mm'][2]==4500 and q['equipment_version']=='2.0-C41B04-02'
            witness=q['layout_review']['top_port_witness'];assert witness['matched_within_5mm']==2
    oldrows={q['id']:q for q in pinned['catalog']}
    for q in json.loads((ROOT/'catalog.json').read_text())['models']:
        if q['id'][:6] not in later and not q['id'].startswith('C41B04'):assert q==oldrows[q['id']],q['id']
    single=ck.script(OUT/'支架/单组/model_data.js','MODEL_PARTS');frames=json.loads((OUT/'支架安装表.json').read_text());bearings=[]
    assert len(frames)==3 and len(single)==38
    for frame in frames:
        beam_tops=[]
        for q in single:
            lo,hi=box(q)
            if 'GL1' in q['name'] and hi[2]==4500:beam_tops.append((lo+frame['position_mm'],hi+frame['position_mm']))
        for tag in frame['support_for']:
            unit=current[tag];matrix=rotation(unit['rotation_deg'],unit['mirror_y'])
            for i,angle in enumerate([90,180,270,0],1):
                a=math.radians(angle)
                # Two solid points flanking the Ø30 hole, directly over a real
                # upper flange. This distinguishes bearing from AABB proximity.
                for tangent in [-40,40]:
                    xy=np.array([937.5*math.cos(a)-tangent*math.sin(a),937.5*math.sin(a)+tangent*math.cos(a)])@matrix.T+unit['position_mm'][:2]
                    assert any(np.all(xy>=lo[:2]) and np.all(xy<=hi[:2]) for lo,hi in beam_tops),(tag,i,xy)
                bearings.append({'id':tag,'ear':'R'+str(i),'bearing_EL':104.5,'vertical_gap_mm':0,'solid_plate_points_over_beam':2})
    assert len(bearings)==24
    own_support_checks=0
    for frame in frames:
        for tag in frame['support_for']:
            unit=current[tag];device=ck.object_mesh(tag,'equipment',ck.tri(parts,unit['position_mm'],unit['rotation_deg'],mirror_y=unit['mirror_y']))
            for piece in single:
                support=ck.object_mesh(piece['name'],'support',ck.tri([piece],frame['position_mm']))
                overlap=np.minimum(device['high'],support['high'])-np.maximum(device['low'],support['low'])
                if np.any(overlap<=.1):continue
                assert ck.column_penetration(device,support,.1) is None,(tag,piece['name'])
                own_support_checks+=1
    conflicts=json.loads((OUT/'来源与差异.json').read_text())['conflicts'];assert conflicts[0]['policy']=='layout'
    # Actual meshes screened against the existing model, retaining intended
    # ear/beam surface contact. Steel checks are additional to the old total report.
    bridge,columns=au.load();beams=[];floor_meshes=[]
    for q in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
        if q['kind']=='floor':floor_meshes.append(ck.object_mesh('FLOOR-'+str(q['el']),'floor',ck.tri([q])))
        if q['kind']!='frame':continue
        for i in range(len(q['vertices'])//8):
            offset=i*8;faces=[[j-offset for j in face] for face in q['faces'] if all(offset<=j<offset+8 for j in face)]
            beams.append(ck.object_mesh(q['name']+'-'+str(i),'beam',ck.tri([{'vertices':q['vertices'][offset:offset+8],'faces':faces}])))
    others=[];cache={};closed={}
    for q in cfg['equipment']:
        if q['asset']=='C41B04':continue
        source=cfg['assets'][q['asset']]['source']
        if source not in cache:cache[source]=ck.script(REPO/source,'MODEL_PARTS')
        otherparts=cache[source];others.append(ck.object_mesh(q['id'],'equipment',ck.tri(otherparts,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))))
        closed[q['id']]=ck.closed_components(otherparts,q['position_mm'],q['rotation_deg'],q.get('mirror_y',False))
    subjects=[]
    for q in cfg['equipment']:
        if q['asset']=='C41B04':subjects.append(ck.object_mesh(q['id'],'equipment',ck.tri(parts,q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))))
    for f in frames:subjects.append(ck.object_mesh(f['id'],'support',ck.tri(single,f['position_mm'])))
    hits=[]
    floor_checks=[]
    for subject in subjects:
        for obstacle in columns+beams+bridge+others:
            overlap=np.minimum(subject['high'],obstacle['high'])-np.maximum(subject['low'],obstacle['low'])
            if np.any(overlap<=.1):continue
            proof=ck.column_penetration(subject,obstacle,.1) if obstacle['kind'] in ('structure','room_column','stair_column','beam') else ck.surface(subject,obstacle)
            contains=any(ck.inside(subject['t'][0,0],t) for t in closed.get(obstacle['id'],[]))
            if proof is not None or contains:hits.append([subject['id'],obstacle['id'],obstacle['kind']])
        if subject['kind']=='equipment':
            for floor in floor_meshes:
                if subject['high'][2]<floor['low'][2] or subject['low'][2]>floor['high'][2]:continue
                a=subject['t'][np.all(subject['th']>=floor['low'],axis=1)&np.all(subject['tl']<=floor['high'],axis=1)]
                b=floor['t'][np.all(floor['th']>=subject['low'],axis=1)&np.all(floor['tl']<=subject['high'],axis=1)]
                if len(a) and len(b):
                    assert ck.surface(ck.object_mesh(subject['id'],'equipment',a),ck.object_mesh(floor['id'],'floor',b)) is None,(subject['id'],floor['id'])
                floor_checks.append({'id':subject['id'],'floor':floor['id'],'actual_floor_mesh_intersection':False})
    assert not hits,hits
    assert len(floor_checks)==6
    report={'revision':'2.0-C41B04-02','status':'passed','accepted_C41B02_building_bridge_hashes':'unchanged','other_93_catalog_items':'unchanged','other_66_placed_equipment':'unchanged','dimensions_mm':p['dimensions_mm'],'source_plan_center_errors_mm':errors,'limits':'中心对原图吻合度不是现场公差；未标局部细部仍属外观量测','ear_beam_checks':bearings,'columns':len(columns),'beams':len(beams),'bridge_parts':len(bridge),'other_equipment':len(others),'new_support_groups':3,'intersections':hits,'AB_frame_decision':conflicts[0]}
    if later:
        report['other_93_catalog_items']='unchanged except separately registered revisions: '+','.join(sorted(later))
        report['other_66_placed_equipment']='unchanged except separately registered revisions: '+','.join(sorted(later))
    report['floor_opening_checks']=floor_checks
    report['own_support_open_interior_checks']=own_support_checks
    report['revision_02_removal']={'removed_objects':82,'remaining_objects_unchanged':len(parts),'steel_geometry_and_placements':'unchanged','old_01_frozen_hashes':'passed'}
    (OUT/'校验报告.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='ear_beam_checks'},ensure_ascii=False))
if __name__=='__main__':run()
