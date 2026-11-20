"""F41B04: preserve the current tube; align its datum with the documented round base."""
from pathlib import Path
import copy,json,shutil,subprocess,sys
import ezdxf
from build_c41b04_v2 import save,sha
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/F41B04'
VERSION='2.0-F41B04-01'
SOURCE='水解桥架工程/data/原始资料/设备基础/水解设备基础图_增补烟囱及洗涤塔钢塔架_20261106.dxf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
OLD='水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
BASESRC=REPO/'水解桥架工程/models/设备/设备基础_20261106'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script

def pin():
    p=OUT/'本批保护基准.json'
    if p.exists():return json.loads(p.read_text())
    project=json.loads((ROOT/'project.json').read_text());prefixes=['厂房外观模型/','水解桥架工程/']+['水解设备模型库/版本/2.0/'+k+'/' for k in project['revisions']]
    names=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    data={'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO).decode().strip(),'assembly':json.loads((REPO/'水解总装工程/assembly.json').read_text()),'catalog':json.loads((ROOT/'catalog.json').read_text()),'protected_files':{n:sha(REPO/n) for n in names if n and not n.endswith('/校验报告.json') and any(n.startswith(q) for q in prefixes)}}
    save(p,data);return data

def native():
    d=ezdxf.readfile(REPO/SOURCE);right=d.entitydb['8DFD'];left=d.entitydb['8DFF'];dim=d.entitydb['8ED2']
    floor=float(dim.dxf.defpoint2.y);bottom=float(right.dxf.start.y);top=float(right.dxf.end.y)
    layout=ezdxf.readfile(REPO/LAYOUT);circle=layout.entitydb['33EAC']
    return {'source':SOURCE,'tube_handles':['8DFD','8DFE','8DFF'],'base_height_handle':'8ED2','steel_foot_height_handle':'8ED8','floor_label':'8E0F','floor_y':floor,'tube_bottom_y':bottom,'tube_top_y':top,'measured_tube_height_mm':top-bottom,'measured_OD_mm':abs(right.dxf.start.x-left.dxf.start.x),'measured_bottom_above_floor_mm':bottom-floor,'dimension_bottom_above_floor_mm':float(dim.dxf.actual_measurement),'plan_circle_handle':'8F98','plan_circle_diameter_mm':2*float(d.entitydb['8F98'].dxf.radius),'layout_circle':{'handle':'33EAC','center_source_mm':list(circle.dxf.center)[:2],'radius_mm':float(circle.dxf.radius)},'adopted_model_mm':[1000,15100],'height_conflicts_mm':{'ledger':17000,'old_side':11000,'new_steel_elevation_measured':top-bottom,'current_rounded_display':15100},'policy':'保留当前Ø1000×15100筒体原网格；高度及新版平面Ø1100差异明示待核。仅改有明确尺寸依据的筒底高差300。'}

def main():
    baseline=pin();trace=native();old=next(q for q in baseline['assembly']['equipment'] if q['id']=='F41B04')
    source=REPO/baseline['assembly']['assets']['F41B04']['source'];src=source.parent
    for folder,origin in [('设备',src),('基础',BASESRC/'F41B04'),('钢塔架',BASESRC/'F41B04-钢塔架')]:
        target=OUT/folder;target.mkdir(parents=True,exist_ok=True)
        for p in origin.iterdir():
            if p.suffix in ['.js','.obj','.mtl','.glb']:shutil.copy2(p,target/p.name)
        if folder!='设备':
            param=json.loads((origin/'参数.json').read_text());param.update(version=VERSION,source_drawing=FOUND if folder=='基础' else SOURCE,geometry_status='原几何逐字节保留',installation_scope='圆基础随已确认中心进入总装；钢塔架方位未核，仅独立对照' if folder=='基础' else '仅局部同心展示，不在厂房总装中实例化');save(target/'参数.json',param)
    install=copy.deepcopy(old);install.update(position_mm=[*old['position_mm'][:2],23300],equipment_version=VERSION,z_status='有安装基准',z_basis='增补钢塔架背立面8ED2：筒底在楼面23.000以上300，与圆基础顶23.300同高；总装筒底EL123.300。仅Z基准明确，总高/锚固仍待核。',local_datum='筒体下端Z0，世界EL123.300；当前显示筒高15100未作制造确认',orientation_status='圆截面只确认中心；钢塔架与底部锚固的共同绝对方位待核')
    install['installation_review']={'before_position_mm':old['position_mm'],'before_rotation_deg':old['rotation_deg'],'retained_xy_and_rotation':True,'z_correction_mm':300,'source_handle':'8ED2','base_top_EL':123.3,'body_top_display_EL':138.4,'height_confirmation':'17000/11000/约15100差异待核；本次保留现模型15100','anchorage':'缺设备底连接详图，不造底法兰/地脚孔或接口'}
    base={'id':'BASE-F41B04','name':'尾气烟囱圆基础','asset':'foundation-F41B04','position_mm':[*old['position_mm'][:2],23300],'rotation_deg':0,'level':'EL123','support_for':'F41B04','status':'基础底EL123.000、顶EL123.300；锚固连接待设备详图'}
    save(OUT/'安装表.json',[install]);save(OUT/'基础安装表.json',[base]);save(OUT/'俯侧视量测.json',trace)
    limits=['当前直筒外径1000/显示高15100保留；新背立面实量15098.60圆整为15100，台账17000及旧侧视11000差异未解决。','新版钢架平面圆直径约1099.76，与台账及立面1000不同，不能据此放大原筒体。','原壁厚16为显示值；现无制造总图/底部锚固详图，不补造底法兰、地脚孔或未画出的侧口。','圆基础和钢塔架源几何均保持，200mm螺栓露头沿用原展示口径；锚栓没有已确认的设备连接板。','筒底基准与基础顶的相对300mm可确认，不等于整机高度和锚固验收；钢架绝对方位未核，不加入厂房总装。']
    params={'version':VERSION,'name':'尾气烟囱','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'original_active_mesh':source.relative_to(REPO).as_posix(),'geometry_status':'本体网格、材质、法线和导出逐字节保持','dimensions_mm':{'OD':1000,'display_height':15100,'display_wall':16,'floor_to_bottom':300},'bounds_mm':[1000,1000,15100],'datum':'筒底Z0；独立组合基础顶Z0、钢架楼面Z-300；总装筒底EL123.300','height_differences':trace['height_conflicts_mm'],'ports':[],'support_status':'仅筒底与基顶同高；底部锚固连接和钢架方位待详图','limits':limits,'installation':install}
    save(OUT/'设备/参数.json',params);save(OUT/'支承复核.json',{'version':VERSION,'status':'pending-relative-check','round_base':'Ø1400×300、50二次浇筑、PCD1200/12-M24，原几何不变','steel_frame':'原153构件保留；同心/原mount仅作局部检查','anchors':'缺设备底部连接板，不能认定锚固链闭合','steel_installed_in_plant':False,'base_installed_in_plant':True})
    save(OUT/'来源与差异.json',{'version':VERSION,'sources':{p:sha(REPO/p) for p in [SOURCE,FOUND,OLD,LAYOUT,LEDGER]},'changed':['总装筒底Z23000改23300，X/Y/旋转保持','补入同心圆基础实例，基础底23000/顶23300','3种高度和Ø1000/平面约Ø1100差异单列，底锚固及钢架方位继续待核'],'preserved':['原筒体全部几何/材质/法线/GLB/OBJ','原圆基础与153件钢塔架','其他98项台账、71条设备位置及原基础/建筑/桥架','1.0和原始图纸'],'limits':limits})
    registry(params,install)
    from publish_f41b04 import publish
    publish();print(json.dumps({'version':VERSION,'geometry':'unchanged','z_mm':[23000,23300],'new_round_base':1,'steel_in_plant':False},ensure_ascii=False))

def registry(params,install):
    catalog=json.loads((ROOT/'catalog.json').read_text());row=next(q for q in catalog['models'] if q['id']=='F41B04')
    files={'model':'版本/2.0/F41B04/设备/model_data.js','glb':'版本/2.0/F41B04/设备/F41B04.glb','obj':'版本/2.0/F41B04/设备/F41B04.obj','parameters':'parameters/F41B04.json','installation':'版本/2.0/F41B04/安装表.json'}
    row.update(model_version=VERSION,model_spec='Ø1000×15100原筒体；筒底EL123.300，整机高度/锚固待核',position_mm=install['position_mm'],rotation_deg=install['rotation_deg'],current_files=files,position_basis=install['z_basis']);save(ROOT/'catalog.json',catalog)
    save(ROOT/'parameters/F41B04.json',{**params,'id':'F41B04','group':'F41B04','qty':1,'position_mm':install['position_mm'],'rotation_deg':install['rotation_deg'],'z_status':install['z_status'],'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/F41B04.json'})
    project=json.loads((ROOT/'project.json').read_text());project['revisions']['F41B04']={'version':VERSION,'equipment':'版本/2.0/F41B04/设备/model_data.js','foundation':'版本/2.0/F41B04/基础/model_data.js','foundation_single':'版本/2.0/F41B04/基础/model_data.js','placements':'版本/2.0/F41B04/安装表.json','support_placements':'版本/2.0/F41B04/基础安装表.json','support_review':'版本/2.0/F41B04/支承复核.json','status':'原筒体15100保持，筒底修正300并补圆基础；总高、底锚固和塔架方位待核'}
    count=sum(q['id'][:6] in project['revisions'] for q in catalog['models']);project.update(active_version='2.0（'+'、'.join(project['revisions'])+'）',next_class='L41B03');project['counts'].update(completed_batches=len(project['revisions']),revised_items=count,other_items_unchanged=99-count);save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=script(path,'EQUIPMENT_VERSION_OVERRIDES');o['version']=VERSION;o['equipment']['F41B04']={'dir':'版本/2.0/F41B04/设备/','bounds':params['bounds_mm'],'default_equipment_only':True}
    index=json.loads((BASESRC/'基础索引.json').read_text())['assets']
    for key,folder in [('F41B04','基础'),('F41B04-钢塔架','钢塔架')]:
        cfg=copy.deepcopy(index[key]);cfg.update(dir='版本/2.0/F41B04/'+folder+'/',combined_label='设备与圆基础（锚固待核）' if folder=='基础' else '局部塔架对照（方位待核）',note='筒体和基础/塔架原网格保持。高度口径和底部锚固待核；塔架仅独立对照。');o['foundations'][key]=cfg
    o['ledger']['F41B04']={'状态':'2.0安装基准修正 · 总高/锚固待核','建模口径或缺项':'保留原Ø1000×15100；台账17000/旧图11000/新立面约15100差异待核。总装筒底EL123.300，补同心圆基础；不造底法兰/接口，钢架方位待核。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')
    progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=VERSION,revised_items=count,unchanged_items=99-count,next_class=project['next_class'])
    for q in progress['rows']:
        if q['位号组']=='F41B04':q.update(本批状态='保留15100筒体，筒底修正300并补圆基础；高度/底锚固/塔架方位待核',本批依据='台账53行；增补钢架图8DFD/8DFE/8DFF及8ED2、圆基础图、屋面圆33EAC',Z有安装基准=1,Z待核=0)
    save(ROOT/'data/设备整改进度.json',progress)
    from publish_equipment_index import publish
    publish()
if __name__=='__main__':main()
