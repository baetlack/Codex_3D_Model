"""Targeted native-outline, immutable source and relative steel-frame checks."""
from collections import Counter
import json,struct,sys
import numpy as np
from scipy.spatial import ConvexHull
from build_l41b02_v2 import ROOT,REPO,OUT,BASESRC,trace,sha,save
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck

def volume_witness(a,b):
    candidates=np.flatnonzero(np.all(b['th']>=a['low'],axis=1)&np.all(b['tl']<=a['high'],axis=1))
    for i in candidates:
        tri=b['t'][i];polygon=list(tri)
        for axis in range(3):
            polygon=ck.clip_polygon(polygon,axis,a['low'][axis],True)
            if not polygon:break
            polygon=ck.clip_polygon(polygon,axis,a['high'][axis],False)
            if not polygon:break
        if len(polygon)<3:continue
        normal=np.cross(tri[1]-tri[0],tri[2]-tri[0]);normal/=np.linalg.norm(normal)
        points=[np.mean(polygon,axis=0)]+polygon+[(x+y)/2 for x,y in zip(polygon,polygon[1:]+polygon[:1])]
        for point in points:
            for sign in [-1,1]:
                sample=point+sign*.5*normal
                if np.any(sample<=np.maximum(a['low'],b['low'])+.1) or np.any(sample>=np.minimum(a['high'],b['high'])-.1):continue
                if ck.inside(sample,a['t']) and ck.inside(sample,b['t']):
                    probes=np.vstack([sample+np.eye(3)*.1,sample-np.eye(3)*.1])
                    if all(ck.inside(q,a['t']) and ck.inside(q,b['t']) for q in probes):return sample.round(5).tolist()
    return None

def intersections(parts,frame,translation=(0,0,-300)):
    hits=[]
    aa=[ck.object_mesh(p['name'],'equipment',ck.tri([p])) for p in parts]
    bb=[ck.object_mesh(p['name']+' #'+str(i),'frame',ck.tri([p],translation)) for i,p in enumerate(frame)]
    for obj in aa+bb:
        points=np.unique(obj['t'][:,:,:2].reshape(-1,2),axis=0)
        obj['foot']=points[ConvexHull(points).vertices]
        edges=np.roll(obj['foot'],-1,axis=0)-obj['foot']
        obj['axes']=np.column_stack([-edges[:,1],edges[:,0]])
    for a in aa:
        for b in bb:
            if np.any(np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])<=.1):continue
            # Conservative convex projection exclusion. Keep exact 3-D triangle
            # and containment tests for every pair not separated by these axes.
            axes=np.vstack([a['axes'],b['axes']]);pa=a['foot']@axes.T;pb=b['foot']@axes.T
            if np.any(pa.max(0)<pb.min(0)-1e-5) or np.any(pb.max(0)<pa.min(0)-1e-5):continue
            hit=ck.surface(a,b)
            if hit is not None or ck.inside(a['t'][0,0],b['t']) or ck.inside(b['t'][0,0],a['t']):
                evidence=volume_witness(a,b) or volume_witness(b,a)
                if evidence:hits.append({'equipment':a['id'],'frame':b['id'],'surface_witness':hit,'point_inside_both_mm':evidence})
    return hits

