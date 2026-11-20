"""F41B03: correct the four-hole plan and keep unproved bearing details unresolved.

Only a Ø1000×1000 straight section and a plan are available. The Ø1100
centre-line circle is a hole pitch circle, not a pair of physical end rings.
"""
from pathlib import Path
import copy,json,math,shutil,sys
import ezdxf,numpy as np
from ezdxf.disassemble import recursive_decompose
from build_c41b04_v2 import geo,sha,save,plate,export,BODY,STEEL
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/F41B03'
VERSION='2.0-F41B03-01'
SOURCE='水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script

def plan_data(d):
    center=np.array(d.entitydb['3623'].dxf.center)[:2];root=d.entitydb['3625'];records=[]
    for e in recursive_decompose([root]):
        if e.dxftype()!='LINE':continue
        a=np.array(e.dxf.start)[:2]-center;b=np.array(e.dxf.end)[:2]-center
        if abs(a[0]-b[0])<.001 and abs(a[0]-591.25)<.01 and abs(a[1]-b[1])>100:
            tangent=max(abs(a[1]),abs(b[1]))
            # Native line 362A is the upper radial edge: its inward endpoint
            # overlaps the nominal shell, rather than stopping in free space.
            rmin=591.25-2*d.entitydb['3629'].dxf.start.x
            records.append({'outer_radius_mm':float(a[0]),'inner_radius_mm':float(rmin),'half_tangent_mm':float(tangent)})
    assert len(records)==1,records
    holes=[]
    for e in recursive_decompose([root]):
        if e.dxftype()=='CIRCLE':
            xy=np.array(e.ocs().to_wcs(e.dxf.center))[:2]-center
            holes.append({'xy_mm':xy.round(7).tolist(),'radius_mm':float(e.dxf.radius)})
    assert len(holes)==4
    return {'center_source_mm':center.tolist(),'root_handle':'3625','body_handle':'3623','pitch_circle_handle':'3626','pitch_circle_radius_mm':float(d.entitydb['3626'].dxf.radius),'ear_profile':records[0],'holes':holes}

