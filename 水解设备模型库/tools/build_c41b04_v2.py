"""C41B04: model the manufacturer condition drawing and separate its steel support.

Local Z0 is the underside of four ear plates. Main end planes are -2612/+2200.
The source PDF, old equipment meshes, building, bridges and accepted C41B02 stay intact.
"""
from pathlib import Path
import argparse, copy, hashlib, json, math, sys
import numpy as np
from scipy.spatial import Delaunay
from matplotlib.path import Path as PolygonPath

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/C41B04'
sys.path.insert(0,str(REPO/'水解桥架工程/tools/source'))
import build_tank_mixer as geo
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script
VERSION='2.0-C41B04-02'
PDF='水解设备模型库/水解设备图纸/偏钛酸酸冷却器(C41B04A-F).pdf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
BODY='#a5b9c3';STEEL='#b7c8d0';DARK='#818b90';SEAL='#626f74'
BOTTOM=-2612.;TOP=2200.

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    p.parent.mkdir(parents=True,exist_ok=True);raw=(json.dumps(value,ensure_ascii=False,indent=2)+'\n').encode()
    baseline=ROOT/'版本/1.0/快照/水解设备模型库'/p.relative_to(ROOT)
    if baseline.exists() and b'\r\n' in baseline.read_bytes():raw=raw.replace(b'\n',b'\r\n')
    p.write_bytes(raw)
def move_last(x=0,y=0,z=0,angle=0):
    n,c,v,f=geo.parts[-1];co,si=math.cos(angle),math.sin(angle)
    geo.parts[-1]=(n,c,[(a*co-b*si+x,a*si+b*co+y,d+z) for a,b,d in v],f)
def cylinder(name,xy,z0,z1,r,color=STEEL,n=64):geo.cyl(name,z0,z1,r,color,n);move_last(*xy)
def ring(name,xy,z0,z1,ro,ri,color=STEEL,n=64):geo.ring(name,z0,z1,ro,ri,color,n);move_last(*xy)
def plate(name,outer,holes,z0,z1,color=STEEL,angle=0):
    loops=[np.asarray(outer,float)]+[np.array([[x+r*math.cos(t),y+r*math.sin(t)] for t in np.linspace(0,2*math.pi,49)[:-1]]) for x,y,r in holes]
    points=np.vstack(loops);tri=Delaunay(points).simplices;centers=points[tri].mean(1)
    keep=PolygonPath(outer).contains_points(centers,radius=1e-7)
    for x,y,r in holes:keep &= np.linalg.norm(centers-[x,y],axis=1)>r-1e-8
    faces=[];count=len(points)
    for t in tri[keep]:faces.extend([t[::-1].tolist(),(t+count).tolist()])
    offset=0
    for i,loop in enumerate(loops):
        for j in range(len(loop)):
            a=offset+j;b=offset+(j+1)%len(loop)
            faces.append([a,b,b+count,a+count] if i==0 else [b,a,a+count,b+count])
        offset+=len(loop)
    v=np.vstack([np.column_stack([points,np.full(count,z)]) for z in [z0,z1]])
    geo.add(name,color,v.tolist(),faces);move_last(angle=angle)
def pipe(name,start,end,ro,ri,color=STEEL):
    a=np.array(start,float);b=np.array(end,float);axis=b-a;axis/=np.linalg.norm(axis)
    u=np.cross(axis,[0,0,1] if abs(axis[2])<.9 else [0,1,0]);u/=np.linalg.norm(u);v=np.cross(axis,u)
    vertices=[];faces=[];count=64
    for c,r in [(a,ro),(b,ro),(a,ri),(b,ri)]:
        vertices.extend((c+r*u*math.cos(t)+r*v*math.sin(t)).tolist() for t in np.linspace(0,2*math.pi,count+1)[:-1])
    for i in range(count):
        j=(i+1)%count
        faces.extend([[i,j,count+j,count+i],[2*count+j,2*count+i,3*count+i,3*count+j],[count+i,count+j,3*count+j,3*count+i],[j,i,2*count+i,2*count+j]])
    geo.add(name,color,vertices,faces)