def run():
    pin=json.loads((OUT/'本批保护基准.json').read_text());p=json.loads((OUT/'设备/参数.json').read_text());parts=ck.script(OUT/'设备/model_data.js','MODEL_PARTS');native=trace()
    assert abs(native['shell_OD']-2200)<.001 and abs(native['shell_top_z']-9400)<.001
    for key,z in [('north_big_z',1500),('south_low_z',800),('south_middle_z',5000),('south_upper_z',7000),('south_high_z',8900)]:assert abs(native[key]-z)<.001,(key,native[key])
    for key in ['south_middle_flange_OD','south_upper_flange_OD','south_high_flange_OD']:assert abs(native[key]-375)<.001
    for port,z in zip(['西侧低口','北侧大口','南侧下口','南侧中下','南侧中上','南侧上口'],[250,1500,800,5000,7000,8900]):assert next(q for q in p['ports'] if q['id']==port)['center_mm'][2]==z
    assert all('底部托座' not in q['name'] for q in parts)
    for q in parts:
        v=np.asarray(q['vertices']);assert np.isfinite(v).all();edges=Counter()
        for f in q['faces']:
            assert min(f)>=0 and max(f)<len(v)
            edges.update(tuple(sorted((a,b))) for a,b in zip(f,f[1:]+f[:1]))
        assert edges and all(n==2 for n in edges.values()),q['name']
    anch=next(q for q in parts if q['name']=='支撑_底锚圈12孔');ta=ck.tri([anch])
    for a in np.linspace(0,2*np.pi,12,endpoint=False):
        xy=np.array([1200*np.cos(a),1200*np.sin(a)])
        assert not ck.inside(np.r_[xy,10],ta)
        assert ck.inside(np.array([1170*np.cos(a),1170*np.sin(a),10]),ta)
    raw=(OUT/'设备/L41B02.glb').read_bytes();assert raw[:4]==b'glTF' and struct.unpack_from('<I',raw,8)[0]==len(raw)
    for name,digest in pin['protected_files'].items():assert sha(REPO/name)==digest,name
    cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text())
    for key in ['equipment','foundations','assets','unplaced']:assert cfg[key]==pin['assembly'][key],key
    assert len(cfg['equipment'])==72 and len(cfg['unplaced'])==27 and not any(q['id']=='L41B02' for q in cfg['equipment'])
    oldrows={q['id']:q for q in pin['catalog']['models']}
    for q in json.loads((ROOT/'catalog.json').read_text())['models']:
        if q['id']!='L41B02':assert q==oldrows[q['id']],q['id']
    for key,folder in [('L41B02','基础'),('L41B02-钢塔架','钢塔架')]:
        for path in (BASESRC/key).iterdir():
            if path.suffix in ['.js','.glb','.obj','.mtl']:assert (OUT/folder/path.name).read_bytes()==path.read_bytes(),str(path)
    frame=ck.script(OUT/'钢塔架/model_data.js','MODEL_PARTS');old=ck.script(ROOT/'示图建模_20260521/模型/L41B02/model_data.js','MODEL_PARTS')
    previous=intersections(old,frame);current=intersections(parts,frame)
    base=ck.script(OUT/'基础/model_data.js','MODEL_PARTS')
    # Plate/bolt clearance is already proved by the 12 real holes above.
    # Here check the side interfaces against the preserved exposed anchors.
    foundation_hits=intersections([p for p in parts if p['name'].startswith('接口_')],base,(0,0,0))
    report={'version':p['version'],'status':'geometry-checked-relative-intersections-pending' if current else 'geometry-checked-location-pending','datum':'局部同心对照：基础顶Z0、钢架楼面Z-300；绝对位置/方位待核','old_hits':previous,'new_hits':current,'new_regions_by_frame':len({h['frame'] for h in current}),'pair_count_meaning':'设备构件与钢架构件对，不等于独立施工冲突数；双实体内部采样排除单纯表面接触','unplaced_excluded_from_plant':True}
    save(OUT/'支承相交校核.json',report)
    save(OUT/'基础接口校核.json',{'version':p['version'],'datum':'圆基础顶/设备底同为Z0，沿用旧12-M24/200mm露头显示值','hits':foundation_hits,'contact_tolerance_mm':.1,'limits':'锚栓露头和设备共同方位待详图；不擅自缩短原锚栓或移动接口。底板孔位同心且孔半径15大于螺杆半径12，净距3mm。'})
    review=json.loads((OUT/'支承复核.json').read_text());review.update(status=report['status'],relative_interference_report='支承相交校核.json',old_intersection_pairs=len(previous),new_intersection_pairs=len(current),foundation_interface_report='基础接口校核.json',foundation_interface_pairs=len(foundation_hits));save(OUT/'支承复核.json',review)
    save(OUT/'校验报告.json',{'version':p['version'],'status':report['status'],'closed_components':len(parts),'native_side_outline_checks':'passed','real_anchor_holes':12,'other_98_catalog_records':'unchanged','all_72_placements_and_27_unplaced':'unchanged','building_bridge_previous_equipment':'hashes unchanged','foundation_and_frame_bytes':'unchanged','relative_old_intersection_pairs':len(previous),'relative_new_intersection_pairs':len(current),'foundation_interface_pairs':len(foundation_hits),'plant_collision':'not applicable: unplaced'})
    from publish_l41b02 import publish
    publish()
    print(json.dumps({'status':report['status'],'closed_parts':len(parts),'old_relative_pairs':len(previous),'new_relative_pairs':len(current),'new_hits':current,'placements':'72/27 unchanged'},ensure_ascii=False))
if __name__=='__main__':run()
