"""Verify source dimensions, confirmed cores, preserved placement and civil fits."""
from pathlib import Path
import copy,json,struct,sys
import ezdxf
import numpy as np
from build_factory_batch_v2 import ROOT,REPO,BATCH,CLASSES,FILES,ALIASES,DRAWINGS,CIVIL,mesh,sha,save
from test_l41b02 import intersections
from revision_scope import unchanged_outside

def run(selected):
    assert set(selected)<=set(CLASSES)
    baseline=json.loads((BATCH/'本批保护基准.json').read_text());cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());catalog=json.loads((ROOT/'catalog.json').read_text());project=json.loads((ROOT/'project.json').read_text())
    approved=json.loads((ROOT/'版本/2.0/C41B04/上部吊耳删除记录.json').read_text())['files']
    for name,digest in baseline['protected_files'].items():
        if name in approved:
            assert approved[name]['before']==digest,name
            digest=approved[name]['after']
        assert sha(REPO/name)==digest,name
    assert len(cfg['equipment'])==72 and len(cfg['unplaced'])==27
    before={q['id']:q for q in baseline['assembly']['equipment']};after={q['id']:q for q in cfg['equipment']};assert set(before)==set(after)
    for tag,q in after.items():
        p=before[tag]
        for field in ['position_mm','rotation_deg','mirror_y','level','xy_status','z_status']:assert q.get(field)==p.get(field),(tag,field)
        if q['asset'] not in CLASSES:assert q==p,tag
    assert cfg['foundations']==baseline['assembly']['foundations'] and cfg['unplaced']==baseline['assembly']['unplaced']
    assert unchanged_outside(baseline['assembly']['assets'],cfg['assets'],set(CLASSES))
    assert unchanged_outside(baseline['catalog']['models'],catalog['models'],set(CLASSES))
    assert project['counts']['reviewed_batches']==35 and project['counts']['reviewed_items']==99
    assert set(project['revisions']).isdisjoint(project['reviews']) and len(project['revisions'])+len(project['reviews'])==35
    assert sum(1 for q in catalog['models'] if q['id'][:6] in project['revisions'])==58
    assert project['counts']['revised_items']==58 and project['counts']['other_items_unchanged']==41
    for key in project['reviews']:
        review=json.loads((ROOT/f'版本/2.0/{key}/复核记录.json').read_text());assert review['geometry_action']=='retained'
        if review['active_model_source']:assert sha(REPO/review['active_model_source'])==review['active_model_sha256']
        assert review['pending'] and review['unit_tags']
    reports={};docs={}
    for key in selected:
        family=ALIASES.get(key,key);out=ROOT/'版本/2.0'/key;params=json.loads((out/'设备/参数.json').read_text());parts=mesh(out/'设备/model_data.js');dimensions=params['dimensions_mm']
        source=DRAWINGS/(FILES[family]+'.dxf')
        if family not in docs:docs[family]=ezdxf.readfile(source)
        doc=docs[family];assert params['source_sha256']==sha(source)
        vertices=np.vstack([p['vertices'] for p in parts]);assert np.isfinite(vertices).all()
        assert np.allclose(np.ptp(vertices,axis=0),params['bounds_mm'],atol=1e-4)
        for q in parts:
            assert all(len(face)>=3 and min(face)>=0 and max(face)<len(q['vertices']) for face in q['faces']),q['name']
        glb=(out/f'设备/{key}.glb').read_bytes();assert glb[:4]==b'glTF' and struct.unpack_from('<I',glb,8)[0]==len(glb)
        if key=='C41B01':
            h=next(q for q in params['ports'] if q['id']=='h')
            lid=np.asarray(next(q for q in parts if q['name']=='盖面_h盖')['vertices'])
            assert np.allclose((lid.min(0)+lid.max(0))[:2]/2,h['face_center_mm'][:2],atol=1e-6)
            assert abs(lid[:,2].min()-h['face_center_mm'][2])<1e-6
        lid_name={'C41B03':'e','F41B01':'k','F41B02':'h2','D41B02':'t'}.get(family)
        if lid_name:
            p=next(q for q in params['ports'] if q['id']==lid_name);assert p['closure']=='带盖侧人孔'
            lid=next(q for q in parts if q['name']=='接口_'+lid_name+'_人孔盖');assert len(lid['faces'])>50
            if family=='F41B01':assert p['cover_thickness_mm']==p['flange_thickness_mm']==38 and '38' in doc.entitydb['31D2E'].dxf.text
        if family in ['C41B01','C41B03','F41B01','F41B02']:
            shell=next(q for q in parts if q['name']=='本体_钢壳');v=np.asarray(shell['vertices']);assert np.allclose(np.ptp(v[:,:2],axis=0),[dimensions['steel_outer_diameter_mm']]*2)
            bearing_vertices=np.vstack([q['vertices'] for q in parts if q['name']=='本体_底板' or q['name'].startswith('设备底型钢_')])
            assert abs(bearing_vertices[:,2].min())<1e-6
            if family=='C41B01':
                assert abs(doc.entitydb['28FB8'].dxf.actual_measurement-4000)<.001
                assert dimensions['steel_outer_diameter_mm']==3520
                assert abs(abs(doc.entitydb['28A9D'].dxf.start.x-doc.entitydb['28A9A'].dxf.start.x)-10)<1e-6
                assert {p['id'] for p in params['ports']}=={'a','b2/k2','b1/k1','g','m','e','h','d','f','c1','c2'}
            elif family=='C41B03':
                assert dimensions['steel_outer_diameter_mm']==1512 and dimensions['cover_diameter_mm']==1638
                points=json.loads((out/'来源量测.json').read_text())['plan_points'];assert np.allclose(points['h']['xy_mm'],[424.2640687,424.2640687],atol=.1)
                assert abs(np.linalg.norm(points['c']['xy_mm'])-650)<.01
            elif family=='F41B01':
                assert abs(doc.entitydb['1A79D'].dxf.actual_measurement-5900)<.01
                assert dimensions['steel_outer_diameter_mm']==5020 and dimensions['bottom_member_height_mm']==150
                assert len([p for p in parts if p['name'].startswith('设备底型钢_')])==10
            else:
                assert abs(doc.entitydb['FA85'].dxf.actual_measurement-2816)<.01
                assert dimensions['mixer_display_height_mm']==1560 and dimensions['bottom_member_height_mm']==150
                assert dimensions['factory_to_type_rotation_deg']==90
                main=next(q for q in params['ports'] if q['id']=='b1');assert np.allclose(main['normal'],[1,0,0])
                basis=json.loads((out/'三槽方位依据.json').read_text());assert len(basis['instances'])==3 and basis['factory_to_type_rotation_deg']==90
                assert sha(REPO/basis['source'])==basis['source_sha256']
                assert len([p for p in parts if p['name'].startswith('设备底型钢_')])==6
                assert not any('g弯头出口法兰' in p['name'] for p in parts)
        elif family=='D41B02':
            original=mesh(REPO/baseline['assembly']['assets'][key]['source']);core={p['name']:p for p in original if not p['name'].startswith('接口_')};current={p['name']:p for p in parts}
            for name,p in core.items():
                for field in ['vertices','faces','color']:assert current[name][field]==p[field],(name,field)
            assert len(params['ports'])==18 and dimensions['confirmed_mixer_total_height_mm']==3076
            assert dimensions['retained_cover_top_mm']==5020 and dimensions['new_drawing_cover_datum_pending']
        else:
            assert dimensions['straight_length_mm']==3800 and dimensions['overall_body_length_mm']==4350
            assert dimensions['saddle_center_distance_mm']==2000 and dimensions['axis_height_mm']==700
            assert len(params['ports'])==11 and dimensions['top_nozzles']==9 and dimensions['bottom_nozzles']==2
            assert all(q['normal'][2]>0.99 for q in params['ports'][:9])
            assert all(q['normal'][2]<-.99 for q in params['ports'][9:])
        # All copied civil exports are immutable; evaluate their original local
        # pairing rather than moving the pads to make a result look resolved.
        local=[]
        for folder in (out/'基础').iterdir() if (out/'基础').exists() else []:
            fid=folder.name
            for p in (CIVIL/fid).iterdir():
                if p.suffix in ['.js','.obj','.glb','.mtl']:assert (folder/p.name).read_bytes()==p.read_bytes(),str(p)
            support=mesh(folder/'model_data.js');hits=intersections(parts,support,(0,0,0))
            local.append({'civil':fid,'solid_intersections':hits,'geometry':'byte-identical','translation_mm':[0,0,0]})
        limits=list(params['limits'])
        if key=='L41B05':limits.append('新两鞍座足底在X±1000；原单墩居中不能承托两足，且与底部h排口同位，禁止把该组合认定为安装方案')
        report={'version':params['version'],'status':'checked-with-open-installation-items','old_XYZ_rotation_mirror':'unchanged','new_assembly_instances':0,'geometry_parts':len(parts),'bounds_mm':params['bounds_mm'],'civil_local_checks':local,'limits':limits}
        save(out/'支承复核.json',report);save(out/'校验报告.json',{'status':'passed','version':params['version'],'core_and_source_checks':'passed','placement_preservation':'passed','civil_intersection_pairs':sum(len(r['solid_intersections']) for r in local),'installation_approval':False});reports[key]={'parts':len(parts),'civil_intersection_pairs':sum(len(r['solid_intersections']) for r in local)}
    if {'F41B02','F41B05','F41B06'}<=set(selected):
        bodies=[mesh(ROOT/f'版本/2.0/{key}/设备/model_data.js') for key in ['F41B02','F41B05','F41B06']];assert bodies[0]==bodies[1]==bodies[2]
    save(BATCH/'校验报告.json',{'status':'passed','checked_classes':selected,'reviewed_groups':35,'reviewed_items':99,'model_revision_items':58,'retained_items':41,'scene_items':72,'unplaced_items':27,'original_positions_and_civil_instances':'unchanged','classes':reports,'limits':'通过的是来源/几何导出/版本隔离校验，未决制造及安装项不因此解除'})
    print(json.dumps({'status':'passed','checked_classes':selected,'reviewed_items':99,'classes':reports},ensure_ascii=False))

if __name__=='__main__':run(sys.argv[1:] or CLASSES)
