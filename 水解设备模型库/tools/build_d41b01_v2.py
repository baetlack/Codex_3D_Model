"""D41B01 external model from LMT1501-03-D4110-1; separate pair supports.

The main drawing is 2 CAD units/mm, the 1:8 ear detail 2.5 units/mm.
Explicit dimension text overrides take precedence over stretched CAD geometry.
Local Z0 is the underside of the four ear plates, at shell top minus 600 mm.
"""
from pathlib import Path
import copy, json, math, sys
import numpy as np
import ezdxf
from build_c41b04_v2 import geo, sha, save, move_last, cylinder, ring, plate, pipe, export, BODY, STEEL, DARK

ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/D41B01'
VERSION='2.0-D41B01-01'
SOURCE='水解设备模型库/水解设备图纸/晶种制备槽(D41B01A-E).dxf'
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
OLD='水解桥架工程/models/设备/设备基础_20261106/'
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script
CX=144589.3865209028;CY=31075.1742346563;TOP=600.;COVER=621.

def source_points(drawing):
    circles={e.dxf.handle:e for e in drawing.modelspace().query('CIRCLE')}
    refs={'a':'7F3A9','b':'7F3A8','c':'7F1BF','d':'7F1B8','e':'7F39E','f':'7F399','h':'7F33C'}
    return {k:{'handle':h,'xy_mm':[(circles[h].dxf.center.x-CX)/2,(circles[h].dxf.center.y-CY)/2],
               'drawn_outer_radius_mm':circles[h].dxf.radius/2} for k,h in refs.items()}

def face_bolts(prefix,xy,z,r,count,size=7):
    for i,a in enumerate(np.linspace(0,2*math.pi,count+1)[:-1],1):
        cylinder(f'紧固_{prefix}_{i:02}',(xy[0]+r*math.cos(a),xy[1]+r*math.sin(a)),z,z+10,size,DARK,6)

