"""Check native datum, byte-identical geometry and only F41B04/new-base spatial pairs."""
from pathlib import Path
import json,math,struct,sys
import numpy as np
from scipy.spatial import ConvexHull
from build_f41b04_v2 import ROOT,REPO,OUT,SOURCE,FOUND,BASESRC,sha,save,native
from revision_scope import unchanged_outside
from test_l41b02 import intersections,volume_witness
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck

def minimum_xy_radius(vertices):
    p=np.unique(np.asarray(vertices)[:,:2],axis=0);h=p[ConvexHull(p).vertices]
    values=[]
    for a,b in zip(h,np.roll(h,-1,axis=0)):
        v=b-a;t=np.clip(-np.dot(a,v)/np.dot(v,v),0,1);values.append(float(np.linalg.norm(a+t*v)))
    return min(values)

def run():
    pin=json.loads((OUT/'本批保护基准.json').read_text());params=json.loads((OUT/'设备/参数.json').read_text());trace=native()
    assert abs(trace['measured_OD_mm']-1000)<1e-5
    assert abs(trace['measured_tube_height_mm']-15098.6016425)<.001
    assert abs(trace['measured_bottom_above_floor_mm']-300)<1e-5 and trace['dimension_bottom_above_floor_mm']==300
    assert abs(trace['plan_circle_diameter_mm']-1099.7595264)<.001
    source=REPO/pin['assembly']['assets']['F41B04']['source']
    for p in source.parent.iterdir():
        if p.suffix in ['.js','.glb','.obj','.mtl']:assert (OUT/'设备'/p.name).read_bytes()==p.read_bytes(),str(p)
    body=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');assert len(body)==1
    v=np.array(body[0]['vertices']);assert np.allclose(v.min(0),[-500,-500,0]) and np.allclose(v.max(0),[500,500,15100])
    assert len(ck.closed_components(body,(0,0,0),0))==1
    raw=(OUT/'设备/F41B04.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
    for key,folder in [('F41B04','基础'),('F41B04-钢塔架','钢塔架')]:
        for p in (BASESRC/key).iterdir():
            if p.suffix in ['.js','.glb','.obj','.mtl']:assert (OUT/folder/p.name).read_bytes()==p.read_bytes(),str(p)
    for path,digest in pin['protected_files'].items():assert sha(REPO/path)==digest,path
    cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());unit=next(q for q in cfg['equipment'] if q['id']=='F41B04');base_install=next(q for q in cfg['foundations'] if q['id']=='BASE-F41B04')
    assert unit['position_mm']==[26000,31900,23300] and unit['rotation_deg']==0 and unit['z_status']=='有安装基准'
    assert unit['installation_review']['before_position_mm']==[26000,31900,23000]
    assert base_install['position_mm']==unit['position_mm'] and base_install['asset']=='foundation-F41B04'
    assert len(cfg['equipment'])==72 and len(cfg['unplaced'])==27
    assert len(cfg['foundations'])==len(pin['assembly']['foundations'])+1
    later=set(cfg['equipment_versions'])-set(pin['assembly']['equipment_versions'])-{'F41B04'}
    for key in ['equipment','foundations','assets','unplaced']:assert unchanged_outside(pin['assembly'][key],cfg[key],{'F41B04'}|later),key
    assert unchanged_outside(pin['catalog']['models'],json.loads((ROOT/'catalog.json').read_text())['models'],{'F41B04'}|later)
    assert all('钢塔架' not in q['name'] for q in cfg['foundations'] if q.get('support_for')=='F41B04')
    frame=ck.script(OUT/'钢塔架/model_data.js','MODEL_PARTS');base=ck.script(OUT/'基础/model_data.js','MODEL_PARTS')
    assert len(frame)==153 and len(base)==14
    frame_hits=intersections(body,frame);base_hits=intersections(body,base,(0,0,0))
    assert not frame_hits and not base_hits,(frame_hits,base_hits)
    gaps=[round(minimum_xy_radius(p['vertices'])-500,4) for p in frame if p['name']=='钢塔架_GJ04限位杆']
    assert len(gaps)==15 and min(gaps)>0
    anchor_gap=min(minimum_xy_radius(p['vertices'])-500 for p in base if '地脚螺栓' in p['name'])
    # New concrete base bottom and roof slab top share a plane, not a volume.
    building=ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']
    roof=next(q for q in building if q['name']=='FLOOR-EL123')
    assert max(z for x,y,z in roof['vertices'])==23000
    assert min(z for p in base for x,y,z in p['vertices'])+23300==23000
    subjects=[ck.object_mesh('F41B04','equipment',ck.tri(body,unit['position_mm'])),ck.object_mesh('BASE-F41B04','foundation',ck.tri(base,base_install['position_mm']))]
    hits=[];checked=0;candidates=0;cache={}
    def check(parts,position,rotation,id,kind,mirror=False):
        nonlocal checked,candidates
        vv=np.vstack([np.asarray(p['vertices'],float) for p in parts]);a=math.radians(rotation);rot=np.array([[math.cos(a),-math.sin(a),0],[math.sin(a),math.cos(a),0],[0,0,1]])
        if mirror:vv[:,1]*=-1
        vv=vv@rot.T+position;low=vv.min(0);high=vv.max(0);checked+=1;target=None
        for subject in subjects:
            if np.any(np.minimum(subject['high'],high)-np.maximum(subject['low'],low)<=.1):continue
            candidates+=1
            if target is None:target=ck.object_mesh(id,kind,ck.tri(parts,position,rotation,mirror_y=mirror))
            surface=ck.surface(subject,target)
            contained=ck.inside(subject['t'][0,0],target['t']) or ck.inside(target['t'][0,0],subject['t'])
            if surface is not None or contained:
                evidence=volume_witness(subject,target) or volume_witness(target,subject)
                if evidence:hits.append({'subject':subject['id'],'other':id,'point_inside_both_mm':evidence})
    for p in building:check([p],(0,0,0),0,p['name'],'building')
    for p in cfg['equipment']+cfg['foundations']:
        if p['id'] in ['F41B04','BASE-F41B04']:continue
        asset=cfg['assets'][p['asset']]['source']
        if asset not in cache:cache[asset]=ck.script(REPO/asset,'MODEL_PARTS')
        check(cache[asset],p['position_mm'],p['rotation_deg'],p['id'],'equipment_or_support',p.get('mirror_y',False))
    bridge=ck.script(REPO/'水解桥架工程/models/整体/viewer_data.js','GEOMETRY')
    for p in bridge:check([{'vertices':(np.asarray(p['v'])*1000).tolist(),'faces':p['f']}],(0,0,0),0,p['id'],'bridge')
    assert not hits,hits
    review=json.loads((OUT/'支承复核.json').read_text());review.update(status='datum-checked-height-anchorage-and-steel-direction-pending',relative_frame_pairs=len(frame_hits),relative_base_pairs=len(base_hits),GJ04_surface_gaps_mm=gaps,anchor_to_tube_radial_gap_mm=round(anchor_gap,4),round_base_bottom_EL=123,round_base_top_EL=123.3,display_tube_top_EL=138.4);save(OUT/'支承复核.json',review)
    report={'version':params['version'],'status':review['status'],'tube_and_exports':'byte-identical','foundation_and_153_steel_parts':'byte-identical','native_300mm_base_height':'passed','original_XY_rotation':'unchanged','new_Z_mm':23300,'new_round_base_instances':1,'new_steel_frame_instances':0,'other_71_positions_and_98_catalog_records':'unchanged','relative_frame_pairs':len(frame_hits),'relative_base_pairs':len(base_hits),'GJ04_surface_gaps_mm':gaps,'anchor_radial_gap_mm':round(anchor_gap,4),'screened_existing_objects':checked,'aabb_candidates':candidates,'world_intersections':hits,'roof_base_contact':'roof top/base bottom =23000; normal surface contact','limits':params['limits']}
    save(OUT/'校验报告.json',report)
    from publish_f41b04 import publish
    publish();print(json.dumps({k:v for k,v in report.items() if k not in ['limits','GJ04_surface_gaps_mm']},ensure_ascii=False))
if __name__=='__main__':run()