def equipment():
    geo.parts.clear();ports=[]
    # OD1300 outer shell, Ø1200 graphite block specification is kept separately.
    geo.cyl('本体_外壳OD1300',BOTTOM+360,TOP-360,650,BODY,96)
    geo.cyl('本体_下端收口',BOTTOM+120,BOTTOM+360,480,BODY,96,650)
    geo.cyl('本体_上端收口',TOP-360,TOP-220,650,BODY,96,600)
    geo.cyl('本体_上端集流盖',TOP-220,TOP-200,600,BODY,96)
    # User removed the two unsupported annular end plates and all 20 exposed
    # tie-rod/spring/nut assemblies. Keep the two existing collars on the body.
    for label,z in [('上',TOP-450),('下',BOTTOM+400)]:
        ring('本体_'+label+'端连接圈',(0,0),z,z+35,705,650)
    for label,x in [('N1',240),('N2',-240)]:
        xy=(x,390)
        ring('接口_'+label+'_接管',xy,TOP-220,TOP-24,109.5,100)
        ring('接口_顶盖法兰_'+label,xy,TOP-24,TOP,197.5,100)
        for i,a in enumerate(np.linspace(0,2*math.pi,13)[:-1],1):
            cylinder(f'紧固_{label}_{i:02}',(x+175*math.cos(a),390+175*math.sin(a)),TOP-12,TOP+2,8,DARK,6)
        ports.append({'id':label,'dn':200,'center_mm':[x,390,TOP],'normal':[0,0,1],'flange_OD_mm':395,'bolt_circle_mm':350,'bolt_count':12,'basis':'PDF主/俯视与管口表；法兰外廓395取布置DXF'})
    # Five separate process drains on Ø800; manufacturer gives DN50, BCD160/8M16.
    angles={'a':72,'b':0,'c':252,'d':180,'e':108}
    for label,degrees in angles.items():
        a=math.radians(degrees);xy=(400*math.cos(a),400*math.sin(a));label='N7'+label
        ring('接口_'+label+'_接管',xy,BOTTOM+20,BOTTOM+140,50,25)
        ring('接口_'+label+'_法兰',xy,BOTTOM,BOTTOM+20,100,25)
        ports.append({'id':label,'dn':50,'center_mm':[*xy,BOTTOM],'normal':[0,0,-1],'flange_OD_mm':200,'bolt_circle_mm':160,'bolt_count':8,'pitch_circle_mm':800,'basis':'PDF俯视与管口表；未标角度由布置DXF对应圆轮廓复核'})
    for label,z in [('N3',BOTTOM+830),('N4',TOP-802)]:
        pipe('接口_'+label+'_接管',(-640,0,z),(-834,0,z),162.5,150)
        pipe('接口_'+label+'_法兰',(-834,0,z),(-858,0,z),222.5,150)
        ports.append({'id':label,'dn':300,'center_mm':[-858,0,z],'normal':[-1,0,0],'flange_OD_mm':445,'drawing_azimuth_deg':270,'basis':'PDF标注轴向830/802、中心至端面858，管口表PL300(B)-10'})
    for label,z in [('N5',TOP-600),('N6',BOTTOM+600)]:
        pipe('接口_'+label+'_接管',(640,0,z),(756,0,z),21.25,16)
        pipe('接口_'+label+'_法兰',(756,0,z),(770,0,z),70,16)
        ports.append({'id':label,'dn':32,'center_mm':[770,0,z],'normal':[1,0,0],'flange_OD_mm':140,'shell_projection_mm':120,'drawing_azimuth_deg':90,'basis':'PDF明确DN32及外伸120；标高按主视图面约600暂取，非明示尺寸'})
    for i,degrees in enumerate([90,180,270,0],1):
        a=math.radians(degrees)
        plate(f'托耳_R{i}_承托底板',[(635,-125),(1027.5,-125),(1027.5,125),(635,125)],[(937.5,0,15)],0,20,angle=a)
        for side in [-1,1]:
            # A triangular web instead of a diagonal rectangular bar.
            v=[(x,y,z) for y in [side*86-6,side*86+6] for x,z in [(635,20),(1027.5,20),(635,350)]]
            geo.add(f'托耳_R{i}_三角筋{side}',STEEL,v,[[0,2,1],[3,4,5],[0,1,4,3],[1,2,5,4],[2,0,3,5]]);move_last(angle=a)
    # User removed only the upper lifting eye overlapping N5; retain the lower eye.
    for z in [BOTTOM+900]:
        plate('吊耳_带孔板',[(640,-90),(760,-50),(790,0),(760,50),(640,90)],[(740,0,22)],-12,12,DARK)
        n,c,v,f=geo.parts[-1];geo.parts[-1]=(n,c,[(x,t,z+d) for x,d,t in v],[list(reversed(face)) for face in f])
    return ports

