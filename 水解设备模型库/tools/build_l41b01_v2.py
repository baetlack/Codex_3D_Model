"""L41B01: exterior of LMBLJC2001-03L4103-1, without invented civil supports.

Coordinates are true mm in the main views. Local Z0 is the bottom discharge
sealing face; the three ear bearing undersides are Z650. Legacy Z stays provisional.
"""
from pathlib import Path
import copy,json,math,sys
import ezdxf,numpy as np
from build_c41b04_v2 import geo,sha,save,move_last,cylinder,ring,plate,pipe,export,BODY,STEEL,DARK
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/L41B01'
VERSION='2.0-L41B01-01';SOURCE='水解设备模型库/水解设备图纸/水解过滤器.dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
LEDGER='水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls'
CX=133799.3865309714;CY=-47947.96058936445

def sector(name,r0,r1,z0,z1,angle,half,color):
    count=12;ts=np.linspace(angle-half,angle+half,count+1);v=[]
    for z,r in [(z0,r1),(z1,r1),(z0,r0),(z1,r0)]:v.extend((r*math.cos(t),r*math.sin(t),z) for t in ts)
    n=len(ts);f=[]
    for i in range(n-1):
        j=i+1;f.extend([[i,j,n+j,n+i],[2*n+j,2*n+i,3*n+i,3*n+j],[n+i,n+j,3*n+j,3*n+i],[j,i,2*n+i,2*n+j]])
    f.extend([[0,n,3*n,2*n],[n-1,3*n-1,4*n-1,2*n-1]])
    geo.add(name,color,v,f)