def main():
    pin=json.loads((OUT/'本批保护基准.json').read_text());old=next(p for p in pin['equipment_placements'] if p['id']=='F41B03')
    d=ezdxf.readfile(REPO/SOURCE);trace=plan_data(d)
    original=script(REPO/'水解设备模型库/示图建模_20260521/模型/F41B03/model_data.js','MODEL_PARTS')
    shell=next(p for p in original if p['name']=='本体_直筒段')
    geo.parts[:]=[(shell['name'],shell['color'],shell['vertices'],shell['faces'])]
    profile=trace['ear_profile'];r0=profile['inner_radius_mm'];r1=profile['outer_radius_mm'];w=profile['half_tangent_mm']
    for i,degrees in enumerate([0,90,180,270],1):
        plate(f'托耳_R{i}_带孔底板',[(r0,-w),(r1,-w),(r1,w),(r0,w)],[(550,0,8.25)],0,24,angle=math.radians(degrees))
    bounds=export(OUT/'设备','F41B03')
    # Preserve the actual older shell including its original smoothed normals.
    # Export recomputes identical normals for this untouched component.
    base_src=REPO/'水解桥架工程/models/设备/设备基础_20261106/F41B03';base=OUT/'基础';base.mkdir(parents=True,exist_ok=True)
    for p in base_src.iterdir():
        if p.suffix in ['.js','.glb','.obj','.mtl']:shutil.copy2(p,base/p.name)
    fp={'version':VERSION,'name':'冷凝水分汽器四支墩（独立展示）','source_drawing':FOUND,'source_sha256':sha(REPO/FOUND),'units':'mm','source_geometry':'水解桥架工程/models/设备/设备基础_20261106/F41B03/model_data.js','geometry_change':'原四支墩与预埋板几何逐字节保持','pads_center_mm':[[750,0],[-750,0],[0,750],[0,-750]],'pad_size_mm':[300,300],'pad_inner_edge_mm':600,'embedded_plate_size_mm':[300,300,10],'display_height_mm':100,'datum':'支墩顶本地Z0；目前仅展示原100mm高露出段，不代表整根结构柱','status':'托耳与支墩无平面搭接；过渡件/托耳高度及全局承托EL待核','limits':['基础图2B06/07/08/09为750+750，2B10/11为300；图上绘制比例与数字不同，按尺寸数字。','2B52尺寸文字为板厚，不能将其残留图形500作为确认板厚；100mm沿用原露出段显示口径，绝对标高/结构构造仍待核。']}
    save(base/'参数.json',fp)
    max_corner=math.hypot(r1,w)
    relations={'version':VERSION,'status':'not-bearing','comparison_datum':'仅诊断平面搭接：耳底与支墩顶暂设同高Z0，不是厂房安装标高','direct_contact_area_mm2':0,'axis_outer_edge_gap_mm':round(600-r1,6),'ear_outer_corner_radius_mm':round(max_corner,6),'support_min_radius_mm':600,'minimum_radial_separation_mm':round(600-max_corner,6),'hole_radius_mm':550,'pad_center_radius_mm':750,'hole_to_embedded_plate_center_mm':200,'rotation_can_close_gap':False,'four_directions':[{'direction_deg':a,'ear_tip_mm':591.25,'support_inner_edge_mm':600,'axis_gap_mm':8.75,'hole_to_embedded_center_mm':200} for a in [0,90,180,270]],'unresolved':['连接过渡件形式/尺寸','托耳厚度/立筋高度/承托面相对筒段的位置','全局承托EL及POSEL112.200定义','完整侧视/总图、封头及管口形状/方位'],'civil_instances_added_to_assembly':0}
    save(OUT/'支承差异.json',relations)
    save(OUT/'俯视图面量测.json',trace)
    params={'version':VERSION,'name':'冷凝水分汽器','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'drawing_scope':'设备示图的俯视，非完整设备总图','ledger_source':LEDGER,'ledger_row':51,'ledger_quantity':1,'modeled_scope':'仅直筒段及四耳底板；不推断封头、盖板、工艺管口和立筋高度','dimensions_mm':{'straight_section_nominal_diameter':1000,'straight_section_height':1000,'display_shell_wall_thickness':12,'ear_plate_radial_mm':round(r1-r0,7),'ear_plate_tangent_mm':round(2*w,7),'ear_plate_display_thickness':24,'ear_outer_edge_radius':591.25,'hole_pitch_diameter':1100,'hole_diameter':16.5,'hole_angles_deg':[0,90,180,270]},'datum':'直筒段下端Z0；耳底Z0/厚24为沿用显示值，非确认承托面','bounds_mm':bounds,'removed_unsupported_parts':['本体_端缘（上）','本体_端缘（下）'],'ports':[],'ports_status':'未提供管口图，不以孔位分度圆代造管口/端部法兰','support_status':relations['status'],
        'limits':['台账明确的是直筒段Ø1000×1000，不代表整机总高；现无完整侧视/总图。','壁厚12、耳板厚24和耳底Z0沿用原显示口径，均待详图，不作为明示制造尺寸。','俯视可见双筋投影，但缺高度，不补造立筋三维外形。','Ø1100中心线是四安装孔分度圆，不是实体端圈；撤销原两道端圈。','四耳外缘591.25与支墩内缘600差8.75；孔心550与预埋板心750差200，搭接面积为0。旋转也不能使两者直接接触。','原X40000/Y41750、暂用原点Z12200及零旋转保留；圆轮廓仅能确认中心，管口方位与全局承托EL待核。','四支墩独立查看；诊断视图同高仅为检验平面差异，不当作总装安装方案，不补过渡钢板/支腿。']}
    save(OUT/'设备/参数.json',params)
    p=copy.deepcopy(old);p.update(equipment_version=VERSION,local_datum='直筒段下端Z0；耳底Z0仅沿用示意',z_status='待核',orientation_status='布置圆轮廓只确认中心；四耳共同方位及管口绝对方向待核',z_basis='保留原POSEL112.200作为筒段下端暂用原点；耳底位置及四墩承托EL未闭合，不能认定安装确认')
    p['installation_review']={'before_position_mm':old['position_mm'],'before_rotation_deg':old['rotation_deg'],'retained_xyz_and_rotation':True,'source_center_handle':'D9737','position_label_handle':'D973A','support_contact':'不成立：平面无搭接；过渡件与竖向承托链待核','civil_instances_added':0}
    save(OUT/'安装表.json',[p])
    save(OUT/'来源与差异.json',{'version':VERSION,'sources':{s:sha(REPO/s) for s in [SOURCE,FOUND,LAYOUT,LEDGER]},'adopted':['台账第51行直筒段Ø1000×1000、数量1','示图3623名义筒径、3626中心线孔圈、3625四耳及3630孔','基础图750+750、300×300与四预埋板位置','布置D9737圆心及D973A的POSEL112.200追溯'],
        'changed':['移除误把孔圈转成的上下两实体圈','四块实心托耳底板改按原俯视外轮廓及Ø16.5孔表达'],
        'preserved':['原直筒段网格','四支墩/预埋板全部几何','原就位XYZ及旋转；安装状态待核','1.0与其他设备/建筑/桥架'],
        'support_differences':relations,'limits':params['limits']})
    registry(params,p)
    from publish_f41b03 import publish
    publish()
    print(json.dumps({'version':VERSION,'parts':5,'holes':4,'bounds_mm':bounds,'axis_gap_mm':8.75,'embedded_center_offset_mm':200,'direct_bearing':False},ensure_ascii=False))

