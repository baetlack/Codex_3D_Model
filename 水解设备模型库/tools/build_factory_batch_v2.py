"""Continue the authorized equipment review using the newly supplied drawings.

Keep the confirmed earlier classes, civil meshes and assembly positions separate.
Dimensions written on drawings take precedence over differently scaled linework.
"""
from pathlib import Path
import copy,json,math,shutil,subprocess
import ezdxf
import numpy as np
from build_c41b04_v2 import geo,sha,save,ring,pipe,plate,export,BODY,STEEL
from check_assembly import script

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
BATCH=ROOT/'data/连续整改_20261120';VERSION='2.0-连续整改-01'
DRAWINGS=ROOT/'水解设备图纸';CIVIL=REPO/'水解桥架工程/models/设备/设备基础_20261106'
SHEET='水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf'
FOUND='水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
FILES={'C41B01':'热水预热槽(C41B01A-B)','C41B03':'稀碱预热槽(C41B03A-C)','F41B01':'偏钛酸缓冲槽(F4101A-B1～4)','F41B02':'钛液事故槽(F41B02)稀碱配置槽(F41B05)稀碱储槽(F41B06)','D41B02':'水解槽(D41B02A-E1～3)','L41B05':'水解蒸汽分汽缸(L41B05)'}
ALIASES={'F41B05':'F41B02','F41B06':'F41B02'}
CLASSES=['C41B01','C41B03','F41B01','F41B02','F41B05','F41B06','D41B02','L41B05']
PIPE_OD={25:32,32:38,50:57,65:76,80:89,100:108,150:159,200:219,250:273,300:325,350:377,400:426,500:530,600:630,700:720,800:820}
FLANGE_OD={25:115,32:140,50:165,65:185,80:200,100:220,150:285,200:340,250:395,300:445,350:505,400:565,500:670,600:780,700:895,800:1015}