def external_model(points):
    geo.parts.clear();ports=[]
    # 1800 is the shell ID. The parts list specifies Ø1816×8; insulation is 60.
    geo.ring('本体_钢壳OD1816',-1100,TOP,908,900,BODY,96)
    geo.cyl('本体_锥底10度',-1152.8,-1008.123,79.5,BODY,96,900)
    geo.ring('保温_外包60mm',-1100,TOP,968,908,BODY,96)
    geo.hollow_frustum('保温_锥底包络',-1213.7,-1057.033,79.5,968,60,BODY,96)
    # Real cover holes; the hidden lining/coil/blades do not enter this exterior model.
    holes=[(*points[k]['xy_mm'],r) for k,r in [('a',50),('b',79.5),('c',28.5),('d',28.5),('e',54),('f',44.5),('h',213)]]+[(0,0,112.5)]
    outer=[(971*math.cos(a),971*math.sin(a)) for a in np.linspace(0,2*math.pi,97)[:-1]]
    plate('槽盖_外盖及接口开口',outer,holes,TOP,COVER,BODY)
    ring('槽盖_角钢法兰',(0,0),TOP-37,TOP,945,908)
    face_bolts('槽盖20M16',(0,0),COVER,958,20,8)
    # The DN400 manhole has a 426 neck and a 530 lid in detail III.
    xy=points['h']['xy_mm'];ring('接口_h_人孔颈',xy,COVER,COVER+100,213,200)
    cylinder('接口_h_取样盖',xy,COVER+100,COVER+108,265)
    geo.box('接口_h_盖柄',(xy[0],xy[1],COVER+130),(120,16,16),DARK)
    for x in [xy[0]-52,xy[0]+52]:geo.box('接口_h_盖柄立脚',(x,xy[1],COVER+119),(12,16,22),DARK)
    ports.append({'id':'h','dn':400,'center_mm':[*xy,COVER+108],'normal':[0,0,1],'role':'简易人孔/取样口','basis':'管口表及III详图：颈426、盖530、伸出100、盖厚8'})
    for k,dn,ro,rf in [('e',100,54,110),('f',80,44.5,100)]:
        xy=points[k]['xy_mm'];ring(f'接口_{k}_接管',xy,COVER,COVER+82,ro,dn/2)
        ring(f'接口_顶盖法兰_{k}',xy,COVER+82,COVER+100,rf,dn/2)
        face_bolts(k,xy,COVER+100,rf-18,8)
        ports.append({'id':k,'dn':dn,'center_mm':[*xy,COVER+100],'normal':[0,0,1],'role':'洗水进口' if k=='e' else '液位计口','basis':'管口表伸出100；中心与法兰外廓直接读取主俯视圆'})
    # Feed insertion assemblies: distinguish the mounting flange from the inlet.
    for k,dn,base_dn,ro,rf,inlet_rf in [('a',50,100,54,105,82.5),('b',100,150,79.5,132.5,110)]:
        xy=points[k]['xy_mm'];ring(f'接口_{k}_安装短颈',xy,COVER,COVER+82,ro,base_dn/2-4)
        cylinder(f'接口_{k}_安装盖',xy,COVER+82,COVER+100,rf)
        ring(f'接口_{k}_进料插管',xy,COVER+100,COVER+212,28.5 if k=='a' else 54,dn/2)
        ring(f'接口_顶盖法兰_{k}',xy,COVER+212,COVER+230,inlet_rf,dn/2)
        face_bolts(k,xy,COVER+230,inlet_rf-17,4 if k=='a' else 8)
        ports.append({'id':k,'dn':dn,'mount_dn':base_dn,'center_mm':[*xy,COVER+230],'normal':[0,0,1],'role':'碱液安装口/进口' if k=='a' else '钛液安装口/进口','basis':'管口表100/130mm高度链；插管末端细节未展开'})
    # Two steam pipes share a rectangular installation plate. 180 pitch is explicit.
    geo.box('接口_cd_共座',(700,0,COVER+25),(280,360,50),STEEL)
    for k in ['c','d']:
        xy=points[k]['xy_mm'];ring(f'接口_{k}_安装法兰',xy,COVER+32,COVER+50,82.5,28.5)
        ring(f'接口_{k}_蒸汽接管',xy,COVER+50,COVER+186,28.5,25)
        ring(f'接口_顶盖法兰_{k}',xy,COVER+186,COVER+204,82.5,25)
        face_bolts(k,xy,COVER+204,62.5,4)
        ports.append({'id':k,'dn':50,'center_mm':[*xy,COVER+204],'normal':[0,0,1],'role':'蒸汽进口' if k=='c' else '冷凝液出口','basis':'主俯视管距180；主视50+154（标注覆盖几何169），表中名义伸出150另记'})
    # Three tight ceramic-lined coil-support nozzles, all on the 572 plane above
    # the straight-shell lower reference. They are not a separate outside cage.
    for i,degrees in enumerate([-90,150,30],1):
        a=math.radians(degrees);u=np.array([math.cos(a),math.sin(a),0]);z=-428.0
        start=u*908+[0,0,z];end=u*1008+[0,0,z]
        pipe(f'接口_m{i}_接管',start,end-u*18,79.5,75)
        pipe(f'接口_m{i}_法兰',end-u*18,end,132.5,75)
        ports.append({'id':'m'+str(i),'dn':150,'center_mm':end.tolist(),'normal':u.tolist(),'role':'盘管支撑管口','basis':'m1—3、伸出100；高度572为图面量测；角度按俯视60度分布'})
    # 45-degree upward slanted thermometer port g on the southwest ray.
    a=math.radians(225);radial=np.array([math.cos(a),math.sin(a),0]);axis=(radial+np.array([0,0,1]))/math.sqrt(2)
    start=radial*908+[0,0,-604.9];end=start+250*axis
    pipe('接口_g_斜接管',start,end-axis*18,44.5,40);pipe('接口_g_斜法兰',end-axis*18,end,100,40)
    ports.append({'id':'g','dn':80,'center_mm':end.tolist(),'normal':axis.tolist(),'role':'温度计口','basis':'管口表伸出250、主视45度、俯视西南；根部高度按图面量测'})
    bottom=-1312.1173
    ring('接口_j_底排接管',(0,0),bottom+20,-1132,79.5,75)
    ring('接口_j_底排法兰',(0,0),bottom,bottom+20,142.5,75)
    ports.append({'id':'j','dn':150,'center_mm':[0,0,bottom],'normal':[0,0,-1],'role':'放料口','basis':'管口表伸出160；钢锥底至端面按主视校准量测'})
    # Explicit rigid-ring ear detail, BOM items 51—54: two close rings and 4 ears.
    ring('托耳_补强圈OD1832',(0,0),-47,483,916,908)
    for label,z in [('下',0),('上',412)]:ring('托耳_'+label+'刚性环OD2072',(0,0),z,z+12,1036,916)
    for i,a in enumerate(np.linspace(0,2*math.pi,5)[:-1],1):
        plate(f'托耳_R{i}_承托底板',[(916,-200),(1166,-200),(1166,200),(916,200)],[(1051,0,18)],0,12,angle=a)
        for side in [-1,1]:
            v=[(x,y,z) for y in [side*110-6,side*110+6] for x,z in [(916,12),(1166,12),(1016,412),(916,412)]]
            geo.add(f'托耳_R{i}_筋板{side}',STEEL,v,[[3,2,1,0],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]);move_last(angle=a)
    # Raised rectangular mixer installation and an open four-sided DJ55A stand.
    geo.box('搅拌_k_安装口颈',(0,0,COVER+25),(250,1200,50),BODY)
    geo.box('搅拌_k_安装盖',(0,0,COVER+60),(430,1300,20),STEEL)
    for sign in [-1,1]:
        geo.box('搅拌_k_高座侧板',(sign*205,0,758),(20,500,115),STEEL)
    cylinder('搅拌_机架下法兰',(0,0),796,816,250)
    ring('搅拌_机架下环',(0,0),816,840,235,180)
    ring('搅拌_机架中环',(0,0),1181,1201,180,135)
    ring('搅拌_机架上环',(0,0),1437,1461,160,110)
    for i,a in enumerate(np.linspace(0,2*math.pi,5)[:-1],1):
        geo.brace(f'搅拌_DJ55A开窗架腿{i}',221,840,145,1437,22,45,STEEL);move_last(angle=a)
    cylinder('搅拌_外露传动轴',(0,0),840,1461,32,DARK,32)
    cylinder('搅拌_联接套',(0,0),1130,1230,65,DARK,48)
    cylinder('驱动_减速机下法兰',(0,0),1461,1485,165)
    geo.cyl('驱动_BLD4机壳',1485,1739,135,BODY,64,112)
    cylinder('驱动_减速机上法兰',(0,0),1739,1763,165)
    cylinder('驱动_电机底座',(0,0),1763,1790,135)
    cylinder('驱动_Y112M电机',(0,0),1790,2053,115,BODY)
    for i,a in enumerate(np.linspace(0,2*math.pi,17)[:-1],1):
        xy=(116*math.cos(a),116*math.sin(a));cylinder(f'驱动_电机散热筋{i}',xy,1800,2033,5,STEEL,8)
    geo.cyl('驱动_电机顶帽',2053,2103,122,BODY,64,110)
    ports.append({'id':'k','size_mm':[250,1200],'center_mm':[0,0,COVER+50],'role':'搅拌器安装口','basis':'管口表250×1200、伸出50；架/减速/电机高度645/302/340；未标外廓按主视量测'})
    return ports