def build_equipment(drawing):
    geo.parts.clear();ports=[]
    # The 1200 nominal value is the shell ID, not its outside diameter.
    geo.ring('本体_下筒体ID1200_OD1216',446.1115,950,608,600,BODY,96)
    geo.hollow_frustum('本体_锥斗',96.1115,446.1115,162.5,608,8,BODY,96)
    geo.ring('本体_上筒体ID1200_OD1216',988,1438,608,600,BODY,96)
    for label,z in [('下',924),('上',984)]:ring('连接_'+label+'筒体法兰OD1375',(0,0),z,z+30,687.5,600)
    for label,z in [('下',954),('上',979)]:ring('连接_'+label+'垫片t5',(0,0),z,z+5,687.5,607,DARK)
    ring('连接_PP筛板外露边缘t20',(0,0),959,979,687.5,600,BODY)
    # Explicit 24 M20×130 fasteners in the drawing. No long external tie cage.
    for i,a in enumerate(np.linspace(0,2*math.pi,25)[:-1]+math.radians(7.5),1):
        xy=(660*math.cos(a),660*math.sin(a))
        cylinder(f'紧固_M20_{i:02}_螺杆',xy,922,1052,10,DARK,16)
        cylinder(f'紧固_M20_{i:02}_螺栓头',xy,908,922,18,DARK,6)
        ring(f'紧固_M20_{i:02}_下垫圈',xy,922,924,20,10.5)
        ring(f'紧固_M20_{i:02}_上垫圈',xy,1014,1016,20,10.5)
        cylinder(f'紧固_M20_{i:02}_螺母',xy,1016,1032,18,DARK,6)
    points={}
    for key,handle in [('d','17295B'),('e','172956')]:
        e=drawing.entitydb[handle];points[key]={'handle':handle,'xy_mm':[e.dxf.center.x-CX,e.dxf.center.y-CY]}
    outer=[(628*math.cos(t),628*math.sin(t)) for t in np.linspace(0,2*math.pi,97)[:-1]]
    plate('顶盖_平盖OD1256_t8',outer,[(*p['xy_mm'],28.5) for p in points.values()],1438,1446,BODY)
    # These two long plates are lid stiffeners, not lifting eyes or handrails.
    for sign in [-1,1]:
        polygon=[(sign*250,-576.0937),(sign*255,-573.8981),(sign*255,573.8981),(sign*250,576.0937)]
        if sign<0:polygon.reverse()
        plate('顶盖_立筋'+str(sign),polygon,[],1446,1496)
    for key in ['d','e']:
        xy=points[key]['xy_mm'];ring(f'接口_{key}_接管',xy,1446,1548,28.5,25)
        ring(f'接口_顶盖法兰_{key}',xy,1548,1566,82.5,25)
        ports.append({'id':key,'dn':50,'center_mm':[*xy,1566],'normal':[0,0,1],'role':'清洗口' if key=='d' else '呼吸口','projection_mm':120,'flange_OD_mm':165,'basis':'管口表120；主俯视400、±200及Ø165圆；主视Ø57×3.5'})
    # Off-centre feed: new drawing Y445.5, not the old schematic Y500.
    # Extend to the real cylinder intersection, rather than leaving a floating stub.
    y=445.5
    pipe('接口_a_进料接管',(-722,y,700),(0,y,700),162.5,154.5)
    pipe('接口_a_连接法兰',(-747,y,700),(-722,y,700),222.5,154.5)
    pipe('接口_a_密封面',(-750,y,700),(-747,y,700),187.5,154.5)
    pipe('接口_a_瓷衬口',(-750,y,700),(0,y,700),145,125,BODY)
    ports.append({'id':'a','dn':300,'ceramic_bore_mm':250,'center_mm':[-750,y,700],'normal':[-1,0,0],'role':'进料口','flange_OD_mm':445,'basis':'主视距锥斗起点250；俯视X-750、Ø250/Ø290瓷衬同心于Y445.5；不把立筋间距500当作侧口偏心'})
    pipe('接口_b_出料接管',(0,-600,1238),(0,-730,1238),162.5,146.5)
    pipe('接口_b_连接法兰',(0,-730,1238),(0,-755,1238),222.5,146.5)
    pipe('接口_b_密封面',(0,-755,1238),(0,-758,1238),187.5,146.5)
    ports.append({'id':'b','dn':300,'center_mm':[0,-758,1238],'normal':[0,-1,0],'role':'出料口','projection_mm':150,'flange_OD_mm':445,'basis':'管口表伸出150；主视距顶盖下表面200；俯视南侧中心'})
    ring('接口_c_排渣接管',(0,0),28,96.1115,162.5,146.5)
    ring('接口_c_连接法兰',(0,0),3,28,222.5,146.5)
    ring('接口_c_密封面',(0,0),0,3,187.5,146.5)
    ports.append({'id':'c','dn':300,'center_mm':[0,0,0],'normal':[0,0,-1],'role':'排渣口','projection_mm':100,'flange_OD_mm':445,'bolt_circle_mm':400,'bore_mm':293,'basis':'主剖面锥斗350、口颈100、Ø325×8、Ø293；Ø400是螺栓圆，非外法兰直径'})
    for i,degrees in enumerate([60,180,300],1):
        a=math.radians(degrees);sector(f'托耳_R{i}_贴体补强板',608,616,630,880,a,math.radians(9.34260863),STEEL)
        plate(f'托耳_R{i}_承托底板',[(616,-80),(741,-80),(741,80),(616,80)],[(691,0,15)],650,660,angle=a)
        for side in [-1,1]:
            polygon=[(616,660),(741,660),(741,690),(646,850),(616,850)]
            v=[(x,y,z) for y in [side*58-3,side*58+3] for x,z in polygon];n=len(polygon)
            f=[list(reversed(range(n))),list(range(n,2*n))]+[[j,(j+1)%n,(j+1)%n+n,j+n] for j in range(n)]
            geo.add(f'托耳_R{i}_筋板{side}',STEEL,v,f);move_last(angle=a)
    return ports,points

