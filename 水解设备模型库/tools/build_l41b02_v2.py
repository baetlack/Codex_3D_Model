"""L41B02: use the original side outline; retain the civil sources and pending location."""
from pathlib import Path
import copy, json, math, shutil, subprocess, sys
import numpy as np
from build_c41b04_v2 import geo, sha, save, ring, plate, pipe, export, BODY, STEEL
from read_equipment_dxf import read_drawing

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/L41B02'
VERSION='2.0-L41B02-01'
SOURCE='水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
FRAME='水解桥架工程/data/原始资料/设备基础/水解设备基础图_增补烟囱及洗涤塔钢塔架_20261106.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
BASESRC=REPO/'水解桥架工程/models/设备/设备基础_20261106'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script

def pin():
    path=OUT/'本批保护基准.json'
    if path.exists():return
    project=json.loads((ROOT/'project.json').read_text());prefixes=['厂房外观模型/','水解桥架工程/']+['水解设备模型库/版本/2.0/'+k+'/' for k in project['revisions']]
    names=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={n:sha(REPO/n) for n in names if n and not n.endswith('/校验报告.json') and any(n.startswith(p) for p in prefixes)}
    save(path,{'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO).decode().strip(),'catalog':json.loads((ROOT/'catalog.json').read_text()),'assembly':json.loads((REPO/'水解总装工程/assembly.json').read_text()),'protected_files':protected})

def trace():
    paths,_=read_drawing(REPO/SOURCE)
    by={p.handle:p for p in paths if p.parent==p.handle}
    body=by['269D'].points;cx=sum(x for x,y in body)/2;z0=by['26FF'].points[0][1]
    def height(h):return sum(y-z0 for x,y in by[h].points)/len(by[h].points)
    def span(h):
        p=np.array(by[h].points);return float(np.ptp(p[:,0])),float(np.ptp(p[:,1]))
    return {'source':SOURCE,'side_origin_xy':[cx,z0],'plan_root':'2E93','plan_use':'仅取西侧低口、北侧大口、南侧四口的相对方位；未确认厂房绝对方向',
        'shell_OD':span('269D')[0],'shell_top_z':height('269D'),'top_flange_z':height('26F4'),'top_flange_OD':span('26F4')[0],
        'north_big_z':height('269B'),'south_low_z':(height('26FC')+height('26FE'))/2,
        'south_middle_z':(height('26D4')+height('26D5'))/2,'south_upper_z':(height('26E9')+height('26EA'))/2,'south_high_z':(height('26EF')+height('26F0'))/2,
        'south_middle_flange_OD':span('26D6')[1],'south_upper_flange_OD':span('26EB')[1],'south_high_flange_OD':span('26F1')[1],
        'anchor_plate_outer_diameter':abs(by['2707'].points[-1][0]-cx)+abs(by['2717'].points[-1][0]-cx),
        'side_handles':['269D','269B','26D1','26D2','26D3','26D4','26D5','26D6','26E9','26EA','26EB','26EF','26F0','26F1','26F4','26F7','26FA','26FB','26FC','26FD','26FE','26FF','2705','2707','2708','2709','2717','2718','2719'],
        'view_conflicts':{'top_flange_OD':{'side':955,'plan':1182.5},'anchor_plate_OD':{'side':2600,'plan':2750},'policy':'立面/本体外形采用同一侧视口径，底锚圈采用侧视与专用基础图的Ø2400螺栓圆配套；俯视仅取方位。不同视图外径差异保留，待制造总图。'},
        'excluded':'2689的2800×100支承示意块不属于设备净模，不替代专用基础图。喷淋锥线、内管及除雾内件不展开为外部构件。'}

def equipment():
    geo.parts.clear()
    # A flat bottom with the visible R50 corner, rather than the old 130-high cylinder.
    profile=[(1050+50*math.sin(t),50-50*math.cos(t)) for t in np.linspace(0,math.pi/2,13)]
    n=96;verts=[(0,0,0),(0,0,50)];faces=[]
    for r,z in profile:verts.extend((r*math.cos(a),r*math.sin(a),z) for a in np.linspace(0,2*math.pi,n,endpoint=False))
    for j in range(n):
        k=(j+1)%n;faces.extend([[0,2+k,2+j],[1,2+(len(profile)-1)*n+j,2+(len(profile)-1)*n+k]])
    for i in range(len(profile)-1):
        for j in range(n):
            k=(j+1)%n;a=2+i*n;faces.append([a+j,a+k,a+n+k,a+n+j])
    geo.add('本体_封底及R50转角',BODY,verts,faces)
    geo.ring('本体_塔身OD2200',50,9400,1100,1082,BODY,96)
    geo.hollow_frustum('本体_塔顶锥段',9400,10100,1100,400,18,BODY,96)
    ring('接口_顶部接管',(0,0),10100,10300,400,382,BODY,96)
    ring('接口_顶部法兰OD955',(0,0),10280,10300,477.5,382,STEEL,96)
    # Side L-shaped support section: circumferential continuity remains a display assumption.
    ring('支撑_底部立边示意',(0,0),0,220,1141.95,1120.97,STEEL,96)
    geo.hollow_frustum('支撑_底部过渡示意',220,240.97,1141.95,1100,20.98,STEEL,96)
    outer=[(1300*math.cos(a),1300*math.sin(a)) for a in np.linspace(0,2*math.pi,96,endpoint=False)]
    # Inner opening and the twelve anchor holes are actual openings in the mesh.
    holes=[(0,0,1120.97)]+[(1200*math.cos(a),1200*math.sin(a),15) for a in np.linspace(0,2*math.pi,12,endpoint=False)]
    plate('支撑_底锚圈12孔',outer,holes,0,20)
    ports=[]
    for name,axis,z,ro,flange,end in [('西侧低口',(-1,0,0),250,100,160,1443.8),('北侧大口',(0,1,0),1500,400,477.5,1300),('南侧下口',(0,-1,0),800,300,377.5,1280),('南侧中下',(0,-1,0),5000,125,187.5,1270),('南侧中上',(0,-1,0),7000,125,187.5,1270),('南侧上口',(0,-1,0),8900,125,187.5,1270)]:
        v=np.array(axis,float);start=v*1080;neck=v*(end-20);face=v*end
        for p in (start,neck,face):p[2]=z
        pipe('接口_'+name+'_接管',start,neck,ro,max(ro-18,1),BODY)
        pipe('接口_'+name+'_法兰',neck,face,flange,max(ro-18,1))
        ports.append({'id':name,'center_mm':face.tolist(),'normal':list(axis),'neck_OD_mm':2*ro,'flange_OD_mm':2*flange,'basis':'侧视外轮廓图面量测；西侧伸出量沿用俯视，非确认DN/制造尺寸'})
    ports.append({'id':'顶部','center_mm':[0,0,10300],'normal':[0,0,1],'neck_OD_mm':800,'flange_OD_mm':955,'basis':'侧视26F4/26F7；俯视外径差异待核'})
    return ports,export(OUT/'设备','L41B02')

def civil():
    for key,folder in [('L41B02','基础'),('L41B02-钢塔架','钢塔架')]:
        source=BASESRC/key;target=OUT/folder;target.mkdir(parents=True,exist_ok=True)
        for p in source.iterdir():
            if p.suffix in ['.js','.glb','.obj','.mtl']:shutil.copy2(p,target/p.name)
        data=json.loads((source/'参数.json').read_text());data.update(version=VERSION,source_drawing=FOUND if folder=='基础' else FRAME,geometry_status='既有几何逐字节保留；本轮仅核对与新本体的相对关系',location_status='绝对平面定位待核，不加入总装')
        save(target/'参数.json',data)

def registry(params):
    catalog=json.loads((ROOT/'catalog.json').read_text())
    row=next(q for q in catalog['models'] if q['id']=='L41B02')
    files={'model':'版本/2.0/L41B02/设备/model_data.js','glb':'版本/2.0/L41B02/设备/L41B02.glb','obj':'版本/2.0/L41B02/设备/L41B02.obj','parameters':'parameters/L41B02.json','installation':'版本/2.0/L41B02/安装表.json'}
    row.update(model_version=VERSION,model_spec='侧视Ø2200×10300；侧口/底锚圈修正；视图外径差异及绝对定位待核',current_files=files)
    save(ROOT/'catalog.json',catalog);save(ROOT/'parameters/L41B02.json',{**params,'id':'L41B02','qty':1,'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/L41B02.json'})
    project=json.loads((ROOT/'project.json').read_text());project['revisions']['L41B02']={'version':VERSION,'equipment':'版本/2.0/L41B02/设备/model_data.js','foundation':'版本/2.0/L41B02/基础/model_data.js','placements':'版本/2.0/L41B02/安装表.json','support_review':'版本/2.0/L41B02/支承复核.json','status':'按原侧视修正侧口/底锚圈；基础和钢塔架保留，绝对定位及视图差异待核'}
    revised=sum(q['id'][:6] in project['revisions'] for q in catalog['models']);project['active_version']='2.0（'+'、'.join(project['revisions'])+'）';project['counts'].update(completed_batches=len(project['revisions']),revised_items=revised,other_items_unchanged=99-revised);project['next_class']='F41B04'
    save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=script(path,'EQUIPMENT_VERSION_OVERRIDES');o['version']=VERSION;o['equipment']['L41B02']={'dir':'版本/2.0/L41B02/设备/','bounds':params['bounds_mm'],'default_equipment_only':True}
    for key,folder in [('L41B02','基础'),('L41B02-钢塔架','钢塔架')]:
        cfg=copy.deepcopy(json.loads((BASESRC/'基础索引.json').read_text())['assets'][key]);cfg['dir']='版本/2.0/L41B02/'+folder+'/'
        cfg['combined_label']='局部对照（配套相交待核）' if folder=='钢塔架' else '设备与圆基础（定位待核）'
        cfg['note']='相对对照采用原同心关系；钢塔架/接口相交见本类支承复核，绝对位置与视图外径差异待核。'
        o['foundations'][key]=cfg
    o['ledger']['L41B02']={'状态':'2.0侧视修正 · 整体待定位','建模口径或缺项':'按侧视修正侧口250/800/1500/5000/7000/8900及底锚圈；侧/俯外径冲突保留。钢塔架和基础保持，绝对定位、底部环向构造及制造细部待核。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')
    progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=VERSION,revised_items=revised,unchanged_items=99-revised,next_class=project['next_class'])
    for q in progress['rows']:
        if q['位号组']=='L41B02':q.update(本批状态='侧视本体/侧口及底锚圈修正；基础与塔架保留，绝对定位/视图差异待核',本批依据='原示图侧视2689—2723、俯视2E93；专用圆基础图与增补钢塔架图')
    save(ROOT/'data/设备整改进度.json',progress)
    from publish_equipment_index import publish
    publish()

def main():
    pin();t=trace();ports,bounds=equipment();civil();save(OUT/'俯侧视量测.json',t)
    limits=['仅原示图及专用基础/塔架图，未获本类制造总图；CAD量测不等于标注制造尺寸。','侧/俯顶法兰955/1182.5、底锚圈2600/2750有差异；本轮外形统一采用侧视，工艺方位待核。','壁厚18、法兰厚20、螺栓孔Ø30为显示值；底部立边的环向连续表达待详图，不当作制造确认。','不展开内部喷淋、喷淋锥线、除雾件及伸入/伸出本体的工艺管线。','基础楼面23.000、基顶23.300及塔架顶31.300为相对组合依据；厂房绝对X/Y仍未知，不沿用旧文字插点作中心，不加入总装。']
    params={'version':VERSION,'name':'尾气洗涤塔','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'ledger_source':LEDGER,'ledger_row':105,'qty':1,'dimensions_mm':{'shell_OD':2200,'nominal_top_z':10300,'shell_top_z':9400,'neck_start_z':10100,'top_neck_OD':800,'top_flange_OD':955,'bottom_fillet_R':50,'anchor_plate_OD':2600,'anchor_hole_PCD':2400,'anchor_hole_count':12,'display_anchor_hole_OD':30},'ports':ports,'bounds_mm':bounds,'datum':'侧视封底最低面/锚板底Z0；圆基础顶Z0，钢塔架局部楼面按旧mount=-300对照','location_status':'待定位；旧文字插点不是设备中心','limits':limits}
    save(OUT/'设备/参数.json',params);save(OUT/'安装表.json',[])
    save(OUT/'安装待核.json',{'id':'L41B02','status':'待定位，不加入总装','legacy_text_insert_mm':[661756,347460],'reason':'尚无可唯一关联的平面设备中心；文字插点不作为中心','relative_datum':'基础楼面EL123、基顶EL123.300、钢架顶EL131.300只用于局部对照','pending':['设备实际中心X/Y','绝对工艺方位','侧视/俯视外径差异','底部立边环向构造与制造详图']})
    save(OUT/'支承复核.json',{'version':VERSION,'status':'pending-mesh-review','absolute_location':'unplaced','datum':'局部同心对照，圆基础顶Z0、钢塔架楼面Z-300；不是绝对安装确认','foundation_geometry':'unchanged','steel_geometry':'unchanged','tower_floor_EL':123,'base_top_EL':123.3,'frame_top_EL':131.3,'note':'原基础图23.000按总装EL100=本地0换算；不把旧EL112文字插点认定为新安装依据。','assembly_instances_added':0})
    save(OUT/'来源与差异.json',{'version':VERSION,'sources':{p:sha(REPO/p) for p in [SOURCE,FOUND,FRAME,LEDGER]},'changed':['侧口标高250/800/1500/5000/7000/8900，尺寸按侧视统一','四个推断托座改为底锚圈及立边表达，12孔与原基础螺栓圆同心','塔身/锥段分界9400、顶颈10100，顶法兰外955'],'preserved':['原始图纸、1.0、原基础与钢塔架几何','其他98项台账及72条已就位设备/建筑/桥架'],'limits':limits,'view_conflicts':t['view_conflicts']})
    registry(params)
    from publish_l41b02 import publish
    publish()
    print(json.dumps({'version':VERSION,'ports':len(ports),'bounds_mm':bounds,'placed':False},ensure_ascii=False))
if __name__=='__main__':main()