def main():
    pinned=json.loads((OUT/'本批保护基准.json').read_text());old={p['id']:p for p in pinned['equipment_placements']}
    drawing=ezdxf.readfile(REPO/SOURCE);points=source_points(drawing);ports=external_model(points)
    bounds=export(OUT/'设备','D41B01')
    params={'version':VERSION,'name':'晶种制备槽','units':'mm','source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'drawing_number':'LMT1501-03-D4110-1','drawing_stage':'施工图总图（共5张中的第1张）','main_geometry_scale':2,'ear_detail_geometry_scale':2.5,
        'dimensions_mm':{'shell_ID':1800,'shell_OD':1816,'shell_thickness':8,'ledger_straight_height':1600,'steel_shell_stock_height':1690,'cone_angle_deg':10,'insulation_thickness':60,'insulated_shell_OD':1936,'shell_top_from_bearing':600,'cover_height':21,'cover_OD':1942,'mixer_stand_height':645,'reducer_height':302,'motor_height':340,'mixer_above_shell_top':1503,'nominal_overall_height_approx':3410,'model_overall_height':3415.1173,'ear_plate_size':[250,400,12],'ear_bolt_hole_diameter':36,'ear_bolt_center_span':2102,'rigid_ring_OD_ID_thickness':[2072,1832,12],'reinforcing_band_height':530},
        'datum':'四向托耳底承托面Z0；钢壳顶Z600；底排端面Z-1312.1173；电机顶Z2103',
        'drawing_quantity':4,'ledger_quantity':5,'user_decision':'A—E五台均采用新本体；A支架继续待核。新图数量4不用于删减台账。',
        'ports':ports,'top_plan_source_points':points,'bounds_mm':bounds,
        'installation':{'bearing_EL':111.0,'shell_top_EL':111.6,'motor_top_EL':113.103,'drain_end_EL':109.6878827,'support_bottom_EL':108.5,'pairs':['BC','DE'],'A_support':'未取得支架依据，不复制成对支架给A'},
        'limits':['总图明确管口方位须按工艺专业方位图；本次保留5台X/Y、旋转和镜像，新增接口绝对方位待核。','总图示意总高约3410与分段尺寸/图面量测链约3415并列记录，不将近似总高作为精确制造尺寸。','图中覆盖尺寸优先：电机340而非几何361、顶盖21而非26、c/d高154而非169、耳板12而非20。','托耳孔跨主视2102与俯视图面2118差16；采用明示2102，现有支架梁轴2118保留，孔各偏轴8mm仍处于承托范围。','平面两槽中心距2600，剖面另标水平2500，相差100；按现有平面位置保留2600，差异待图纸复核。支架高度2500另由EL108.500至EL111.000确定。','支架纵横梁160×200、立柱160×160继续沿用既有示意截面；未提供支架施工详图，不标为结构验收完成。','保温60只表达外包络，隐藏衬胶/衬砖、内部盘管与叶轮不展开；不补无尺寸雨棚及外接工艺管线。']}
    save(OUT/'设备/参数.json',params)
    installs=[]
    for s in 'ABCDE':
        p=copy.deepcopy(old['D41B01'+s]);legacy=p.pop('layout_review',{})
        p['position_mm'][2]=11000
        p.update(equipment_version=VERSION,local_datum='四向托耳底承托面Z0',z_status='待核' if s=='A' else '有安装基准',z_basis='保持原承托面EL111.000；B/C、D/E支架底EL108.500，上部承托高2500；A支架及该标高适用性待核',orientation_status='保留原图INSERT旋转/镜像；新总图要求工艺管口方位图，新接口绝对方位待核')
        p['installation_review']={'before_position_mm':old[p['id']]['position_mm'],'before_bearing_local_z_mm':1180,'bearing_world_z_mm':11000,'xy_rotation_mirror_unchanged':True,'legacy_layout_review':legacy,'support_status':'A支架待核' if s=='A' else '成对承托模型；截面示意'}
        installs.append(p)
    save(OUT/'安装表.json',installs)
    # Preserve the existing 2600 pair rack mesh. It already supports all four ears
    # on real solid bearing areas; do not turn schematic sections into invented steel.
    support=script(REPO/(OLD+'D41B01/model_data.js'),'MODEL_PARTS')
    geo.parts[:]=[(q['name'],q['color'],q['vertices'],q['faces']) for q in support]
    support_bounds=export(OUT/'支架','D41B01')
    support_params={'version':VERSION,'name':'晶种制备槽成对安装支架','source_drawing':LAYOUT,'source_sha256':sha(REPO/LAYOUT),'geometry_source':OLD+'D41B01/model_data.js','geometry_source_sha256':sha(REPO/(OLD+'D41B01/model_data.js')),'units':'mm','center_spacing_mm':2600,'bearing_height_mm':2500,'datum':'梁顶Z0，支架底Z-2500；总装原点EL111.000','bounds_mm':support_bounds,'sections':'沿用示意：梁160×200、柱160×160；未取得支架施工截面','supports':[['D41B01B','D41B01C'],['D41B01D','D41B01E']],'limits':['A支架待核，不在总装中增加A支架。','平面中心距2600（DIMENSION F1C1C/F1B80），剖面水平中心距2500（57BF9），差100待核；本次保持平面2600。支架竖向高度另由111.000-108.500得2500。']}
    save(OUT/'支架/参数.json',support_params)
    frames=[]
    for pair in ['BC','DE']:
        pp=[p for p in installs if p['id'][-1] in pair];xy=np.mean([p['position_mm'][:2] for p in pp],axis=0)
        frames.append({'id':'FRAME-D41B01'+pair,'name':'晶种制备槽'+pair+'组成对支架','asset':'foundation-D41B01','position_mm':[*xy.tolist(),11000],'rotation_deg':0,'level':'EL106','support_for':[p['id'] for p in pp],'status':'承托EL111.000、支架底EL108.500；截面示意待施工图'})
    save(OUT/'支架安装表.json',frames)
    source_diff={'version':VERSION,'sources':{s:sha(REPO/s) for s in [SOURCE,LAYOUT,OLD+'D41B01/model_data.js']},'user_decision':params['user_decision'],
        'accepted':['钢壳内径1800、外径1816、保温60；1600内筒段与钢壳用料高1690分开','顶盖7处开口及中央搅拌安装口、3个侧盘管支撑口、斜温度口及底排口','四耳底板250×400×12、双筋及贴身刚性环按详图/BOM','5台中心/旋转/镜像保留；新局部承托原点统一0，世界承托面保持EL111.000'],
        'conflicts':[{'topic':'图纸4台与台账5台','resolution':params['user_decision']},{'topic':'平面/剖面水平中心距','plan_mm':2600,'plan_handles':['F1C1C','F1B80'],'section_mm':2500,'section_handle':'57BF9','difference_mm':100,'resolution':'本次以既有平面位置2600建模，剖面2500差异待复核，不擅自挪动设备。支架高2500由独立标高差111.000-108.500确定。'},{'topic':'孔距2102与2118','resolution':'明示2102建耳孔，旧支架梁轴2118保留；通过实际承托区校核，不移动建筑或其他设备'},{'topic':'制造详图不齐','resolution':'当前仅总图第1张；其余4张及工艺方位图未取得，未标外廓/小厚度按图面展示'}], 'limits':params['limits']}
    save(OUT/'来源与差异.json',source_diff)
    update_registry(params,installs,support_bounds)
    from publish_d41b01 import publish
    publish()
    print(json.dumps({'version':VERSION,'units':len(installs),'ports':len(ports),'bounds_mm':bounds,'pair_supports':len(frames)},ensure_ascii=False))