def main():
    pinned=json.loads((OUT/'本批保护基准.json').read_text());drawing=ezdxf.readfile(REPO/SOURCE)
    ports,points=build_equipment(drawing);bounds=export(OUT/'设备','L41B01')
    params={'version':VERSION,'name':'水解过滤器','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'drawing_number':'LMBLJC2001-03L4103-1','drawing_stage':'施工图总图，第1张/共4张','cad_units_per_mm':1,
        'applicability':'2026.5.21台账水解页103行复用图号LMBLJC2001-03L4103，与本次总图一致；图示与台账均6台',
        'dimensions_mm':{'shell_ID':1200,'shell_OD':1216,'shell_wall':8,'lower_straight_shell':500,'upper_straight_shell':450,'cone_axial_height':350,'bottom_nozzle_nominal_extension':100,'top_plate_OD':1256,'top_plate_thickness':8,'main_flange_OD_drawn':1375,'main_flange_bolt_circle':1320,'main_flange_bolts':24,'main_flange_bolt_spec':'M20×130','screen_edge_thickness':20,'gasket_thickness_each':5,'body_face_to_lid_top_approx':1446,'top_nozzle_extension':120,'overall_envelope':1566,'ear_count':3,'ear_bearing_z':650,'ear_angles_deg':[60,180,300],'ear_hole_circle':1382,'ear_hole_diameter':30,'ear_plate_radial_tangent_thickness':[125,160,10]},
        'ledger_spec':'Ø1200,H1220；台账名义H与总图约1446分开保留，不以旧高度压缩新图',
        'datum':'底部c口密封端面Z0；下筒锥斗起点Z450；三耳底Z650；平盖顶Z1446；d/e口顶Z1566',
        'ports':ports,'top_plan_source_points':points,'bounds_mm':bounds,
        'support_status':'新图三耳悬挂支承；未取得承托梁/支墩与承托EL，暂不新建；旧Ø1300×200圆台仅保留1.0，不与新本体组合',
        'user_decision':'承托EL暂不明确；保留现有位置作待核展示，旧圆台留1.0、不与新本体组合',
        'limits':['本体/接口/三耳按适用总图；未提供-2/-3/-4制造详图，局部法兰/螺栓外廓及耳板未标细节按CAD图面展示。','主连接法兰外廓按图面Ø1375；Ø1320为主连接螺栓圆，Ø1382为三耳孔圆，底口Ø400为该口螺栓圆，均不混作筒径或法兰外径。','仅表现外露PP筛板边缘、垫片、加强筋，不展开内部筛孔、衬砖/衬胶施工层与隐藏流道。','总图注明按工艺专业管口方位图；按布置INSERT保留平面方向/镜像，但新接口绝对方位仍待核。','6台X/Y及原暂用Z保持；A/C/E纠正原INSERT负比例镜像遗漏。原Z无可靠承托依据，以底口端面作当前暂用原点，不能作为安装验收。','不造承托梁、支墩、地脚连接或检修空间；支承图/承托标高提供后再闭合安装链。']}
    save(OUT/'设备/参数.json',params)
    layout=ezdxf.readfile(REPO/LAYOUT);installs=[]
    for old in pinned['equipment_placements']:
        if old['asset']!='L41B01':continue
        p=copy.deepcopy(old);legacy=p.pop('layout_review',{});e=layout.entitydb[p['source_insert']]
        a=math.radians(e.dxf.rotation);matrix=np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])@np.diag([e.dxf.xscale,e.dxf.yscale])
        yaw=math.degrees(math.atan2(matrix[1,0],matrix[0,0]))%360
        p.update(rotation_deg=round(yaw,5)%360,mirror_y=bool(np.linalg.det(matrix)<0),equipment_version=VERSION,local_datum='底部c口密封端面Z0；托耳底Z650',z_status='待核',z_basis='按用户选择保留原暂用Z，以c口端面为当前模型原点；三耳承托EL=原暂用EL+0.650，仅算术暂用，不是确认标高',orientation_status='按布置图INSERT纠正负比例镜像；新总图要求工艺管口方位图，新接口绝对方位待核')
        p['installation_review']={'before_position_mm':old['position_mm'],'before_rotation_deg':old['rotation_deg'],'before_mirror_y':old.get('mirror_y',False),'source_rotation_deg':float(e.dxf.rotation),'source_scale':[e.dxf.xscale,e.dxf.yscale],'source_transform_matrix_xy':matrix.round(8).tolist(),'retained_xy_and_provisional_z':True,'temporary_bearing_EL':100+(p['position_mm'][2]+650)/1000,'support_status':'承托结构/标高待核；不采用旧暂定圆台','legacy_layout_review':legacy}
        installs.append(p)
    save(OUT/'安装表.json',installs)
    save(OUT/'支承待核.json',{'version':VERSION,'new_equipment_support':'三耳；承托底局部Z650、孔圈1382、60/180/300度','civil_geometry_created':False,'installed_civil_instances':0,'legacy_foundation':'版本/1.0/快照/水解桥架工程/models/设备/设备基础_20261106/L41B01','legacy_round_base_mm':[1300,200],'reason':'圆台不是三耳支承结构；缺承托EL与承托梁/支墩图，按用户选择不与新本体组合','items':[{k:p[k] for k in ['id','position_mm','z_status']} for p in installs]})
    save(OUT/'来源与差异.json',{'version':VERSION,'sources':{s:sha(REPO/s) for s in [SOURCE,LAYOUT,LEDGER]},'adopted':['台账复用图号与新总图图号一致、数量6台','1200内径/1216钢壳外径、500/350/450分段、约1446及顶口120','a/b/c DN300与d/e DN50五管口、三耳与24M20连接件','原图块中心；原INSERT镜像按矩阵分解纠正'],
        'changes':['平底直筒改下锥斗和中心底排渣口；补上下筒体连接层与顶盖立筋','a口改图示Y445.5（旧500）、局部Z700（旧880）；b口局部Z1238（旧880）；增加中心c排渣','A/C/E旧180度无镜像改0度+Y镜像，与源180度/X负比例矩阵等价；不是任意转向'],
        'retained':['6台X/Y和原暂用Z','设备1.0与旧基础源文件','已确认设备/建筑/桥架'],
        'differences':[{'topic':'台账H1220与新图约1446','policy':'台账原值保留，当前本体按匹配图号总图；总高加顶口120为1566'},{'topic':'旧暂定圆台与三耳支承','policy':params['user_decision']},{'topic':'工艺方位与承托EL缺失','policy':'不虚构新支承和安装标高；新接口现场绝对方位继续待核'}], 'limits':params['limits']})
    registry(params,installs)
    from publish_l41b01 import publish
    publish()
    print(json.dumps({'version':VERSION,'units':len(installs),'ports':len(ports),'ears':3,'bounds_mm':bounds,'civil_created':False},ensure_ascii=False))