def registry(params,p):
    catalog=json.loads((ROOT/'catalog.json').read_text());files={'model':'版本/2.0/F41B03/设备/model_data.js','glb':'版本/2.0/F41B03/设备/F41B03.glb','obj':'版本/2.0/F41B03/设备/F41B03.obj','parameters':'parameters/F41B03.json','installation':'版本/2.0/F41B03/安装表.json'}
    for row in catalog['models']:
        if row['id']=='F41B03':row.update(model_version=VERSION,model_spec='仅Ø1000×1000直筒段；四耳/Ø16.5孔；孔圈Ø1100不作端圈；四墩支承未闭合',current_files=files,position_mm=p['position_mm'],rotation_deg=p['rotation_deg'],position_basis=p['z_basis'])
    save(ROOT/'catalog.json',catalog)
    save(ROOT/'parameters/F41B03.json',{**params,'id':'F41B03','group':'F41B03','qty':1,'position_mm':p['position_mm'],'rotation_deg':p['rotation_deg'],'z_status':'待核','current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/F41B03.json'})
    project=json.loads((ROOT/'project.json').read_text());project['revisions']['F41B03']={'version':VERSION,'equipment':'版本/2.0/F41B03/设备/model_data.js','foundation':'版本/2.0/F41B03/基础/model_data.js','placements':'版本/2.0/F41B03/安装表.json','support_review':'版本/2.0/F41B03/支承差异.json','status':'直筒段表达/四耳孔修正，撤销无依据端圈；四墩无搭接，过渡件/承托EL待核'}
    revised=sum(r['id'][:6] in project['revisions'] for r in catalog['models']);project['counts'].update(completed_batches=len(project['revisions']),revised_items=revised,other_items_unchanged=99-revised);project['active_version']='2.0（'+'、'.join(project['revisions'])+'）'
    if len(project['revisions'])==5:project['next_class']='L41B02'
    save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'));o['version']=VERSION;o['equipment']['F41B03']={'dir':'版本/2.0/F41B03/设备/','bounds':params['bounds_mm']}
    foundation=json.loads((REPO/'水解桥架工程/models/设备/设备基础_20261106/基础索引.json').read_text())['assets']['F41B03']
    foundation.update(dir='版本/2.0/F41B03/基础/',mount=None,dimensions='4个300×300支墩；轴向中心±750；原100高露出段仅作显示，承托EL待核',note='与四耳没有平面搭接：轴向边距8.75mm，孔心与预埋板心差200mm；过渡件及托耳高度待核，不提供安装组合。')
    o['foundations']['F41B03']=foundation;o['ledger']['F41B03']={'状态':'2.0校核修正 · 四墩支承待核','建模口径或缺项':'仅按台账Ø1000×1000直筒段与原俯视修正四耳/Ø16.5孔；Ø1100为孔圈，删除误作实体的两端圈。壁厚/耳厚及耳底高度仍示意；四墩边距8.75、孔心与预埋板心差200，不能直接支承。完整总图/过渡件/承托EL待核。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')
if __name__=='__main__':main()
