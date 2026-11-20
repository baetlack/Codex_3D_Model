"""L41B03: ledger size, reference-sheet proportions, independent civil frame."""
from pathlib import Path
import copy, json, math, shutil, subprocess, sys
import ezdxf
import numpy as np
from build_c41b04_v2 import geo, sha, save, ring, pipe, export, plate, BODY, STEEL
from check_assembly import script

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/L41B03'
VERSION='2.0-L41B03-01'
SOURCE='水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
CIVIL=REPO/'水解桥架工程/models/设备/设备基础_20261106/L41B03'

def pin():
    path=OUT/'本批保护基准.json'
    if path.exists():return
    project=json.loads((ROOT/'project.json').read_text())
    prefixes=['厂房外观模型/','水解桥架工程/']+['水解设备模型库/版本/2.0/'+k+'/' for k in project['revisions']]
    names=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={n:sha(REPO/n) for n in names if n and not n.endswith('/校验报告.json') and any(n.startswith(p) for p in prefixes)}
    save(path,{'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'catalog':json.loads((ROOT/'catalog.json').read_text()),'assembly':json.loads((REPO/'水解总装工程/assembly.json').read_text()),'protected_files':protected})

def trace():
    doc=ezdxf.readfile(REPO/SOURCE);db=doc.entitydb
    cone=float(db['25AA'].dxf.start.y);top=float(db['25C4'].dxf.start.y)
    side_d=float(db['25A4'].dxf.start.x-db['25A2'].dxf.start.x)
    raw={'side_root':'25D9','plan_root':'2F1D','side_OD':side_d,'plan_OD':float(db['2EFE'].dxf.radius*2),'cone_tip_y':cone,'drain_face_y':float(db['25AC'].dxf.start.y),'cylinder_bottom_y':float(db['2598'].dxf.start.y),'cylinder_top_y':float(db['25A3'].dxf.start.y),'top_flange_y':top,'ear_bottom_y':float(db['25B7'].dxf.start.y),'lower_port_y':float(db['25C7'].dxf.center.y),'upper_port_y':float((db['25C0'].dxf.start.y+db['25C1'].dxf.start.y)/2),'ellipse_center_y':float(db['25BE'].dxf.center.y),'ellipse_major_radius':float(db['25BE'].dxf.major_axis.magnitude),'ellipse_ratio':float(db['25BE'].dxf.ratio)}
    raw['cone_to_top_height']=top-cone
    return {'source':SOURCE,'source_sha256':sha(REPO/SOURCE),'native':raw,'choice':'用户选择保留台账Ø1800×3100，参照原示图修正外形与接口；3100沿用锥尖至顶法兰口径，底排接管另计','xy_scale':1800/side_d,'z_scale':3100/(top-cone),'plan_to_model':'图纸平面逆时针90°转换，延续旧模型东侧下口/北侧偏东上口的局部轴向；不是厂房绝对方位','limits':['原示图无本体尺寸标注，图面量测不作制造尺寸','原图Ø2000/锥尖至顶约4168与台账Ø1800×3100差异保留','原设备示图框架高3000，专用基础图高2000；两者不得同时作为安装支承']}

def equipment(t):
    n=t['native'];s=t['xy_scale'];k=t['z_scale'];z=lambda y:(y-n['ear_bottom_y'])*k
    geo.parts.clear()
    geo.cyl('本体_下锥段',z(n['cone_tip_y']),z(n['cylinder_bottom_y']),32.5*s,BODY,96,900)
    geo.cyl('本体_直筒',z(n['cylinder_bottom_y']),z(n['ellipse_center_y']),900,BODY,96)
    # Elliptical head, truncated at the top neck. No internal demister blades.
    profile=[(900*math.cos(a),z(n['ellipse_center_y']+n['ellipse_major_radius']*n['ellipse_ratio']*math.sin(a))) for a in np.linspace(0,math.acos(.35),25)]
    verts=[(r*math.cos(a),r*math.sin(a),h) for r,h in profile for a in np.linspace(0,2*math.pi,97)[:-1]]
    faces=[[j*96+i,j*96+(i+1)%96,(j+1)*96+(i+1)%96,(j+1)*96+i] for j in range(len(profile)-1) for i in range(96)]
    faces += [list(reversed(range(96))),list(range((len(profile)-1)*96,len(profile)*96))]
    geo.add('本体_椭圆封头',BODY,verts,faces)
    top=z(n['top_flange_y']);neck_start=profile[-1][1]
    pipe('接口_顶部接管',(0,0,neck_start-2),(0,0,top-40),350*s,350*s-12,BODY)
    ring('接口_顶部法兰',(0,0),top-40,top,430*s,350*s-12)
    ports=[]
    for name,start,end,ro,rf,thick,normal in [
        ('东侧下口',(0,0,z(n['lower_port_y'])),(1180.063535*s,0,z(n['lower_port_y'])),250*s,322.5*s,30.063535*s,[1,0,0]),
        ('北侧偏东',(775*s,0,z(n['upper_port_y'])),(775*s,1050*s,z(n['upper_port_y'])),225*s,270*s,50*s,[0,1,0]),
        ('锥底排口',(0,0,z(n['cone_tip_y'])+4),(0,0,z(n['drain_face_y'])),32.5*s,92.5*s,20,[0,0,-1])]:
        a=np.array(start,float);b=np.array(end,float);v=np.array(normal);neck=b-v*thick
        pipe('接口_'+name+'接管',a,neck,ro,max(ro-8,1),BODY)
        pipe('接口_'+name+'法兰',neck,b,rf,max(ro-8,1))
        ports.append({'id':name,'center_mm':b.tolist(),'normal':normal,'neck_OD_mm':2*ro,'flange_OD_mm':2*rf,'basis':'原示图平面/侧视按用户所选主尺寸比例表达；标高、DN和厚度均未作制造确认'})
    # Four bearing plates from the reference plan. No unsupported bolt holes.
    inner=990*s;tip=1188.11*s;width=344.825*s;thick=20*k;rise=250*k
    for i,a in enumerate([0,math.pi/2,math.pi,3*math.pi/2],1):
        plate(f'托耳_{i}底板',[(inner,-width/2),(tip,-width/2),(tip,width/2),(inner,width/2)],[],0,thick,STEEL,a)
        dx,dy=math.cos(a),math.sin(a)
        for side in [-1,1]:
            profile=[(inner,thick),(tip,thick),(tip,70*k),(1060*s,rise),(inner,rise)]
            vertices=[(dx*r-dy*w,dy*r+dx*w,h) for w in [side*width*.3-7,side*width*.3+7] for r,h in profile]
            faces=[list(reversed(range(5))),list(range(5,10))]+[[j,(j+1)%5,(j+1)%5+5,j+5] for j in range(5)]
            geo.add(f'托耳_{i}筋板{side:+d}',STEEL,vertices,faces)
    bounds=export(OUT/'设备','L41B03')
    return ports,bounds,{'body_OD':1800,'cone_to_top':3100,'drain_projection':(n['cone_tip_y']-n['drain_face_y'])*k,'ear_to_top':top,'ear_to_drain':-z(n['drain_face_y']),'ear_outer_radius':tip,'ear_width':width,'plate_thickness_display':thick,'top_flange_thickness_display':40,'port_wall_display':8}

def registry(params):
    files={'model':'版本/2.0/L41B03/设备/model_data.js','glb':'版本/2.0/L41B03/设备/L41B03.glb','obj':'版本/2.0/L41B03/设备/L41B03.obj','parameters':'parameters/L41B03.json','installation':'版本/2.0/L41B03/安装待核.json'}
    catalog=json.loads((ROOT/'catalog.json').read_text());row=next(q for q in catalog['models'] if q['id']=='L41B03');row.update(model_version=VERSION,model_spec='台账Ø1800×3100；按原示图比例修正，绝对定位待核',current_files=files);save(ROOT/'catalog.json',catalog)
    save(ROOT/'parameters/L41B03.json',{**params,'id':'L41B03','group':'L41B03','qty':1,'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/L41B03.json'})
    project=json.loads((ROOT/'project.json').read_text());project['revisions']['L41B03']={'version':VERSION,'equipment':files['model'],'foundation':'版本/2.0/L41B03/钢支架/model_data.js','placements':'版本/2.0/L41B03/安装表.json','support_review':'版本/2.0/L41B03/支承复核.json','status':'台账主尺寸、示图比例修正；本体不含旧框架；原钢支架保留，绝对定位待核'}
    count=sum(q['id'][:6] in project['revisions'] for q in catalog['models']);project.update(active_version='2.0（'+'、'.join(project['revisions'])+'）',next_class='L41B04');project['counts'].update(completed_batches=len(project['revisions']),revised_items=count,other_items_unchanged=99-count);save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=script(path,'EQUIPMENT_VERSION_OVERRIDES');o['version']=VERSION;o['equipment']['L41B03']={'dir':'版本/2.0/L41B03/设备/','bounds':params['bounds_mm'],'default_equipment_only':True}
    cfg=copy.deepcopy(json.loads((CIVIL/'参数.json').read_text()));cfg.update(dir='版本/2.0/L41B03/钢支架/',offsets=[[0,-175,2000]],mount=[0,0,0],combined_label='设备与专用钢架（局部对照）',note='原31件钢支架保持，设备托耳Z0对齐钢架顶2000、开口中心Y-175；不是厂房绝对安装确认。');o['foundations']['L41B03']=cfg
    o['ledger']['L41B03']={'状态':'2.0外形/接口修正 · 绝对定位待核','建模口径或缺项':'用户选择台账Ø1800×3100；3100为锥尖至顶法兰，底排另计。原示图尺寸差异、接口/厚度及绝对方位待核；本体不再混入旧框架，专用钢架独立。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')
    progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=VERSION,revised_items=count,unchanged_items=99-count,next_class='L41B04')
    for q in progress['rows']:
        if q['位号组']=='L41B03':q.update(本批状态='用户保留台账主尺寸；本体/接口比例修正，撤下旧框架，钢支架/绝对位置待核',本批依据='原示图25D9/2F1D、台账107行、专用钢架3BA7/3B63；用户尺寸取舍')
    save(ROOT/'data/设备整改进度.json',progress)
    from publish_equipment_index import publish
    publish()

def main():
    pin();t=trace();ports,bounds,dimensions=equipment(t)
    doc=ezdxf.readfile(REPO/FOUND);measurements={}
    for handle in ['3B63','3BB6','3BB7','3BCD','3BCE']:
        e=doc.entitydb[handle];measurements[handle]={'dimension_value_mm':e.dxf.actual_measurement,'defpoint2':list(e.dxf.defpoint2),'defpoint3':list(e.dxf.defpoint3)}
    save(OUT/'钢架尺寸依据.json',{'source':FOUND,'sha256':sha(REPO/FOUND),'dimensions':measurements,'floor_text':{'3BBC':doc.entitydb['3BBC'].dxf.text,'3BBA':doc.entitydb['3BBA'].dxf.text},'note':'本图按标注尺寸值建模，图面端点间距为标注值的2倍；不可把图面2:1长度再次用于放大钢架'})
    target=OUT/'钢支架';target.mkdir(parents=True,exist_ok=True)
    for p in CIVIL.iterdir():
        if p.suffix in ['.js','.glb','.obj','.mtl']:shutil.copy2(p,target/p.name)
    civil=json.loads((CIVIL/'参数.json').read_text());civil.update(version=VERSION,geometry_status='原31件钢支架几何及导出逐字节保持',offsets=[[0,-175,2000]],relative_datum='新本体托耳底Z0；局部组合托耳放到平台顶2000；不是厂房定位');save(target/'参数.json',civil)
    limits=t['limits']+['接口/托耳的未标尺寸按示图比例表达；法兰厚、壁厚、筋板厚仍为显示值','钢架GZ1/GL1截面仍示意；仅验证模型承托与开口关系','绝对X/Y和工艺方位待核，不以文字插点放入总装；不新增孔/支腿或内部除雾叶片']
    params={'version':VERSION,'name':'旋流除雾器','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'user_choice':t['choice'],'dimensions_mm':dimensions,'bounds_mm':bounds,'datum':'四向托耳底Z0；局部钢架顶Z2000，设备中心对开口Y-175','ports':ports,'limits':limits,'status':'本体示图比例修正，绝对定位/制造详图待核'}
    save(OUT/'设备/参数.json',params);save(OUT/'俯侧视量测.json',t)
    save(OUT/'安装表.json',[])
    save(OUT/'安装待核.json',{'id':'L41B03','status':'待定位，不进入总装','legacy_text_insert_mm':[660751,343767],'absolute_position':None,'relative_offset_mm':[0,-175,2000],'relative_floor_EL':123,'relative_bearing_EL':125,'basis':'基础图23.000至25.000；只确认局部楼面—钢架顶高差，不代表厂房中心/方位已确认'})
    save(OUT/'支承复核.json',{'version':VERSION,'status':'pending-mesh-check','steel_geometry':'unchanged','steel_parts':31,'absolute_position':'unplaced','assembly_instances_added':0,'relative_offset_mm':[0,-175,2000]})
    save(OUT/'来源与差异.json',{'version':VERSION,'sources':{p:sha(REPO/p) for p in [SOURCE,FOUND,LEDGER]},'user_choice':t['choice'],'changed':['原示图模型30件中排除4立柱/4横梁；原净模已为22件，本轮新本体23件','上封头按椭圆轮廓，顶部/偏心上口/下口及锥底口按示图比例修正','四托耳尺寸参照平面；新局部原点为耳底，组合仍对钢架顶'],'preserved':['台账Ø1800×3100主尺寸，3100沿用锥尖至顶法兰口径','原31件专用钢支架/基础、1.0、原始资料','其他98项台账及72条就位记录、建筑和桥架；本类仍待定位'],'limits':limits})
    registry(params)
    from publish_l41b03 import publish
    publish();print(json.dumps({'version':VERSION,'bounds_mm':bounds,'body_parts':len(geo.parts),'placed':False},ensure_ascii=False))

if __name__=='__main__':main()