def registry(params,installs):
    rows=json.loads((ROOT/'catalog.json').read_text());byid={p['id']:p for p in installs}
    for row in rows['models']:
        if row['id'] not in byid:continue
        p=byid[row['id']];files={'model':'版本/2.0/L41B01/设备/model_data.js','glb':'版本/2.0/L41B01/设备/L41B01.glb','obj':'版本/2.0/L41B01/设备/L41B01.obj','parameters':'parameters/'+p['id']+'.json','installation':'版本/2.0/L41B01/安装表.json'}
        row.update(model_version=VERSION,model_spec='内Ø1200/外Ø1216；上下分筒+锥斗；盖顶约H1446，顶口H1566；三耳承托待核',position_mm=p['position_mm'],rotation_deg=p['rotation_deg'],mirror_y=p['mirror_y'],current_files=files,position_basis=p['z_basis'])
        save(ROOT/'parameters'/(p['id']+'.json'),{**params,'id':p['id'],'group':'L41B01A-F','qty':6,'position_mm':p['position_mm'],'rotation_deg':p['rotation_deg'],'mirror_y':p['mirror_y'],'z_status':'待核','temporary_bearing_EL':p['installation_review']['temporary_bearing_EL'],'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/'+p['id']+'.json'})
    save(ROOT/'catalog.json',rows)
    project=json.loads((ROOT/'project.json').read_text());project['revisions']['L41B01']={'version':VERSION,'equipment':'版本/2.0/L41B01/设备/model_data.js','placements':'版本/2.0/L41B01/安装表.json','support_review':'版本/2.0/L41B01/支承待核.json','status':'6台本体/三耳更新，A/C/E源镜像纠正；保留暂用位置，承托结构/EL与新管口方位待核'}
    revised=sum(p['id'][:6] in project['revisions'] for p in rows['models']);project['active_version']='2.0（'+'、'.join(project['revisions'])+'）';project['counts'].update(completed_batches=len(project['revisions']),revised_items=revised,other_items_unchanged=99-revised)
    if len(project['revisions'])==4:project['next_class']='F41B03'
    save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'));o['version']=VERSION;o['equipment']['L41B01']={'dir':'版本/2.0/L41B01/设备/','bounds':params['bounds_mm']}
    o.setdefault('foundation_policy',{})['L41B01']='unresolved-three-ear-support'
    o['ledger']['L41B01A-F']={'状态':'2.0整改 · 三耳承托/标高待核','建模口径或缺项':'按适用总图LMBLJC2001-03L4103-1：上下筒体+锥斗、5管口、3耳及24M20连接；台账H1220保留追溯，新盖顶约1446、顶口1566。按用户选择保留原位置作待核展示，不再与旧圆台组合；承托EL及工艺方位待核。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')
if __name__=='__main__':main()