def pin():
    p=BATCH/'本批保护基准.json'
    if p.exists():return json.loads(p.read_text())
    project=json.loads((ROOT/'project.json').read_text());prefixes=['厂房外观模型/','水解桥架工程/']+['水解设备模型库/版本/2.0/'+k+'/' for k in project['revisions']]
    names=subprocess.check_output(['git','ls-files','-z'],cwd=REPO).decode().split('\0')
    protected={n:sha(REPO/n) for n in names if n and not n.endswith('/校验报告.json') and any(n.startswith(a) for a in prefixes)}
    value={'baseline_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),'project':project,'catalog':json.loads((ROOT/'catalog.json').read_text()),'assembly':json.loads((REPO/'水解总装工程/assembly.json').read_text()),'protected_files':protected}
    save(p,value);return value

def mesh(path):
    d=json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'));return d if isinstance(d,list) else d['parts']

def common_tank_frame(baseline):
    """Keep the established type-model main drain pointing east.

    The plant drawing inserts are at 90 degrees; the existing type-model
    convention and its zero-degree assembly placement already include that
    convention. New factory geometry must be expressed in the same local basis.
    """
    doc=ezdxf.readfile(REPO/LAYOUT);records=[]
    for q in baseline['assembly']['equipment']:
        if q['asset'] not in ['F41B02','F41B05','F41B06']:continue
        root=doc.entitydb[q['source_insert']]
        assert root.dxf.name=='钛液事故槽' and abs(root.dxf.rotation-90)<1e-6
        records.append({'id':q['id'],'insert':root.dxf.handle,'block':root.dxf.name,'drawing_rotation_deg':root.dxf.rotation,'retained_model_rotation_deg':q['rotation_deg'],'retained_position_mm':q['position_mm']})
    old=baseline['assembly']['assets']['F41B02']['source'];p=next(p for p in mesh(REPO/old) if p['name']=='接口_东侧低位接管')
    v=np.asarray(p['vertices']);assert np.ptp(v[:,0])>np.ptp(v[:,1]) and v[:,0].min()>0
    proof={'source':LAYOUT,'source_sha256':sha(REPO/LAYOUT),'instances':records,'old_type_model':old,'old_type_sha256':sha(REPO/old),'retained_main_drain_axis':[1,0,0],'factory_main_drain_axis':[0,-1,0],'factory_to_type_rotation_deg':90,'basis':'布置图主低排口向东；保持原类型模型主低口轴系及原实例变换，将新总图南向主低口整体转为模型东向','pending':'次低口及人孔与旧布置图的相对方位仍有差异；保留新总图的相对布局，不单独挪孔以贴合旧图'}
    save(BATCH/'三槽方位依据.json',proof);return proof

def rotate_common_tank(ports,measurements,spec,limits):
    # Exact quarter-turn avoids a numerical skew in shared opposite faces.
    geo.parts[:]=[(n,c,[(-y,x,z) for x,y,z in v],f) for n,c,v,f in geo.parts]
    for p in ports:
        for field in ['face_center_mm','normal']:
            if field in p:
                x,y,z=p[field];p[field]=[-y,x,z]
    for q in measurements.values():
        if 'xy_mm' in q:
            x,y=q['xy_mm'];q['drawing_xy_mm']=[x,y];q['xy_mm']=[-y,x];q['factory_to_type_rotation_deg']=90
    spec['factory_to_type_rotation_deg']=90
    limits[:0]=['新总图局部南向主低口转换为既有类型模型东向，整体转90°；原单台XYZ/旋转不变，依据见三槽方位记录','次低口/人孔的新旧相对方位仍有差异，保持厂家相对布局，工艺最终方位待核；不单独旋转接口消除差异']

def add_mesh(parts,offset=(0,0,0),prefix=''):
    for q in parts:geo.add(prefix+q['name'],q['color'],(np.asarray(q['vertices'])+offset).tolist(),q['faces'])

def port(name,start,end,dn,flange=None,wall=6,outer_d=None,bore_d=None,flange_thickness=18):
    a=np.asarray(start,float);b=np.asarray(end,float);axis=(b-a)/np.linalg.norm(b-a);neck=b-axis*flange_thickness;ro=(outer_d or PIPE_OD[dn])/2;ri=bore_d/2 if bore_d else max(1,PIPE_OD[dn]/2-wall)
    pipe('接口_'+name+'接管',a,neck,ro,ri,BODY)
    pipe('接口_'+name+'法兰',neck,b,(flange or FLANGE_OD[dn])/2,ri)
    return {'id':name,'DN':dn,'face_center_mm':b.tolist(),'normal':axis.tolist(),'neck_OD_mm':ro*2,'flange_OD_mm':flange or FLANGE_OD[dn],'flange_thickness_mm':flange_thickness}

def top_port(name,xy,z,dn,height,flange=None,lower_dn=None,lower_flange=None):
    x,y=xy
    if lower_dn:
        middle=z+min(150,height*.55)
        port(name+'外套',(x,y,z-4),(x,y,middle),lower_dn,lower_flange)
        p=port(name+'内接管',(x,y,middle-3),(x,y,z+height),dn,flange)
        p['id']=name;p['outer_DN']=lower_dn;p['outside_flange_OD_mm']=lower_flange or FLANGE_OD[lower_dn]
        return p
    return port(name,(x,y,z-4),(x,y,z+height),dn,flange)

def manhole(name,xy,z,dn,height,cover_d,center_lid=False):
    p=top_port(name,xy,z,dn,height,cover_d)
    geo.cyl('盖面_'+name+'盖',z+height,z+height+8,cover_d/2,STEEL,72)
    if center_lid:
        # C41B01 h lid must share the neck/handle XY, not the vessel origin.
        label,color,vertices,faces=geo.parts[-1]
        geo.parts[-1]=(label,color,[(x+xy[0],y+xy[1],zz) for x,y,zz in vertices],faces)
    x,y=xy;geo.box('盖面_'+name+'提手',(x,y,z+height+29),(80,12,34),STEEL)
    return p

def side_manhole_lid(name,record,thickness=8):
    """Close the explicitly identified side manhole, with its drawn handle."""
    center=np.asarray(record['face_center_mm'],float);normal=np.asarray(record['normal'],float);u=np.cross(normal,[0,0,1]);u/=np.linalg.norm(u);v=np.cross(normal,u)
    geo.cyl('接口_'+name+'_人孔盖',0,thickness,record['flange_OD_mm']/2,STEEL,72)
    n,c,vertices,faces=geo.parts[-1];geo.parts[-1]=(n,c,[(center+u*x+v*y+normal*z).tolist() for x,y,z in vertices],faces)
    front=center+normal*thickness;outer=front+normal*30
    for side in [-1,1]:pipe('接口_'+name+'_提手支脚'+str(side),front+v*100*side,outer+v*100*side,6,4,STEEL)
    pipe('接口_'+name+'_提手',outer-v*100,outer+v*100,6,4,STEEL)
    record.update(closure='带盖侧人孔',cover_thickness_mm=thickness,handle_scope='图示提手按比例表达；未标细部不作制造尺寸')

def bottom_members(radius,height,count,step):
    for i in range(count):
        x=(i-(count-1)/2)*step;length=2*math.sqrt(max(radius*radius-x*x,0))
        geo.box('设备底型钢_'+str(i+1),(x,0,height/2),(10,length,height),STEEL)

def vent_elbow(x,y,z):
    pipe('接口_g直管',(x,y,z),(x,y,z+100),44.5,38.5,BODY)
    vertices=[];faces=[];segments=16;around=48
    for theta in np.linspace(0,math.pi/2,segments+1):
        center=np.array([x-100*(1-math.cos(theta)),y,z+100+100*math.sin(theta)])
        u=np.array([math.cos(theta),0,math.sin(theta)]);v=np.array([0,1,0])
        for radius in [44.5,38.5]:
            vertices.extend((center+radius*(u*math.cos(a)+v*math.sin(a))).tolist() for a in np.linspace(0,2*math.pi,around+1)[:-1])
    for j in range(segments):
        for i in range(around):
            a=j*around*2+i;b=j*around*2+(i+1)%around;c=a+around*2;d=b+around*2
            faces.extend([[a,b,d,c],[b+around,a+around,c+around,d+around]])
    for j in [0,segments]:
        offset=j*around*2
        for i in range(around):faces.append([offset+i,offset+(i+1)%around,offset+(i+1)%around+around,offset+i+around])
    geo.add('接口_g呼吸弯管',BODY,vertices,faces)
    pipe('接口_g开口短管',(x-100,y,z+200),(x-160,y,z+200),44.5,38.5,BODY)

def vessel(key,diameter,wall,height,bottom_d,bottom_t,cover_d,cover_t,base_height=0,mixer_h=0,bolts=0,pcd=0):
    if base_height:bottom_members(diameter/2,base_height,10 if key=='F41B01' else 6,500)
    geo.cyl('本体_底板',base_height,base_height+bottom_t,bottom_d/2,BODY,96)
    base=base_height+bottom_t;top=base+height
    ring('本体_钢壳',(0,0),base,top-cover_t,diameter/2+wall,diameter/2,BODY,96)
    # Genuine openings under the external necks. Bolt detail is confined to the
    # explicitly drawn ring, with no guessed bolts on the nozzles themselves.
    return top,{'nominal_inner_diameter_mm':diameter,'steel_outer_diameter_mm':diameter+2*wall,'nominal_body_height_mm':height,'body_base_mm':base,'cover_top_mm':top,'bottom_member_height_mm':base_height,'bottom_plate_diameter_mm':bottom_d,'bottom_plate_thickness_mm':bottom_t,'cover_diameter_mm':cover_d,'cover_thickness_mm':cover_t,'mixer_display_height_mm':mixer_h,'ring_bolt_count':bolts,'ring_bolt_PCD_mm':pcd}

def cover_and_mixer(top,spec,holes,mixer_h=0):
    r=spec['cover_diameter_mm']/2;outer=[(r*math.cos(a),r*math.sin(a)) for a in np.linspace(0,2*math.pi,97)[:-1]]
    if spec['ring_bolt_count']:
        for a in np.linspace(0,2*math.pi,spec['ring_bolt_count']+1)[:-1]:holes.append((spec['ring_bolt_PCD_mm']/2*math.cos(a),spec['ring_bolt_PCD_mm']/2*math.sin(a),9 if spec['ring_bolt_count']!=20 else 8))
    plate('盖面_开孔盖板',outer,holes,top-spec['cover_thickness_mm'],top,STEEL)
    if mixer_h:
        for name,color,v,f in geo.mixer_at(top,top+mixer_h):geo.add('搅拌_'+name,color,v,f)

def native_point(doc,h,c,scale=1):
    p=doc.entitydb[h].dxf.center;return [(p.x-c.x)*scale,(p.y-c.y)*scale]

def radial_face(doc,center,scale,guess,diameter):
    candidates=[]
    for e in doc.modelspace().query('LINE'):
        a,b=e.dxf.start,e.dxf.end;mid=(a+b)/2-center;xy=np.array([mid.x,mid.y])*scale;v=np.array([b.x-a.x,b.y-a.y])*scale;r=np.linalg.norm(xy);length=np.linalg.norm(v)
        if not (2900<r<3800 and abs(length-diameter)<max(5,diameter*.04)):continue
        if abs(np.dot(xy,v))>r*length*.06:continue
        angle=math.degrees(math.atan2(xy[1],xy[0]));error=abs((angle-guess+180)%360-180)
        if error<8:candidates.append((error,-r,e.dxf.handle,xy))
    if candidates:
        error,minus_r,h,xy=min(candidates,key=lambda q:q[:2]);return h,xy
    return None,None

def tanks(key,doc):
    geo.parts.clear();ports=[];holes=[];measurements={};limits=[]
    if key=='C41B01':
        top,spec=vessel(key,3500,10,4000,3580,12,3670,10,bolts=28,pcd=3606);c=doc.entitydb['28C52'].dxf.center
        rows=[('a','28D64',80,150,200,None),('b2/k2','28D0C',80,300,200,200),('b1/k1','28D23',65,300,185,200),('g','28D40',100,100,220,None),('m','28D4C',150,150,265,None),('e','28D58',80,100,200,None)]
        for name,h,dn,height,flange,lower in rows:
            xy=native_point(doc,h,c);holes.append((*xy,PIPE_OD[lower or dn]/2-6));ports.append(top_port(name,xy,top,dn,height,flange,lower,340 if lower else None));measurements[name]={'handle':h,'xy_mm':xy}
        xy=native_point(doc,'28CD4',c);holes.append((*xy,259));ports.append(manhole('h',xy,top,500,150,620,center_lid=True));measurements['h']={'handle':'28CD4','xy_mm':xy}
        for name,deg,dn,z,extension in [('d',-45,80,top-200,150),('f',-135,25,1112,200)]:
            a=math.radians(deg);v=np.array([math.cos(a),math.sin(a),0]);start=v*1740;end=v*(1760+extension);start[2]=end[2]=z;ports.append(port(name,start,end,dn))
        ports.append(port('c1',(0,-1748,136),(0,-1908,136),150,285,outer_d=219,bore_d=150))
        candidates=[]
        for e in doc.modelspace().query('LINE'):
            a,b=e.dxf.start,e.dxf.end;mid=(a+b)/2-c;v=b-a;distance=math.hypot(mid.x,mid.y)
            if 335<v.magnitude<345 and -1000<mid.x<-50 and mid.y<-1600 and 1800<distance<2100 and abs(mid.x*v.x+mid.y*v.y)<distance*v.magnitude*.03:candidates.append((distance,e.dxf.handle,mid))
        if not candidates:raise ValueError('C41B01 c2 flange face could not be identified')
        distance,h,mid=max(candidates);v=np.array([mid.x,mid.y,0])/distance;start=v*1748;end=v*distance;start[2]=end[2]=147;ports.append(port('c2',start,end,200,340));measurements['c2']={'handle':h,'flange_face_xy_mm':[mid.x,mid.y]}
        cover_and_mixer(top,spec,holes);limits+=['h侧视接管Ø530与平面内圈Ø490不同，外形采用侧视接管和俯视盖外廓；制造接口待详图','侧口d/f及c1/c2口高按总图标注，未标伸出与法兰厚为显示值']
        refs=['28FB8','291D0','291CD','28C4C','28C4F']
    elif key=='C41B03':
        top,spec=vessel(key,1500,6,2000,1550,6,1638,6,mixer_h=1350,bolts=20,pcd=1586);c=doc.entitydb['3FD3D'].dxf.center
        for name,h,dn,flange,height,lower in [('h','3FD81',80,200,150,None),('b','3FDCE',100,220,150,None),('a','3FDD1',100,220,150,None),('c','3FD82',50,165,300,150)]:
            xy=native_point(doc,h,c,8/15);holes.append((*xy,PIPE_OD[lower or dn]/2-6));ports.append(top_port(name,xy,top,dn,height,flange,lower,265 if lower else None));measurements[name]={'handle':h,'xy_mm':xy,'plan_scale':8/15}
        p=port('e',(740,0,506),(906,0,506),500,650);side_manhole_lid('e',p);ports.append(p);measurements['e盖']={'source_name_handle':'49B85','source_name':'人孔 DN500'}
        slant=150/math.sqrt(2);ports.append(port('d',(-740,0,490),(-756-slant,0,506+slant),50,165))
        ports.append(port('f',(0,740,56),(0,1006,56),50,165))
        cover_and_mixer(top,spec,holes,1350)
        limits+=['平面R600图形半径1125，采用8/15换算，不能直接按图形1:1取数','Ø1550/1586/1638为明确标注；对应图形1556/1590/1642差异保留','厂家题名碱液稀释槽，上传文件对应C41B03；设备适用性及侧口细部待确认','现有1350搅拌总高保持；内部盘管与未标附件不展开']
        refs=['45E19','45E40','3FC49','464F7','46C11']
    elif key=='F41B01':
        top,spec=vessel(key,5000,10,5900,5100,12,5220,12,150,2310,40,5140);c=doc.entitydb['2A224'].dxf.center
        for name,h,dn,height,flange,lower in [('a/n1','2AA11',200,300,340,250),('c/n2','2AA3F',150,300,285,200),('d','193A1',200,150,340,None),('e','1938E',200,150,340,None),('f','1A600',80,100,200,None)]:
            xy=native_point(doc,h,c);holes.append((*xy,PIPE_OD[lower or dn]/2-6));ports.append(top_port(name,xy,top,dn,height,flange,lower));measurements[name]={'handle':h,'xy_mm':xy}
        xy=native_point(doc,'2A945',c);holes.append((*xy,259));ports.append(manhole('h',xy,top,500,150,620));measurements['h']={'handle':'2A945','xy_mm':xy}
        ports.append(port('b',(2480,0,362),(2770,0,362),400,565))
        for name,deg,dn,z,end,flange in [('k',45,800,1062,2810,1000),('g',-135,65,862,2710,185)]:
            a=math.radians(deg);v=np.array([math.cos(a),math.sin(a),0]);a=v*2480;b=v*end;a[2]=z;b[2]=z-(100 if name=='g' else 0);p=port(name,a,b,dn,flange,flange_thickness=38 if name=='k' else 18)
            if name=='k':side_manhole_lid(name,p,38);measurements['k盖']={'source_name_handle':'31D2E','flange_source_handle':'31D2B','source_name':'人孔盖/法兰 δ＝38'}
            ports.append(p)
        cover_and_mixer(top,spec,holes,2310)
        limits+=['新总图增加150高底型钢；模型以型钢下表面Z0，底板与槽体上移，基础承托位置不动','型钢高度/500间距有图示；未标截面仅显示，不能用于结构承载','搅拌总高2310保持，内部叶轮与盘管不展开；m检视窗细部待核']
        refs=['1A79D','27045','274BD','2A386','2A3CE']
    else:
        top,spec=vessel(key,2800,8,2500,2900,8,2966,8,150,1560,34,2906);c=doc.entitydb['247E'].dxf.center
        for name,h,dn,height,flange,lower in [('a','5159',150,300,315,250),('c','516C',100,150,210,None),('d','5174',150,150,265,None),('e','5162',200,150,320,None),('f','5178',80,100,200,None)]:
            xy=native_point(doc,h,c);holes.append((*xy,PIPE_OD[lower or dn]/2-6));ports.append(top_port(name,xy,top,dn,height,flange,lower,375 if lower else None));measurements[name]={'handle':h,'xy_mm':xy}
        xy=native_point(doc,'512E',c);holes.append((*xy,259));ports.append(manhole('h1',xy,top,500,150,630));measurements['h1']={'handle':'512E','xy_mm':xy}
        # Breather g is explicitly shared with manhole h1 in the assembly.
        x,y=xy;vent_elbow(x,y,top+158);ports.append({'id':'g','DN':80,'face_center_mm':[x-160,y,top+358],'normal':[-1,0,0],'basis':'g/h1共座呼吸口；不补造出口法兰'})
        p=port('h2',(-1390,0,758),(-1558,0,758),700,1150);side_manhole_lid('h2',p);ports.append(p);measurements['h2盖']={'source_name_handle':'103A4','source_name':'侧壁人孔；盖件见10563'}
        for name,deg in [('b1',-90),('b2',-135)]:
            angle=math.radians(deg);v=np.array([math.cos(angle),math.sin(angle),0]);a=v*1390;middle=v*1608;b=v*1808;a[2]=middle[2]=b[2]=358;port(name+'外套',a,middle,250,375);ports.append(port(name,middle-v*3,b,150,315,outer_d=190,bore_d=150))
        cover_and_mixer(top,spec,holes,1560)
        limits+=['按共用文件外形用于F41B02/F41B05/F41B06，三台介质、材质和接口用途不互相复制确认','新增150高底型钢；裸罐高度2500，搅拌按90+720+750=1560外形口径，内部零件仍示意','h2外廓Ø1150按总图，DN700与护套/外廓分别记录；底双排口复合套管细部待核','g/h1共座明确；呼吸弯管曲率和法兰厚待详图，未补造出口法兰']
        refs=['FA85','FAB0','FDAE','10328','FB71','FB7B']
    return ports,spec,measurements,refs,limits

def hydrolysis(doc,baseline):
    old=mesh(REPO/baseline['assembly']['assets']['D41B02']['source']);geo.parts.clear()
    # Preserve the previously confirmed body, lid and 3076-high mixer exactly.
    add_mesh([p for p in old if not p['name'].startswith('接口_')]);ports=[];c=doc.entitydb['1121'].dxf.center;measurements={}
    rows=[('a','4AB',250,350,395,300),('b','4B9',150,350,285,250),('c','4B3',100,350,220,150),('e','4AC',250,200,375,None),('f1','130E',65,350,185,150),('f2','1306',65,350,185,150),('f3','1314',65,350,185,150),('g','429',600,300,760,None),('j','E26',150,100,285,200),('k','4BA',80,200,190,None),('l','4BE',80,200,190,None)]
    for name,h,dn,height,flange,lower in rows:
        xy=native_point(doc,h,c,20);ports.append(top_port(name,xy,5020,dn,height,flange,lower));measurements[name]={'handle':h,'xy_mm':xy,'plan_scale':20}
    for name,angle,dn,z,extension,flange in [('d',180,150,220,400,285),('h',135,65,700,200,185),('m1',245,200,1140,200,340),('m2',135,200,1140,200,340),('m3',6.5,200,1140,200,340),('n',45,300,220,200,445),('t',-45,600,480,240,720)]:
        h,xy=radial_face(doc,c,20,angle,flange)
        if xy is not None:
            v=np.array([*xy,0]);v/=np.linalg.norm(v);end=np.array([*xy,z]);measurements[name]={'handle':h,'flange_face_xy_mm':xy.tolist(),'plan_scale':20}
        else:
            a=math.radians(angle);v=np.array([math.cos(a),math.sin(a),0]);end=v*(2950+extension);end[2]=z;measurements[name]={'angle_display_deg':angle,'status':'图面分布示意，未获得唯一法兰面线段'}
        start=v*2930;start[2]=z
        if name=='h':
            # The temperature branch is explicitly drawn at 45 degrees.
            end=v*(2950+extension/math.sqrt(2));end[2]=z+extension/math.sqrt(2);start[2]=z-20
        p=port(name,start,end,dn,flange)
        if name=='t':side_manhole_lid(name,p);measurements['t盖']={'source_name_handle':'26F8','source_name':'常压人孔 DN600'}
        ports.append(p)
    spec={'confirmed_body_diameter_mm':5900,'confirmed_body_height_mm':4700,'confirmed_mixer_top_mm':7776,'confirmed_mixer_total_height_mm':3076,'retained_cover_top_mm':5020,'new_drawing_cover_datum_pending':True}
    limits=['已确认Tank_shell、Tank_flat_bottom、Tank_cover_lid及搅拌顶点/面/颜色保持；只替换/补外部接口','新图11个顶口按1:20几何换算平面，图形通径/衬套与名义DN分开','原盖面320高差与新总图口高基准未闭合；顶口暂从现有盖面5020表达，不宣称已核实绝对口高','原模型Ø5900及3076总高保留；新图钢壳Ø5924、盖面及2866分段需与已确认口径核对','侧口角度由图面分布作局部示意；m1/m2/m3和工艺绝对方位须现场/工艺图核实，不能据此施工']
    return ports,spec,measurements,[],limits

def separator():
    geo.parts.clear();ports=[]
    pipe('本体_卧式筒体',(-1900,0,700),(1900,0,700),500,484,BODY)
    for sign in [-1,1]:
        angles=np.linspace(0,math.pi/2,19)[:-1];vertices=[(sign*(1900+275*math.sin(a)),500*math.cos(a)*math.cos(t),700+500*math.cos(a)*math.sin(t)) for a in angles for t in np.linspace(0,2*math.pi,73)[:-1]]
        faces=[[j*72+i,j*72+(i+1)%72,(j+1)*72+(i+1)%72,(j+1)*72+i] for j in range(len(angles)-1) for i in range(72)]
        end=len(vertices);vertices.append((sign*2175,0,700));faces += [[(len(angles)-1)*72+i,(len(angles)-1)*72+(i+1)%72,end] for i in range(72)];faces.append(list(reversed(range(72))))
        if sign<0:faces=[list(reversed(f)) for f in faces]
        geo.add('本体_椭圆封头'+str(sign),BODY,vertices,faces)
    for name,x,dn,flange in [('a',-1500,350,520),('b',-900,100,340),('c1',-550,25,115),('c2',-250,25,115),('d1',0,25,115),('d2',300,25,115),('e',700,150,285),('f',1100,200,340),('g',1600,350,520)]:ports.append(port(name,(x,0,1180),(x,0,1400),dn,flange))
    for name,x,dn in [('h',0,100),('j',1500,32)]:ports.append(port(name,(x,0,220),(x,0,0),dn))
    for i,x in enumerate([-1000,1000],1):
        geo.box('支承_鞍座'+str(i)+'底板',(x,0,10),(300,800,20),STEEL)
        # Profile follows the bottom of the Ø1000 cylinder; its upper edge is
        # circular rather than a block passing through the pressure shell.
        outer=np.asarray(geo.parts[0][2][:64]);lower=outer[outer[:,2]<=700+1e-7][:,[1,2]];lower=lower[np.argsort(lower[:,0])]
        ys=sorted(set([-400.,400.]+[float(y) for y,z in lower if -400<y<400]));profile=[(-400,20),(400,20)]+[(y,float(np.interp(y,lower[:,0],lower[:,1]))) for y in ys[::-1]]
        plate('支承_鞍座'+str(i)+'腹板',profile,[],x-10,x+10,STEEL)
        n,c,v,f=geo.parts[-1];geo.parts[-1]=(n,c,[(w,u,vv) for u,vv,w in v],f)
    spec={'body_outer_diameter_mm':1000,'straight_length_mm':3800,'head_depth_mm':275,'overall_body_length_mm':4350,'axis_height_mm':700,'saddle_center_distance_mm':2000,'top_nozzles':9,'bottom_nozzles':2,'nozzle_extension_mm':200,'display_wall_mm':16}
    limits=['DN与外径不是同一量；未给钢管系列/壁厚时按常见外形显示，法兰厚暂18','b表中DN100、俯视内圈约Ø200不一致；采用表中DN100，俯视外廓Ø340保留待核','a与g同为DN350；a俯视未完整表达，按侧视位置/管口表补齐，最终厂家总图待确认','条件图未给鞍座宽/厚，300×800底板及20厚腹板为显示值；鞍座中心距2000与轴高700有图示','原基础仅单墩详图，不能自动认定为完整两鞍座基础；绝对定位、支承数量/方向/标高继续待核','本类仍待定位，不加入厂房总装']
    return ports,spec,{},[],limits

def publish_class(key,params):
    out=ROOT/'版本/2.0'/key
    import html
    lines=[f'{params["name"]} {key} · {params["version"]}',params['scope']]+params['limits']
    (out/'整改说明.md').write_text('\n\n'.join(lines)+'\n')
    style='body{max-width:1080px;margin:30px auto;padding:20px;background:#101923;color:#dce8ef;font:15px/1.8 sans-serif}a{color:#7cdce6}img{max-width:100%}'
    text=''.join('<p>'+html.escape(s)+'</p>' for s in lines)
    (out/'整改说明.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+key+'整改说明</title><style>'+style+'</style><h1>'+html.escape(params['name'])+'</h1><p><a href="index.html">模型</a> · <a href="来源量测.json">量测与句柄</a> · <a href="安装表.json">安装表</a> · <a href="支承复核.json">支承/空间复核</a> · <a href="../../1.0/index.html">1.0保留版</a></p>'+text+'<p>来源完整图纸见设备库详情下载。</p><img src="来源_总图.png" alt="新增原图">')
    (out/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+key+'设备2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>'+html.escape(params['name'])+' · <a href="整改说明.html">来源与待核</a> · <a href="../../1.0/index.html">1.0</a></header><iframe src="../../../index.html?type='+key+'"></iframe></html>')

def review_remaining(baseline,project,catalog,overrides):
    """Record actual limits for every remaining class without relabeling it fixed."""
    import html
    reviews={};issues=[]
    for key in sorted({q['id'][:6] for q in catalog['models']}-set(project['revisions'])):
        rows=[q for q in catalog['models'] if q['id'][:6]==key];name=rows[0]['name'];out=ROOT/'版本/2.0'/key;out.mkdir(parents=True,exist_ok=True)
        asset=baseline['assembly']['assets'].get(key);model=asset['source'] if asset else None
        oldparam=ROOT/f'版本/1.0/快照/水解设备模型库/parameters/{key}.json';legacy=json.loads(oldparam.read_text()) if oldparam.exists() else {}
        if key=='L41B04':
            action='保留现有减温减压器外形；平面外廓有依据，立面与安装支座待核'
            pending=['原示图2F6D平面5250×639可追溯，未取得完整厂家立面/安装图','主管中心高、支座底面与MJ-b预埋板/3300中心距未闭合','原XYZ、90°旋转和原基础保持，不能把暂用EL112认定为已确认承托高']
        elif key=='F41B07':
            action='保留已按图建立的两座地坑；净空1500×1500×2000继续作为口径'
            pending=['原俯视3564内框1500、外框1700；底厚100为显示值','坑口Z0、向下2000；地坑顶口与建筑地坪开口界面需配合，未改建筑','排水、爬梯、盖板及立式泵入坑深度无详图，不补造']
        elif key=='F41B08':
            action='保留用户确认的Ø1000×1000一体圆柱'
            pending=['不因其他槽罐更新而增设搅拌、接口或支腿','仅有台账/俯视353F，真实进出水口和安装详图待补']
        elif key.startswith('V'):
            action='保留葫芦示意模型；吨位/起升高度仅作为台账参数'
            pending=['共用侧视27CA不能确认所有1t/2t/5t型号外形','旧0.9/1/1.2外形比例仅显示；额定吨位不构成线性缩放或结构设计依据','起升高度是行程，不当作设备本体高度','吊点、轨道梁、运行方向和挂装标高缺依据，未定位设备继续不入总装']
        elif key in ['P41B07','P41B09']:
            action='暂留现有泵示意，立式外形尚未整改通过'
            pending=['台账为立式泵/立式管道泵，现有卧式比例外形不符合已知型式，应替换厂家立式模型','现有平面安装符号不能推导真实总高、电机外形或入坑深度','不凭流量扬程推造设备尺寸；原位置/基础暂留，外形标记待厂家图']
        elif key=='P41B04':
            action='暂留管道泵示意；卧式/立式型式与安装外形待厂家图'
            pending=['Q120/H40及管道泵台账不足以确定卧式/立式和本体尺寸','平面459.81×300为安装符号，现高度360仅比例显示','主管中心高、进出口方向和支座待核；原基础与位置不移动']
        elif key=='P41B10':
            action='保留风机蜗壳、轴向入口、切向出口及本体底座'
            pending=['Q40000/ΔP3000是工况，不能据此确定厂家外廓','蜗壳和电机底座按原图示意；本体支脚不能当作土建基础删除','厂家安装尺寸、锚固孔/底座与基础标高待核']
        else:
            action='保留可追溯的卧式泵示意，厂家安装尺寸待补'
            pending=['现外廓采用布置俯视，竖向高度/电机细节为比例值，不是厂家制造模型','流量扬程不能代替轴高、底脚和进口/出口尺寸','单台旋转/镜像与原安装点保持；缺设备图时不挪动基础或复制邻机支座']
            if key=='P41A08':pending.append('沿用P41B08型式仅作显示，不据此确认跨工段两台设备型号相同')
            if key=='P41B11':pending.append('原图P41B11独立俯视不足，不能把共用泵图当作已确认本机外形')
        placed=[q for q in baseline['assembly']['equipment'] if q['asset']==key];unplaced=[q for q in baseline['assembly']['unplaced'] if q['id'][:6]==key]
        params={'id':key,'name':name,'version':'2.0-'+key+'-复核01','action':action,'geometry_action':'retained','status':'reviewed-with-open-items','unit_tags':[q['id'] for q in rows],'active_model_source':model,'active_model_sha256':sha(REPO/model) if model else None,'legacy_model_basis':legacy.get('height_basis','原档案及示图；未取得厂家立面尺寸'),'sources':{p:sha(REPO/p) for p in [SHEET,FOUND,LAYOUT,LEDGER]},'installation':{'placed':placed,'unplaced':unplaced,'position_action':'unchanged'},'pending':pending}
        save(out/'复核记录.json',params);save(out/'安装表_原样记录.json',placed)
        text='\n\n'.join([f'{key} {name} · 首轮复核',action,'本轮不改原模型、基础或安装点。1.0及原始资料保留。']+pending)+'\n';(out/'整改说明.md').write_text(text)
        body=''.join('<p>'+html.escape(q)+'</p>' for q in text.split('\n\n'));style='body{max-width:1050px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px/1.8 sans-serif}a{color:#7cdce6}'
        (out/'整改说明.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+key+'复核记录</title><style>'+style+'</style><h1>'+html.escape(name)+'</h1><p><a href="index.html">原模型</a> · <a href="复核记录.json">证据与待核</a> · <a href="../../1.0/index.html">冻结1.0</a></p>'+body)
        (out/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+key+'复核保留</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>'+html.escape(name)+' · 本轮保留原几何 · <a href="整改说明.html">复核与未决项</a></header><iframe src="../../../index.html?type='+key+'"></iframe></html>')
        reviews[key]={'version':params['version'],'status':action,'record':f'版本/2.0/{key}/复核记录.json','geometry_changed':False}
        overrides.setdefault('review_info',{})[key]={'action':action,'pending':pending,'url':f'版本/2.0/{key}/整改说明.html','geometry':'本轮保留原几何'}
        overrides['ledger'][key]={'状态':'首轮复核 · 原示意保留/待核','建模口径或缺项':action+'；'+pending[0]}
        issues.append({'class':key,'name':name,'units':[q['id'] for q in rows],'action':action,'pending':pending})
    project['reviews']=reviews;project['counts'].update(reviewed_batches=len(project['revisions'])+len(reviews),reviewed_items=99,unreviewed_items=0)
    save(BATCH/'保留与待核.json',issues)
    return reviews

def build():
    if json.loads((ROOT/'project.json').read_text()).get('review_workflow',{}).get('mode')=='逐类确认':
        raise SystemExit('当前逐类确认模式：使用各类专用生成器，禁止旧批量构建覆盖已修正模型。')
    baseline=pin();frame_proof=common_tank_frame(baseline);project=json.loads((ROOT/'project.json').read_text());catalog=json.loads((ROOT/'catalog.json').read_text());overrides=script(ROOT/'equipment_versions.js','EQUIPMENT_VERSION_OVERRIDES');civil_index=json.loads((CIVIL/'基础索引.json').read_text());docs={};results={};civil_overrides={}
    for key in CLASSES:
        family=ALIASES.get(key,key);source=DRAWINGS/(FILES[family]+'.dxf')
        if family not in docs:docs[family]=ezdxf.readfile(source)
        doc=docs[family];out=ROOT/'版本/2.0'/key;out.mkdir(parents=True,exist_ok=True)
        if family=='D41B02':ports,spec,measured,refs,limits=hydrolysis(doc,baseline)
        elif family=='L41B05':ports,spec,measured,refs,limits=separator()
        else:ports,spec,measured,refs,limits=tanks(family,doc)
        if family=='F41B02':
            rotate_common_tank(ports,measured,spec,limits);save(out/'三槽方位依据.json',frame_proof)
        bounds=export(out/'设备',key);version='2.0-'+key+'-01';rows=[q for q in catalog['models'] if q['id'][:6]==key];name=rows[0]['name']
        dimensions={h:{k:(list(v) if hasattr(v,'x') else v) for k,v in doc.entitydb[h].dxfattribs().items() if k in ['actual_measurement','text','defpoint2','defpoint3']} for h in refs}
        source_relative=source.relative_to(REPO).as_posix();save(out/'来源量测.json',{'source':source_relative,'sha256':sha(source),'dimension_entities':dimensions,'plan_points':measured,'specification':spec,'port_table':ports,'scale_note':'以明确标注值优先；平面与侧视可能不同图形比例；未标尺寸保持显示假设'})
        params={'id':key,'group':key,'name':name,'version':version,'units':'mm','source_drawing':source_relative,'source_sha256':sha(source),'scope':'外部本体/接口、基础配合与安装复核；不展开内部工艺构造','dimensions_mm':spec,'bounds_mm':bounds,'ports':ports,'datum':'设备最低承托面Z0；D41B02沿用确认档案Z0；安装表保持原XYZ/旋转','limits':limits+['未标盖板厚、法兰厚和管外径系列为显示值；不得据此制造','各单台设备的工艺绝对方位待核；不凭文字插点新增位置','原始图纸、1.0、先前八类、建筑/桥架及原土建几何保持'],'detail_level':'采用已接受的C41B02工程展示风格；无依据细部不作制造确认'}
        save(out/'设备/参数.json',params)
        # No new instance is introduced. The existing bearing datum remains in
        # place while the equipment geometry gains its drawing-based bottom frame.
        placements=[]
        for old in baseline['assembly']['equipment']:
            if old['asset']!=key:continue
            q=copy.deepcopy(old);q.update(equipment_version=version,orientation_status='新接口按局部总图表达；沿用原旋转，绝对工艺方位待核',local_datum=params['datum'],installation_review={'before_position_mm':old['position_mm'],'reason':'原XYZ/旋转保持；新增本体以底部承托面为原点，型钢/底板及未决口高见本类参数','source_drawing':source_relative})
            q['model_origin']='最低承托面Z0；本类图纸口径和未决差异见设备参数'
            placements.append(q)
        save(out/'安装表.json',placements)
        files={'model':f'版本/2.0/{key}/设备/model_data.js','glb':f'版本/2.0/{key}/设备/{key}.glb','obj':f'版本/2.0/{key}/设备/{key}.obj','parameters':f'parameters/{key}.json','installation':f'版本/2.0/{key}/安装表.json'}
        for row in rows:row.update(model_version=version,current_files=files,model_spec='新增图纸外部本体/接口复核；单台安装/工艺方位待核')
        save(ROOT/f'parameters/{key}.json',{**params,'qty':len(rows),'current_files':files})
        rev={'version':version,'equipment':files['model'],'placements':files['installation'],'support_review':f'版本/2.0/{key}/支承复核.json','orientation_review':'new-factory-layout-pending','status':'新增总图修正外部本体/接口；原基础/位置保持，未决差异单列'}
        foundation_ids=civil_index.get('tags',{}).get(key,[])
        if not foundation_ids:
            foundation_ids=[k for k,v in civil_index['assets'].items() if key in v.get('tags',[])]
        for fid in foundation_ids:
            src=CIVIL/fid;dest=out/'基础'/fid;dest.mkdir(parents=True,exist_ok=True)
            for p in src.iterdir():
                if p.suffix in ['.js','.obj','.glb','.mtl']:shutil.copy2(p,dest/p.name)
            cp=json.loads((src/'参数.json').read_text());cp.update(source_drawing=FOUND,geometry_status='原土建/钢支架几何保持；本类仅校核配合');save(dest/'参数.json',cp)
            if fid==key:rev['foundation']=str((dest/'model_data.js').relative_to(ROOT))
            if fid not in civil_overrides:
                co=copy.deepcopy(civil_index['assets'][fid]);co.update(dir=dest.relative_to(ROOT).as_posix()+'/',combined_label='设备与基础（配合待核）',note='原基础几何保持；本类配合与安装限制见支承复核。');civil_overrides[fid]=co
        save(out/'支承复核.json',{'version':version,'status':'pending-check','original_placements':'unchanged','new_assembly_instances':0,'civil_assets':foundation_ids,'limits':params['limits']})
        project['revisions'][key]=rev;overrides['equipment'][key]={'dir':f'版本/2.0/{key}/设备/','bounds':bounds,'default_equipment_only':True};overrides['ledger'][key]={'状态':'2.0新增图纸整改 · 配合/方位待核','建模口径或缺项':'按新增图纸修正外部本体/接口，原基础及位置保持；原始图纸的未决差异见本类说明。'}
        overrides.setdefault('review_info',{})[key]={'action':'新增图纸外部本体/接口已更新；原基础及单台位置保持','pending':params['limits'][:2],'url':f'版本/2.0/{key}/整改说明.html','geometry':'本轮更新外部模型'}
        publish_class(key,params);results[key]={'version':version,'source':source_relative,'parts':len(geo.parts),'bounds_mm':bounds,'placed_instances':len(placements),'foundation_ids':foundation_ids}
    review_remaining(baseline,project,catalog,overrides)
    save(ROOT/'catalog.json',catalog);project['active_version']='2.0（首轮35类99项已覆盖，未决项保留）';project['next_class']=None;count=sum(q['id'][:6] in project['revisions'] for q in catalog['models']);project['counts'].update(completed_batches=len(project['revisions']),revised_items=count,other_items_unchanged=99-count);save(ROOT/'project.json',project)
    overrides['version']=VERSION;overrides['foundations'].update(civil_overrides);(ROOT/'equipment_versions.js').write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(overrides,ensure_ascii=False,separators=(',',':'))+';\n')
    progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=VERSION,revised_items=count,unchanged_items=99-count,next_class=project['next_class'])
    for row in progress['rows']:
        key=row['位号组'][:6]
        if key in results:row.update(本批状态='新增图纸本体/接口修正；位置/原土建保持；未决差异另列',本批依据=results[key]['source'])
        elif key in project['reviews']:row.update(本批状态=project['reviews'][key]['status'],本批依据=project['reviews'][key]['record'])
    progress.update(reviewed_groups=35,reviewed_items=99,unreviewed_items=0)
    save(ROOT/'data/设备整改进度.json',progress);save(BATCH/'本批结果.json',results)
    from publish_equipment_index import publish
    publish()
    from publish_factory_batch_v2 import publish as publish_review
    publish_review();print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':build()
