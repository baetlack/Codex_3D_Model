"""C41B02 first equipment class: new drawing cover/nozzles and explicit support datum.
Confirmed tank OD5500/H5000 and mixer +2185 retained. The new drawing is a
vectorized page, not full-scale CAD: dimensions and approximate details are distinguished.
"""
from pathlib import Path
import sys,json,math,copy,hashlib,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
sys.path.insert(0,str(REPO/'水解桥架工程/tools/source'))
import build_tank_mixer as geo
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
from check_assembly import script
OUT=ROOT/'版本/2.0/C41B02';BASE=ROOT/'版本/1.0/快照'
SOURCE='水解设备模型库/水解设备图纸/钛液预热槽(C41B02A-E).dxf'
COLOR='#a5b9c3';STEEL='#b7c8d0';SUPPORT='#818b90'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 p.parent.mkdir(parents=True,exist_ok=True);content=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
 try:baseline=BASE/'水解设备模型库'/p.relative_to(ROOT)
 except ValueError:baseline=None
 if baseline and baseline.is_file() and b'\r\n' in baseline.read_bytes():content=content.replace('\n','\r\n')
 p.write_bytes(content.encode('utf-8'))
def add(p):geo.parts.append((p['name'],p['color'],p['vertices'],p['faces']))
def at_cylinder(name,center,z0,z1,r,color=STEEL,r2=None):
 geo.cyl(name,z0,z1,r,color,64,r2)
 n,c,v,f=geo.parts[-1];geo.parts[-1]=(n,c,[(x+center[0],y+center[1],z) for x,y,z in v],f)
def at_ring(name,center,z0,z1,ro,ri,color=STEEL):
 geo.ring(name,z0,z1,ro,ri,color,64)
 n,c,v,f=geo.parts[-1];geo.parts[-1]=(n,c,[(x+center[0],y+center[1],z) for x,y,z in v],f)
def horizontal_reducer(name,angle,z):
 a=math.radians(angle);u=np.array([math.cos(a),math.sin(a),0]);side=np.array([-math.sin(a),math.cos(a),0]);up=np.array([0,0,1]);v=[];faces=[]
 # Envelope only: DN350/250 or DN250/150 transition, 400 mm projection per table.
 major,minor=(350,250) if name=='g' else (250,150)
 rings=[(2730,(major+16)/2),(2910,(major+16)/2),(3118,(minor+12)/2),(3150,(minor+12)/2)]
 for distance,r in rings:
  center=u*distance+[0,0,z]
  v.extend((center+side*r*math.cos(t)+up*r*math.sin(t)).tolist() for t in np.linspace(0,2*math.pi,65)[:-1])
 for j in range(3):
  for i in range(64):k=(i+1)%64;faces.append([j*64+i,j*64+k,(j+1)*64+k,(j+1)*64+i])
 faces.extend([list(range(63,-1,-1)),list(range(192,256))]);geo.add('接口_'+name+'_侧向变径接管',STEEL,v,faces)
 # Flange oriented perpendicular to the radial pipe, not a vertical disk.
 ro=(505 if name=='g' else 395)/2;ri=(minor+12)/2;v=[];faces=[]
 for distance,r in [(3126,ro),(3150,ro),(3126,ri),(3150,ri)]:
  center=u*distance+[0,0,z];v.extend((center+side*r*math.cos(t)+up*r*math.sin(t)).tolist() for t in np.linspace(0,2*math.pi,65)[:-1])
 for i in range(64):j=(i+1)%64;faces.extend([[i,j,64+j,64+i],[128+j,128+i,192+i,192+j],[64+i,64+j,192+j,192+i],[j,i,128+i,128+j]])
 geo.add('接口_'+name+'_侧法兰',STEEL,v,faces)
 return {'id':name,'dn':f'{major}/{minor}','center_mm':(u*3150+[0,0,z]).tolist(),'normal':u.tolist(),'projection_mm':400,'status':'DN与伸出长度按管口表；变径及法兰外廓为展示包络'}