def export(folder,stem):
    geo.export_model(folder,stem,color_materials=True,smooth=True)
    v=np.vstack([p[2] for p in geo.parts]);return (v.max(0)-v.min(0)).round(4).tolist()

def main(frame_policy):
    pinned=json.loads((OUT/'本批保护基准.json').read_text());old={p['id']:p for p in pinned['equipment_placements']}
    ports=equipment();bounds=export(OUT/'设备','C41B04')
    parameters={'version':VERSION,'name':'偏钛酸冷却器','units':'mm','source_drawing':PDF,'source_sha256':sha(REPO/PDF),'drawing_number':'SS-XYK1200-240S(10)','drawing_stage':'条件图','drawing_revision':'Rev.0 2026.01.09，图面2026.4.14签字','user_accuracy_reference':'C41B02-02当前外形及展示精度已获用户认可；按同等工程展示风格，不展开内部流道',
        'dimensions_mm':{'shell_OD':1300,'graphite_block_spec':1200,'end_face_height':4812,'top_to_bearing':2200,'bottom_to_bearing':2612,'lug_outer_span':2055,'lug_hole_span':1875,'lug_hole_diameter':30},
        'exchange_area_m2':240,'ledger_exchange_area_m2':230,'datum':'四向托耳底承托面Z0；底端面Z-2612，顶端面Z2200','installation':{'bearing_EL':104.5,'bottom_end_EL':101.888,'top_end_EL':106.7},'ports':ports,'bounds_mm':bounds,
        'limits':['外壳1300与换热块1200分别记录，不将传热面积当几何尺寸。','封头过渡、法兰未标厚度、吊耳及N5/N6准确标高按图面/旧DXF作展示量测。','按用户要求删除2个大开孔端环、20根通长外露杆及配套20个弹簧/40个螺母；旧DXF圆符号不再用于推断这套外露构造。内部石墨流道不展开。','AB/CD图纸200mm差异已按用户选择解决：保持设备位置，AB钢架随设备调整；见来源与差异。','该PDF为厂家条件图，本模型不是制造或施工放样模型。']}
    parameters['user_revision_decision']='删掉上下大环及20根外露杆和配套弹簧/螺母；其余构件、支架和安装变换保持'
    parameters['model_max_EL']=104.5+max(v[2] for q in geo.parts for v in q[2])/1000
    save(OUT/'设备/参数.json',parameters)
    placements=[]
    for suffix in 'ABCDEF':
        p=copy.deepcopy(old['C41B04'+suffix]);legacy=p.pop('layout_review',{})
        p['position_mm'][2]=4500
        if frame_policy=='move-equipment' and suffix in 'AB':p['position_mm'][1]+=200
        p.update(equipment_version=VERSION,local_datum='四向托耳底承托面Z0',z_status='有安装基准',z_basis='钢架梁顶EL104.500；托耳底Z0，端面距承托面下2612/上2200',orientation_status='PDF两顶口位于+Y一侧，与EL106顶视图对应；沿用原INSERT旋转/镜像')
        p['installation_review']={'before_position_mm':old[p['id']]['position_mm'],'bearing_EL':104.5,'bottom_end_EL':101.888,'top_end_EL':106.7,'legacy_layout_review':legacy,'position_policy':frame_policy}
        placements.append(p)
    save(OUT/'安装表.json',placements)
    # The 4275×1875×4500 frame topology stays sourced from the existing foundation.
    # Copy one source portal, keeping its GZ1/GL1/ZC1 display sections unchanged.
    source=script(REPO/'水解桥架工程/models/设备/设备基础_20261106/C41B04/model_data.js','MODEL_PARTS')
    single=[]
    for p in source:
        v=np.array(p['vertices'])
        if v[:,1].min()>3000:
            q=copy.deepcopy(p);q['vertices']=(v-[0,4200,0]).tolist();single.append(q)
    assert single and len(single)*3==len(source),(len(single),len(source))
    geo.parts[:]=[(p['name'],p['color'],p['vertices'],p['faces']) for p in single]
    frame_bounds=export(OUT/'支架/单组','C41B04-frame')
    # Preserve diagram group spacing by default until the conflict is resolved.
    center={pair:np.mean([p['position_mm'][:2] for p in placements if p['id'][-1] in pair],axis=0) for pair in ['AB','CD','EF']}
    group_records=[];preview_offsets=[];combined=[]
    for pair,dy in [('AB',4200),('CD',0),('EF',-3000)]:
        xy=center[pair].copy()
        if pair=='AB' and frame_policy=='pending':xy[1]=center['CD'][1]+4200
        group_records.append({'id':'FRAME-C41B04'+pair,'name':'偏钛酸冷却器'+pair+'组钢架','asset':'foundation-C41B04','position_mm':[round(float(xy[0]),4),round(float(xy[1]),4),0],'rotation_deg':0,'level':'EL100','support_for':['C41B04'+s for s in pair],'status':'AB组平面差异200mm待核' if pair=='AB' and frame_policy=='pending' else '按设备中心与钢架梁网就位'})
        shift=xy-center['CD']
        for p in single:
            q=copy.deepcopy(p);q['name']=pair+'_'+q['name'];q['vertices']=(np.array(q['vertices'])+[shift[0],shift[1],0]).tolist();combined.append(q)
        for s in pair:
            p=next(p for p in placements if p['id']=='C41B04'+s);preview_offsets.append([p['position_mm'][0]-center['CD'][0],p['position_mm'][1]-center['CD'][1],4500])
    geo.parts[:]=[(p['name'],p['color'],p['vertices'],p['faces']) for p in combined]
    combined_bounds=export(OUT/'支架','C41B04')
    frame_params={'version':VERSION,'name':'三组双机钢架','source_drawing':FOUND,'source_sha256':sha(REPO/FOUND),'unit':'mm','single_frame_axis_span_mm':[4275,1875],'bearing_height_mm':4500,'device_center_spacing_mm':2400,'source_group_spacing_mm':[4200,3000],'layout_group_spacing_mm':[3999.5189,2999.9812],'frame_policy':frame_policy,'sections':'GZ1/GL1/ZC1继续沿用原基础模型展示截面，未作无依据细化','single_frame_bounds_mm':frame_bounds,'combined_bounds_mm':combined_bounds}
    save(OUT/'支架/参数.json',frame_params);save(OUT/'支架/单组/参数.json',frame_params);save(OUT/'支架安装表.json',group_records)
    save(OUT/'来源与差异.json',{'revision':VERSION,'sources':{p:sha(REPO/p) for p in [PDF,FOUND,LAYOUT]},'accepted':['厂家总图H4812、托耳距上端2200、四托耳1875/2055、N1—N7管口表；图中240㎡与原台账230㎡差异单列','布置图6台中心及顶口朝向','基础图单组4275×1875、钢架顶4500、梁网与截面展示'],
        'replaced':['端面高度4812保持；02版删除01版的外露端环/杆/弹簧/配套螺母，撤销200mm弹簧包络','2只托耳改四向4只，底部2大口改5个DN50排净口','两处顶口Y-390改Y+390；取消无依据的中央顶口','旧4个相同侧口改N3/N4 DN300及N5/N6 DN32','6台逐台元数据1700×3600及面积240/230矛盾已整合，旧值在1.0保留'],
        'conflicts':[{'topic':'AB/CD组中心距','foundation_mm':4200,'layout_mm':3999.5189,'difference_mm':200.4811,'policy':frame_policy,'user_decision':'保留设备布置位置，AB组钢架随设备调整200mm','consequence':'按用户选择，以布置图设备中心定位三组钢架；保留基础图4200mm原值供追溯'}], 'limits':parameters['limits']})
    update_registry(parameters,placements,preview_offsets,combined_bounds,frame_policy)
    from publish_c41b04 import publish
    publish()
    print(json.dumps({'version':VERSION,'equipment_bounds':bounds,'ports':len(ports),'single_frame_parts':len(single),'frame_policy':frame_policy},ensure_ascii=False))

