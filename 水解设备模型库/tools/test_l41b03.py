"""Check user-selected dimensions, independent supports and unchanged placement."""
from pathlib import Path
import json,struct,sys
import numpy as np
from build_l41b03_v2 import ROOT,REPO,OUT,CIVIL,VERSION,trace,sha,save
from check_assembly import script
from test_l41b02 import intersections
from revision_scope import unchanged_outside

def bounds(p):
    v=np.asarray(p['vertices']);return v.min(0),v.max(0)

def rectangle_union(rectangles):
    if not rectangles:return 0.
    xs=sorted({q[i] for q in rectangles for i in [0,2]});area=0.
    for a,b in zip(xs,xs[1:]):
        intervals=sorted((q[1],q[3]) for q in rectangles if q[0]<(a+b)/2<q[2])
        length=0.;end=-float('inf')
        for lo,hi in intervals:
            length+=max(0,hi-max(lo,end));end=max(end,hi)
        area+=(b-a)*length
    return area

def run():
    t=trace();n=t['native'];assert np.allclose([n['side_OD'],n['plan_OD']],[2000,2000])
    assert abs(n['cone_to_top_height']-4167.996)<.01
    assert abs(t['xy_scale']-.9)<1e-8 and abs(t['z_scale']*n['cone_to_top_height']-3100)<1e-6
    assert t==json.loads((OUT/'俯侧视量测.json').read_text())
    p=json.loads((OUT/'设备/参数.json').read_text());parts=script(OUT/'设备/model_data.js','MODEL_PARTS');civil=script(OUT/'钢支架/model_data.js','MODEL_PARTS')
    assert len(parts)==23 and len(civil)==31
    assert not any(q['name'].startswith('支撑_') for q in parts)
    cylinder=next(q for q in parts if q['name']=='本体_直筒');a,b=bounds(cylinder);assert np.allclose((b-a)[:2],[1800,1800])
    cone=next(q for q in parts if q['name']=='本体_下锥段');flange=next(q for q in parts if q['name']=='接口_顶部法兰')
    assert abs(bounds(flange)[1][2]-bounds(cone)[0][2]-3100)<1e-6
    all_vertices=np.vstack([q['vertices'] for q in parts]);assert np.allclose(all_vertices.max(0)-all_vertices.min(0),p['bounds_mm'],atol=1e-4)
    assert len(p['ports'])==3 and abs(p['ports'][1]['center_mm'][0]-697.5)<1e-6
    for q in parts:
        v=np.asarray(q['vertices']);assert np.isfinite(v).all()
        assert all(len(f)>=3 and min(f)>=0 and max(f)<len(v) for f in q['faces'])
    raw=(OUT/'设备/L41B03.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
    for q in CIVIL.iterdir():
        if q.suffix in ['.js','.glb','.obj','.mtl']:assert (OUT/'钢支架'/q.name).read_bytes()==q.read_bytes(),str(q)
    # Model contact is checked independently of the still-unknown plant location.
    shifted=[]
    for q in parts:
        shifted.append({**q,'vertices':(np.asarray(q['vertices'])+[0,-175,2000]).tolist()})
    hits=intersections(shifted,civil,(0,0,0));assert not hits,hits
    bearing=[]
    for ear in [q for q in shifted if q['name'].endswith('底板')]:
        low,high=bounds(ear);assert abs(low[2]-2000)<1e-6
        contacts=[]
        for q in civil:
            a,b=bounds(q)
            if abs(b[2]-2000)>.01:continue
            lo=np.maximum(low[:2],a[:2]);hi=np.minimum(high[:2],b[:2])
            if np.all(hi-lo>1e-6):contacts.append([float(lo[0]),float(lo[1]),float(hi[0]),float(hi[1])])
        area=rectangle_union(contacts);assert area>1000,(ear['name'],area)
        bearing.append({'ear':ear['name'],'contact_area_mm2':round(area,3),'bearing_Z_mm':2000,'method':'耳板底面与原钢架顶面矩形交集的并集，排除梁/钢板重叠重复面积'})
    assert len(bearing)==4
    pin=json.loads((OUT/'本批保护基准.json').read_text())
    for path,digest in pin['protected_files'].items():assert sha(REPO/path)==digest,path
    cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());later=set(cfg['equipment_versions'])-set(pin['assembly']['equipment_versions'])-{'L41B03'}
    for key in ['equipment','foundations','unplaced']:assert unchanged_outside(pin['assembly'][key],cfg[key],later),key
    assert unchanged_outside(pin['assembly']['assets'],cfg['assets'],later|{'L41B03'})
    assert unchanged_outside(pin['catalog']['models'],json.loads((ROOT/'catalog.json').read_text())['models'],later|{'L41B03'})
    assert len(cfg['equipment'])==72 and len(cfg['unplaced'])==27
    assert json.loads((OUT/'安装表.json').read_text())==[]
    assert not any(q.get('asset')=='L41B03' for q in cfg['equipment'])
    assert not any('L41B03' in q.get('asset','') for q in cfg['foundations'])
    review={'version':VERSION,'status':'local-geometry-checked-absolute-location-and-manufacture-pending','steel_geometry':'byte-identical','steel_parts':31,'absolute_position':'unplaced','assembly_instances_added':0,'relative_offset_mm':[0,-175,2000],'intersections':hits,'bearing_contacts':bearing,'opening_clearance_mm':125,'limits':p['limits']}
    save(OUT/'支承复核.json',review)
    report={'version':VERSION,'status':'passed','user_dimensions_mm':[1800,3100],'height_datum':'cone tip to top flange; bottom drain extra','body_parts':23,'excluded_reference_frame_parts':8,'previous_runtime_parts':22,'civil_parts_preserved':31,'local_intersections':len(hits),'bearing_contacts':4,'equipment_in_scene':72,'unplaced':27,'other_models_and_placements':'unchanged'}
    save(OUT/'校验报告.json',report)
    from publish_l41b03 import publish
    publish();print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':run()