def update_registry(params,installs,support_bounds):
    byid={p['id']:p for p in installs};catalog=json.loads((ROOT/'catalog.json').read_text());catalog['version']='2.0-revised-classes'
    catalog['binding_policy']='已整改条目按current_files引用2.0；其余条目和历史导出保留；旧cad_position_mm是文字点追溯，不作为安装中心。'
    for row in catalog['models']:
        if row['id'] not in byid:continue
        p=byid[row['id']];files={'model':'版本/2.0/D41B01/设备/model_data.js','glb':'版本/2.0/D41B01/设备/D41B01.glb','obj':'版本/2.0/D41B01/设备/D41B01.obj','parameters':'parameters/'+p['id']+'.json','installation':'版本/2.0/D41B01/安装表.json'}
        row.update(model_version=VERSION,model_spec='壳内Ø1800/钢壳Ø1816；保温60；筒高1600；四耳承托EL111.000；A支架待核',position_mm=p['position_mm'],rotation_deg=p['rotation_deg'],mirror_y=p['mirror_y'],current_files=files,position_basis=p['z_basis'])
        save(ROOT/'parameters'/(p['id']+'.json'),{**params,'id':p['id'],'group':'D41B01A-E','qty':5,'position_mm':p['position_mm'],'rotation_deg':p['rotation_deg'],'mirror_y':p['mirror_y'],'installation_status':p['z_status'],'current_files':files,'legacy_parameters':'版本/1.0/快照/水解设备模型库/parameters/'+p['id']+'.json'})
    save(ROOT/'catalog.json',catalog)
    project=json.loads((ROOT/'project.json').read_text())
    project['revisions']['D41B01']={'version':VERSION,'equipment':'版本/2.0/D41B01/设备/model_data.js','foundation':'版本/2.0/D41B01/支架/model_data.js','foundation_single':'版本/2.0/D41B01/支架/model_data.js','placements':'版本/2.0/D41B01/安装表.json','support_placements':'版本/2.0/D41B01/支架安装表.json','status':'5台新本体与BC/DE成对支架；平剖面槽距100差异、A支架/新接口绝对方位待核'}
    project['active_version']='2.0（'+ '、'.join(project['revisions'])+'）'
    revised=sum(r['id'][:6] in project['revisions'] for r in catalog['models'])
    project['counts'].update(completed_batches=len(project['revisions']),revised_items=revised,other_items_unchanged=99-revised);project['next_class']='L41B01';save(ROOT/'project.json',project)
    path=ROOT/'equipment_versions.js';o=json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'));o['version']=VERSION
    o['equipment']['D41B01']={'dir':'版本/2.0/D41B01/设备/','bounds':params['bounds_mm']}
    f=json.loads((REPO/(OLD+'基础索引.json')).read_text())['assets']['D41B01']
    f.update(dir='版本/2.0/D41B01/支架/',stem='D41B01',bounds=support_bounds,mount=[0,0,0],offsets=[[0,-1300,0],[0,1300,0]],dimensions='双槽中心距2600；梁顶EL111.000，距支架底2500；本体托耳底Z0',note='仅B/C及D/E成对支架有依据，A支架待核。平面槽距2600，剖面水平2500差100待核；钢梁柱截面继续示意。')
    o['foundations']['D41B01']=f;o['ledger']['D41B01A-E']={'状态':'2.0整改 · A支架/管口方位待核','建模口径或缺项':'5台按用户选择统一新总图LMT1501-03-D4110-1：壳内1800/外1816、60mm保温，顶盖7口+搅拌安装口，四耳、3个支撑侧口、斜温度口及底排。BC/DE中心距2600、承托EL111.000，支架底EL108.500；平剖面槽距差100、A支架与新接口绝对方位待核。'}
    path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(o,ensure_ascii=False,separators=(',',':'))+';\n')

if __name__=='__main__':main()