def update_registry(parameters,placements,offsets,frame_bounds,policy):
    catalog=json.loads((ROOT/'catalog.json').read_text());catalog['version']='2.0-revised-classes';byid={p['id']:p for p in placements}
    for row in catalog['models']:
        if row['id'] not in byid:continue
        p=byid[row['id']];files={'model':'版本/2.0/C41B04/设备/model_data.js','glb':'版本/2.0/C41B04/设备/C41B04.glb','obj':'版本/2.0/C41B04/设备/C41B04.obj','parameters':'parameters/'+p['id']+'.json','installation':'版本/2.0/C41B04/安装表.json'}
        row.update(w=1300,h=4812,depth=1300,spec='立式圆形块孔石墨换热器（A=240m2/台）',pos_el=104.5,level='EL100',plan_sheet='EL100',model_version=VERSION,model_spec='壳体Ø1300；换热块Ø1200；端面H4812；四托耳承托EL104.500',position_mm=p['position_mm'],rotation_deg=p['rotation_deg'],mirror_y=p['mirror_y'],current_files=files,position_basis='安装采用position_mm建筑轴网坐标，Z为托耳底EL104.500；x/y/cad_position_mm旧文字点仅保留追溯')
        param={**parameters,'id':p['id'],'group':'C41B04A-F','qty':6,'position_mm':p['position_mm'],'rotation_deg':p['rotation_deg'],'mirror_y':p['mirror_y'],'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/'+p['id']+'.json'}
        save(ROOT/'parameters'/str(p['id']+'.json'),param)
    save(ROOT/'catalog.json',catalog)
    project=json.loads((ROOT/'project.json').read_text());project['active_version']='2.0（C41B02、C41B04）'
    project['revisions']['C41B02']['status']='用户已接受外形及精度为基准；POS与绝对方位待核'
    project['revisions']['C41B04']={'version':VERSION,'equipment':'版本/2.0/C41B04/设备/model_data.js','foundation':'版本/2.0/C41B04/支架/model_data.js','foundation_single':'版本/2.0/C41B04/支架/单组/model_data.js','placements':'版本/2.0/C41B04/安装表.json','support_placements':'版本/2.0/C41B04/支架安装表.json','status':'本体/四托耳/接口修正；AB组200mm图纸差异待核' if policy=='pending' else '02版删除无充分依据的外露大环/杆/弹簧/螺母；设备位置和钢架保持'}
    revised=sum(row['id'][:6] in project['revisions'] for row in catalog['models'])
    project['counts'].update(completed_batches=len(project['revisions']),revised_items=revised,other_items_unchanged=99-revised)
    project['active_version']='2.0（'+'、'.join(project['revisions'])+'）'
    if len(project['revisions'])==2:project['next_class']='D41B01'
    save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';overrides=json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'))
    overrides['ledger']['C41B02A-E']['状态']='外形精度已确认 · 安装待核'
    overrides['equipment']['C41B04']={'dir':'版本/2.0/C41B04/设备/','bounds':parameters['bounds_mm']}
    old=json.loads((REPO/'水解桥架工程/models/设备/设备基础_20261106/基础索引.json').read_text())['assets']['C41B04']
    old.update(dir='版本/2.0/C41B04/支架/',stem='C41B04',bounds=frame_bounds,offsets=offsets,mount=[0,0,0],dimensions='3组双机钢架；单组柱轴距4275×1875，托耳承托EL104.500；本体端面H4812',note='AB/CD基础图4200、设备布置约4000，200差异待核。' if policy=='pending' else '按用户确认位置口径整合钢架，单组梁网不变。')
    overrides['foundations']['C41B04']=old
    overrides['ledger']['C41B04A-F']={'状态':'2.0整改 · AB钢架位置待核' if policy=='pending' else '2.0整改','建模口径或缺项':'02版按用户要求删除外露端环/杆及配套弹簧螺母；厂家条件图SS-XYK1200-240S(10)：Ø1200换热块/Ø1300壳体，端面H4812、四托耳；承托EL104.500；2顶口、5底口及4侧口分别建模。AB/CD钢架与布置相差200mm，已按用户选择保持设备位置、钢架随设备调整。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(overrides,ensure_ascii=False,separators=(',',':'))+';\n')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--frame-policy',choices=['pending','layout','move-equipment'],default='layout');main(parser.parse_args().frame_policy)