def main():
 eq=OUT/'设备';base=OUT/'基础';eq.mkdir(parents=True,exist_ok=True);base.mkdir(parents=True,exist_ok=True)
 original=script(BASE/'水解桥架工程/models/设备/设备基础_20261106/设备净模/C41B02/model_data.js','MODEL_PARTS')
 geo.parts.clear();offset=160
 # Preserve the approved mixer, shaft and tank body exactly, translating the assembly
 # above the new I16 support. Old six roof/two side interfaces are not reused.
 for p in original:
  if p['name'].startswith('接口_') or p['name'] in ['Tank_cover_lid','Lid_edge_rim']:continue
  p=copy.deepcopy(p);p['vertices']=[[x,y,z+offset] for x,y,z in p['vertices']];add(p)
 geo.cyl('Tank_cover_lid',5160,5215,2862,COLOR,128)
 geo.ring('Lid_edge_rim',5130,5160,2862,2750,STEEL,128)
 # Nine chord beams: 8 x 650 = 5200 spacing, I16 envelope H160.
 for i,x in enumerate(np.arange(-2600,2601,650),1):
  length=2*math.sqrt(2750**2-x**2)
  geo.box(f'设备支撑_I16_{i:02}_下翼缘',(x,0,5),(88,length,10),SUPPORT)
  geo.box(f'设备支撑_I16_{i:02}_腹板',(x,0,80),(6,length,140),SUPPORT)
  geo.box(f'设备支撑_I16_{i:02}_上翼缘',(x,0,155),(88,length,10),SUPPORT)
 # m opening frame, without replacing or stretching the approved mixer.
 theta=math.radians(112.5)
 for name,c,size in [('长边1',(0,-520,5235),(2940,20,40)),('长边2',(0,520,5235),(2940,20,40)),('短边1',(-1460,0,5235),(20,1020,40)),('短边2',(1460,0,5235),(20,1020,40))]:
  geo.box('盖面_m_安装框_'+name,c,size,STEEL);n,col,v,f=geo.parts[-1];geo.parts[-1]=(n,col,[(x*math.cos(theta)-y*math.sin(theta),x*math.sin(theta)+y*math.cos(theta),z) for x,y,z in v],f)
 ports=[]
 for i in range(8):
  angle=math.radians(22.5+45*i);u=np.array([math.cos(angle),math.sin(angle)]);center=u*2100
  at_ring(f'接口_k{i+1}_DN800安装口',center,5215,5341,430,400)
  at_cylinder(f'接口_k{i+1}_盘管检修盖',center,5341,5365,500)
  ports.append({'id':f'k{i+1}','dn':800,'center_mm':[*center.tolist(),5365],'normal':[0,0,1],'pitch_circle_mm':4200,'angle_deg':22.5+45*i,'status':'DN/数量按总图；盖外径1000mm与厚度为图面比例包络'})
  for label,sign in [('b',-1),('j',1)]:
   xy=center+u*sign*150
   at_ring(f'接口_{label}{i+1}_DN40接管',xy,5365,5491,28,20)
   at_ring(f'接口_{label}{i+1}_法兰',xy,5491,5515,75,20)
   ports.append({'id':f'{label}{i+1}','dn':40,'center_mm':[*xy.tolist(),5515],'normal':[0,0,1],'projection_mm':150,'status':'DN/数量/伸出按管口表；b/j间距300mm按图面比例，待详图'})
 for label,dn,angle,projection in [('a',200,45,150),('c',150,355,150),('d',200,175,150),('e',65,235,100),('f',80,305,100),('n',200,90,150)]:
  xy=np.array([math.cos(math.radians(angle)),math.sin(math.radians(angle))])*2400;top=5215+projection
  at_ring(f'接口_{label}_DN{dn}接管',xy,5215,top-24,dn/2+8,dn/2)
  at_ring(f'接口_{label}_法兰',xy,top-24,top,dn/2+65,dn/2)
  if label=='d':at_cylinder('接口_d_快开盖',xy,top,top+16,dn/2+65)
  ports.append({'id':label,'dn':dn,'center_mm':[*xy.tolist(),top],'normal':[0,0,1],'projection_mm':projection,'angle_deg':angle,'status':'DN/伸出按管口表；Φ4800圆周位置和小口角度按图面量测，待工艺方位图'})
 # a/p share the insertion axis; p is the DN250 installation connection.
 center=np.array([math.sqrt(.5),math.sqrt(.5)])*2400
 at_ring('接口_p_DN250套管',center,5215,5255,133,108)
 ports.append({'id':'p','dn':250,'coaxial_with':'a','center_mm':[*center.tolist(),5255],'normal':[0,0,1],'status':'按管口表与俯视a,p共轴；套管局部高度为包络'})
 ports.extend([horizontal_reducer('g',0,460),horizontal_reducer('h',180,4860)])
 geo.export_model(eq,'C41B02',color_materials=True,smooth=True)
 source_base=BASE/'水解桥架工程/models/设备/设备基础_20261106/C41B02'
 for p in source_base.iterdir():
  if p.is_file():shutil.copy2(p,base/p.name)
 base_parameters=json.loads((base/'参数.json').read_text());base_parameters['设备2.0承托说明']='圆台顶对应型钢底Z0；槽底Z160，圆台几何保持5700×150及50mm二次浇筑。';save(base/'参数.json',base_parameters)
 bb=np.vstack([np.array(p[2]) for p in geo.parts]);bounds=(bb.max(0)-bb.min(0)).round(6).tolist()
 parameters={'version':'2.0-C41B02-01','name':'钛液预热槽','units':'mm','source_drawing':SOURCE,'drawing_number':'LMT0701-03-C3302-1','source_sha256':sha(REPO/SOURCE),'user_decision':'2026-11-18按新增总图更新盖面和外部接口；保留Ø5500×5000及搅拌高2185mm',
  'tank':{'outside_diameter_mm':5500,'straight_shell_height_mm':5000,'bottom_z_mm':160,'shell_top_z_mm':5160,'basis':'既有用户确认尺寸'},
  'cover':{'outside_diameter_mm':5724,'plate_top_z_mm':5215,'k_count':8,'b_count':8,'j_count':8,'m_opening_mm':[2900,1020],'basis':'新增总图俯视与管口表；板厚/法兰包络仍含示意值'},
  'support':{'kind':'槽底I16型钢','height_mm':160,'beam_count':9,'center_spacing_mm':650,'basis':'主视8×650=5200及160高；翼缘88/腹板6/翼缘厚10和弦长端部为展示假设'},
  'mixer':{'height_above_shell_top_mm':2185,'top_z_mm':7345,'geometry':'冻结1.0原搅拌、开窗支架、轴与叶轮刚性上移160mm，未缩放未改形'},
  'local_datum':{'origin':'底部型钢承托面','bearing_z_mm':0,'tank_bottom_z_mm':160,'foundation_top_z_mm':0,'foundation_bottom_z_mm':-150},
  'installation':{'foundation_top_EL':112.150,'steel_bearing_EL':112.150,'tank_bottom_EL':112.310,'tank_top_EL':117.310,'mixer_top_EL':119.495,'status':'按基础顶和新增160mm型钢换算；POS EL是否指型钢底仍待确认','orientation_status':'新总图按工艺管口方位图；旧6孔布置符号不能证明新8组接口的现场方位，暂保留原实例旋转/镜像并标待核'},
  'ports':ports,'bounds_mm':bounds,'confirmed_dimensions':['槽体外径5500','直筒高5000','搅拌高出槽顶2185'],
  'limits':['新总图为转曲页面，DXF页面坐标不是设备毫米实尺寸。','新图剖面与底圈另标φ5560、俯视盖外径φ5724；本体5500仍按用户确认的外径，不宣称已完成制造内外径定义复核。','盘管/衬里/焊缝/螺栓不展开；内部轴和叶轮沿用旧模型。','小口位置、盖外径、支撑截面及未明示厚度属于量测或包络，不作加工尺寸。','本类仅第1张总图；第2—8张详图未提供。']}
 save(eq/'参数.json',parameters)
 oldcfg=json.loads((BASE/'水解总装工程/assembly.json').read_text());placements=[copy.deepcopy(p) for p in oldcfg['equipment'] if p['asset']=='C41B02']
 for p in placements:
  p.update(equipment_version='2.0-C41B02-01',local_datum='底部型钢承托面Z0；槽底Z160',z_status='按承托面换算，POS定义待核',orientation_status='新总图8组接口，工艺绝对方位待核；保留1.0旋转/镜像',z_basis='基础顶EL112.150=型钢底，型钢H160，槽底EL112.310；POS定义待核')
  p['installation_review']={'source_insert':p['source_insert'],'xy_unchanged':True,'rotation_and_mirror_unchanged':True,'foundation_top_EL':112.150,'support_bottom_EL':112.150,'tank_bottom_EL':112.310,'tank_top_EL':117.310,'mixer_top_EL':119.495,'support_gap_mm':0,'legacy_layout_review':p.pop('layout_review',{})}
 save(OUT/'安装表.json',placements)
 # Retire the contradictory legacy catalog metadata without deleting its old meshes.
 catalog=json.loads((ROOT/'catalog.json').read_text());by_id={p['id']:p for p in placements}
 catalog['legacy_export_version']='0.2';catalog['version']='2.0-first-C41B02'
 catalog['binding_policy']='C41B02当前模型与参数按current_files；obj/及viewer_data.js旧网格保留历史，当前浏览不读取它们。其余条目不变。'
 for row in catalog['models']:
  if row['id'] not in by_id:continue
  install=by_id[row['id']]
  row.update(w=5500,h=5000,level='EL112',plan_sheet='EL112',pos_el=112.15,model_spec='Ø5500×5000mm；槽底型钢H160；搅拌高2185mm',model_version='2.0-C41B02-01',position_mm=install['position_mm'],rotation_deg=install['rotation_deg'],mirror_y=install['mirror_y'],position_basis='EL112真实图块中心；Z0为型钢底EL112.150，POS定义和新接口方位待核；旧cad_position_mm仅保留文字点追溯')
  row['current_files']={'model':'版本/2.0/C41B02/设备/model_data.js','glb':'版本/2.0/C41B02/设备/C41B02.glb','obj':'版本/2.0/C41B02/设备/C41B02.obj','parameters':'parameters/'+row['id']+'.json','installation':'版本/2.0/C41B02/安装表.json'}
  row['legacy_1_0_parameters']='版本/1.0/快照/水解设备模型库/parameters/'+row['id']+'.json'
  current=copy.deepcopy(parameters);current.update(id=row['id'],group=row['group'],qty=row['qty'],level='EL112',pos_el=112.15,position_mm=install['position_mm'],rotation_deg=install['rotation_deg'],mirror_y=install['mirror_y'],position_basis=install['z_basis'],coordinate_reference='建筑轴网本地毫米坐标；安装原点为型钢底承托面',current_files=row['current_files'],legacy_parameters=row['legacy_1_0_parameters'])
  save(ROOT/'parameters'/str(row['id']+'.json'),current)
 save(ROOT/'catalog.json',catalog)
 save(OUT/'来源与差异.json',{'source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'decision':parameters['user_decision'],'preserved':['槽体5500×5000','搅拌高2185和原搅拌几何','基础5700×150及50mm二次浇筑','5台X/Y、旋转及镜像数值'],
  'changes':['旧6处盖面接口改8组k检修盖及各8处b/j接口，增补a/p,c,d,e,f,n及新g/h侧口','盖外径改按φ5724','补槽底160mm型钢、显式承托原点，槽体及驱动上移160mm','既有方位已核标签降为新接口待核，不沿用旧6孔匹配结论'],
  'remaining':parameters['limits']+[parameters['installation']['status'],parameters['installation']['orientation_status']]})
 save(OUT/'变更对比.json',{'version':'2.0-C41B02-01','before':{'tank_bottom_z_mm':0,'shell_top_z_mm':5000,'mixer_top_z_mm':7185,'top_nozzle_count':6,'side_nozzle_count':2,'cover_OD_mm':5500,'rim_OD_mm':5580,'foundation_mm':[5700,150]},'after':{'tank_bottom_z_mm':160,'shell_top_z_mm':5160,'mixer_top_z_mm':7345,'k_cover_count':8,'b_count':8,'j_count':8,'additional_port_ids':['a','p','c','d','e','f','n','g','h'],'cover_OD_mm':5724,'foundation_mm':[5700,150]},'position_transform_changed':False,'tank_world_z_change_mm':160,'mixer_geometry_rigid_translation_mm':[0,0,160]})
 state={'module':'水解设备模型库','active_version':'2.0（首批C41B02）','baseline_version':'1.0','counts':{'ledger_groups':35,'ledger_items':99,'completed_batches':1,'revised_items':5,'other_items_unchanged':94},'baseline':'版本/1.0/冻结清单.json','revisions':{'C41B02':{'version':'2.0-C41B02-01','equipment':'版本/2.0/C41B02/设备/model_data.js','foundation':'版本/2.0/C41B02/基础/model_data.js','placements':'版本/2.0/C41B02/安装表.json','status':'几何整改；安装解释及新接口方位待核'}},'next_class':'C41B04','rules':'每类单独追溯；不覆盖1.0与原图，不修改其他设备、建筑或桥架几何'}
 if (ROOT/'project.json').exists():
  previous=json.loads((ROOT/'project.json').read_text());state['revisions']={**previous.get('revisions',{}),**state['revisions']}
 catalog=json.loads((ROOT/'catalog.json').read_text())['models'];revised=sum(p['id'][:6] in state['revisions'] for p in catalog)
 state['counts'].update(completed_batches=len(state['revisions']),revised_items=revised,other_items_unchanged=len(catalog)-revised)
 save(ROOT/'project.json',state)
 foundation_info=json.loads((BASE/'水解桥架工程/models/设备/设备基础_20261106/基础索引.json').read_text())['assets']['C41B02'];foundation_info['dir']='版本/2.0/C41B02/基础/';foundation_info['note']='圆台顶与设备底部型钢承托面接触；槽体底相对承托面高160mm。基础几何及150mm总高/50mm二次浇筑保持。'
 foundation_info['datum']['label']='楼面 EL112.000 m（相对+12.000 m）'
 foundation_info['dimensions']='Ø5700 × 150 mm，含50mm二次浇筑；楼面EL112.000，基础顶EL112.150。'
 overrides={'version':'2.0-C41B02-01','equipment':{'C41B02':{'dir':'版本/2.0/C41B02/设备/','bounds':bounds}},'foundations':{'C41B02':foundation_info},'ledger':{'C41B02A-E':{'状态':'2.0整改 · 安装待核','建模口径或缺项':'新增总图盖面8组k盖、b/j各8处及外部管口；槽体Ø5500×5000、搅拌高2185保留。新增H160底型钢，按基础顶EL112.150换算槽底EL112.310。接口绝对方位与POS定义待核。'}}}
 if (ROOT/'equipment_versions.js').exists():
  previous=json.loads((ROOT/'equipment_versions.js').read_text().split('=',1)[1].strip().rstrip(';'))
  for key in ['equipment','foundations','ledger']:overrides[key]={**previous.get(key,{}),**overrides[key]}
 (ROOT/'equipment_versions.js').write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(overrides,ensure_ascii=False,separators=(',',':'))+';\n')
 from publish_c41b02 import publish
 publish()
 print(json.dumps({'version':parameters['version'],'parts':len(geo.parts),'ports':len(ports),'bounds_mm':bounds,'placements':len(placements),'installation_status':parameters['installation']['status']},ensure_ascii=False))
if __name__=='__main__':main()
