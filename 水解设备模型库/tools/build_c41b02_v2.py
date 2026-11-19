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

def main():
 eq=OUT/'设备';base=OUT/'基础';eq.mkdir(parents=True,exist_ok=True);base.mkdir(parents=True,exist_ok=True)
 original=script(BASE/'水解桥架工程/models/设备/设备基础_20261106/设备净模/C41B02/model_data.js','MODEL_PARTS')
 geo.parts.clear();offset=160
 # Preserve tank, confirmed upper drive, shaft and bottom support.
 # Roof, nozzles and 06 support frame are rebuilt from the checked drawing.
 for p in original:
  if p['name'].startswith(('接口_','06_')) or p['name'] in ['Tank_cover_lid','Lid_edge_rim']:continue
  p=copy.deepcopy(p);p['vertices']=[[x,y,z+offset] for x,y,z in p['vertices']];add(p)
 # Nine chord beams: 8 x 650 = 5200 spacing, I16 envelope H160.
 for i,x in enumerate(np.arange(-2600,2601,650),1):
  length=2*math.sqrt(2750**2-x**2)
  geo.box(f'设备支撑_I16_{i:02}_下翼缘',(x,0,5),(88,length,10),SUPPORT)
  geo.box(f'设备支撑_I16_{i:02}_腹板',(x,0,80),(6,length,140),SUPPORT)
  geo.box(f'设备支撑_I16_{i:02}_上翼缘',(x,0,155),(88,length,10),SUPPORT)
 from c41b02_topside import add_topside
 ports,trace=add_topside(geo)
 save(OUT/'顶侧结构图面量测.json',trace)
 geo.export_model(eq,'C41B02',color_materials=True,smooth=True)
 source_base=BASE/'水解桥架工程/models/设备/设备基础_20261106/C41B02'
 for p in source_base.iterdir():
  if p.is_file() and not (base/p.name).exists():shutil.copy2(p,base/p.name)
 bb=np.vstack([np.array(p[2]) for p in geo.parts]);bounds=(bb.max(0)-bb.min(0)).round(6).tolist()
 parameters={'version':'2.0-C41B02-02','name':'钛液预热槽','units':'mm','source_drawing':SOURCE,'drawing_number':'LMT0701-03-C3302-1','source_sha256':sha(REPO/SOURCE),'user_decision':'2026-11-18按新增总图更新盖面和外部接口；保留Ø5500×5000及搅拌高2185mm',
  'tank':{'outside_diameter_mm':5500,'straight_shell_height_mm':5000,'bottom_z_mm':160,'shell_top_z_mm':5160,'basis':'既有用户确认尺寸'},
  'cover':{'outside_diameter_mm':5724,'plate_top_z_mm':5175,'k_count':8,'b_count':8,'j_count':8,'m_opening_mm':[2900,1020],'steel_plate_thickness_mm':12,'gasket_mm':3,'m_seat_height_mm':280,'m_top_plate_thickness_mm':30,'m_top_z_mm':5485,'m_plan_outer_mm':[3064,1150],'basis':'顶部位置按校准原图量测；盖与支座按局部详图/明细表；未标项仍列包络'},
  'support':{'kind':'槽底I16型钢','height_mm':160,'beam_count':9,'center_spacing_mm':650,'basis':'主视8×650=5200及160高；翼缘88/腹板6/翼缘厚10和弦长端部为展示假设'},
  'mixer':{'height_above_shell_top_mm':2185,'top_z_mm':7345,'geometry':'电机、联轴器、中间轴、槽内轴和叶轮保持01版位置/形状；06支架改圆筒开窗外形并衔接m高座，总高仍为2185mm','frame_body_OD_mm':490,'frame_foot_OD_mm':600,'frame_mount_z_mm':5485},
  'local_datum':{'origin':'底部型钢承托面','bearing_z_mm':0,'tank_bottom_z_mm':160,'foundation_top_z_mm':0,'foundation_bottom_z_mm':-150},
  'installation':{'foundation_top_EL':112.150,'steel_bearing_EL':112.150,'tank_bottom_EL':112.310,'tank_top_EL':117.310,'mixer_top_EL':119.495,'status':'按基础顶和新增160mm型钢换算；POS EL是否指型钢底仍待确认','orientation_status':'新总图按工艺管口方位图；旧6孔布置符号不能证明新8组接口的现场方位，暂保留原实例旋转/镜像并标待核'},
  'ports':ports,'bounds_mm':bounds,'confirmed_dimensions':['槽体外径5500','直筒高5000','搅拌高出槽顶2185'],
  'limits':['新总图为转曲页面，DXF页面坐标不是设备毫米实尺寸。','新图剖面与底圈另标φ5560、俯视盖外径φ5724；本体5500仍按用户确认的外径，不宣称已完成制造内外径定义复核。','盘管/衬里/焊缝/螺栓不展开；内部轴和叶轮沿用旧模型。','小口中心按φ5724校准图面量测；k盖1075/940及b/j共座400/350按明细表；法兰未标厚度、踏步板高度及支架细部仍含量测/包络。','本类仅第1张总图；第2—8张详图未提供。']}
 save(eq/'参数.json',parameters)
 oldcfg=json.loads((BASE/'水解总装工程/assembly.json').read_text());placements=[copy.deepcopy(p) for p in oldcfg['equipment'] if p['asset']=='C41B02']
 for p in placements:
  p.update(equipment_version='2.0-C41B02-02',local_datum='底部型钢承托面Z0；槽底Z160',z_status='按承托面换算，POS定义待核',orientation_status='新总图8组接口，工艺绝对方位待核；保留1.0旋转/镜像',z_basis='基础顶EL112.150=型钢底，型钢H160，槽底EL112.310；POS定义待核')
  p['installation_review']={'source_insert':p['source_insert'],'xy_unchanged':True,'rotation_and_mirror_unchanged':True,'foundation_top_EL':112.150,'support_bottom_EL':112.150,'tank_bottom_EL':112.310,'tank_top_EL':117.310,'mixer_top_EL':119.495,'support_gap_mm':0,'legacy_layout_review':p.pop('layout_review',{})}
 save(OUT/'安装表.json',placements)
 # Retire the contradictory legacy catalog metadata without deleting its old meshes.
 catalog=json.loads((ROOT/'catalog.json').read_text());by_id={p['id']:p for p in placements}
 catalog['legacy_export_version']='0.2';catalog['version']='2.0-first-C41B02'
 catalog['binding_policy']='C41B02当前模型与参数按current_files；obj/及viewer_data.js旧网格保留历史，当前浏览不读取它们。其余条目不变。'
 for row in catalog['models']:
  if row['id'] not in by_id:continue
  install=by_id[row['id']]
  row.update(w=5500,h=5000,level='EL112',plan_sheet='EL112',pos_el=112.15,model_spec='Ø5500×5000mm；槽底型钢H160；搅拌高2185mm',model_version='2.0-C41B02-02',position_mm=install['position_mm'],rotation_deg=install['rotation_deg'],mirror_y=install['mirror_y'],position_basis='EL112真实图块中心；Z0为型钢底EL112.150，POS定义和新接口方位待核；旧cad_position_mm仅保留文字点追溯')
  row['current_files']={'model':'版本/2.0/C41B02/设备/model_data.js','glb':'版本/2.0/C41B02/设备/C41B02.glb','obj':'版本/2.0/C41B02/设备/C41B02.obj','parameters':'parameters/'+row['id']+'.json','installation':'版本/2.0/C41B02/安装表.json'}
  row['legacy_1_0_parameters']='版本/1.0/快照/水解设备模型库/parameters/'+row['id']+'.json'
  current=copy.deepcopy(parameters);current.update(id=row['id'],group=row['group'],qty=row['qty'],level='EL112',pos_el=112.15,position_mm=install['position_mm'],rotation_deg=install['rotation_deg'],mirror_y=install['mirror_y'],position_basis=install['z_basis'],coordinate_reference='建筑轴网本地毫米坐标；安装原点为型钢底承托面',current_files=row['current_files'],legacy_parameters=row['legacy_1_0_parameters'])
  save(ROOT/'parameters'/str(row['id']+'.json'),current)
 save(ROOT/'catalog.json',catalog)
 save(OUT/'来源与差异.json',{'source_drawing':SOURCE,'source_sha256':sha(REPO/SOURCE),'decision':parameters['user_decision'],'preserved':['槽体5500×5000','搅拌高2185及电机/联轴器/中间轴/内部轴叶轮；06支架重建','基础5700×150及50mm二次浇筑','5台X/Y、旋转及镜像数值'],
  'prior_revision':'2.0-C41B02-01','this_revision_changes':['m薄框改280mm座体和30mm顶板、对开盖板/踏步板，圆筒开窗支架衔接','k盖径按明细表1075；b/j由径向300改切向250并补460共座法兰/400垫片','小口中心按原图闭合圆校准，f从φ4800改φ4200，a/p约49.74度','g/h锥形管改同轴直套管、连接法兰/垫片和外端短接，按200+13+200尺寸链','d补带柄盖；n改φ340盲板和φ295螺栓圆；a/p拆上下同轴接管'],'changes':['旧6处盖面接口改8组k检修盖及各8处b/j接口，增补a/p,c,d,e,f,n及新g/h侧口','盖外径改按φ5724','补槽底160mm型钢、显式承托原点，槽体及驱动上移160mm','既有方位已核标签降为新接口待核，不沿用旧6孔匹配结论'],
  'remaining':parameters['limits']+[parameters['installation']['status'],parameters['installation']['orientation_status']]})
 save(OUT/'顶侧二次修正对比.json',{'revision':'2.0-C41B02-02','previous_revision':'2.0-C41B02-01','foundation_and_bottom_support':'不变','m_seat_height_mm':[40,280],'m_top_plate_mm':30,'k_cover_OD_mm':[1000,1075],'bj_pair_spacing_mm':[300,250],'bj_direction':['径向','切向'],'side_structure':['锥形变径','直套管/连接法兰/垫片/直短接'],'side_projection_chain_mm':[200,13,200],'d_cover':['普通盖','带竖柄取样盖'],'n_cover':['开口','φ340盲板/φ295螺栓圆'],'measurement_reference':'顶侧结构图面量测.json','mixer_confirmed_height_mm':2185})
 save(OUT/'变更对比.json',{'version':'2.0-C41B02-02','before_version':'设备1.0','before':{'tank_bottom_z_mm':0,'shell_top_z_mm':5000,'mixer_top_z_mm':7185,'top_nozzle_count':6,'side_nozzle_count':2,'cover_OD_mm':5500,'rim_OD_mm':5580,'foundation_mm':[5700,150]},'after':{'tank_bottom_z_mm':160,'shell_top_z_mm':5160,'mixer_top_z_mm':7345,'k_cover_count':8,'b_count':8,'j_count':8,'additional_port_ids':['a','p','c','d','e','f','n','g','h'],'cover_OD_mm':5724,'foundation_mm':[5700,150]},'position_transform_changed':False,'tank_world_z_change_mm':160,'preserved_drive_geometry_translation_mm':[0,0,160],'frame_06':'按02版圆筒开窗外形重建，非整体刚性平移'})
 state={'module':'水解设备模型库','active_version':'2.0（首批C41B02）','baseline_version':'1.0','counts':{'ledger_groups':35,'ledger_items':99,'completed_batches':1,'revised_items':5,'other_items_unchanged':94},'baseline':'版本/1.0/冻结清单.json','revisions':{'C41B02':{'version':'2.0-C41B02-02','equipment':'版本/2.0/C41B02/设备/model_data.js','foundation':'版本/2.0/C41B02/基础/model_data.js','placements':'版本/2.0/C41B02/安装表.json','status':'顶侧结构二次修正；基础/底钢不变，POS与绝对方位待核'}},'next_class':'C41B04','rules':'每类单独追溯；不覆盖1.0与原图，不修改其他设备、建筑或桥架几何'}
 if (ROOT/'project.json').exists():
  previous=json.loads((ROOT/'project.json').read_text());state['revisions']={**previous.get('revisions',{}),**state['revisions']}
 catalog=json.loads((ROOT/'catalog.json').read_text())['models'];revised=sum(p['id'][:6] in state['revisions'] for p in catalog)
 state['counts'].update(completed_batches=len(state['revisions']),revised_items=revised,other_items_unchanged=len(catalog)-revised)
 save(ROOT/'project.json',state)
 foundation_info=json.loads((BASE/'水解桥架工程/models/设备/设备基础_20261106/基础索引.json').read_text())['assets']['C41B02'];foundation_info['dir']='版本/2.0/C41B02/基础/';foundation_info['note']='圆台顶与设备底部型钢承托面接触；槽体底相对承托面高160mm。基础几何及150mm总高/50mm二次浇筑保持。'
 foundation_info['datum']['label']='楼面 EL112.000 m（相对+12.000 m）'
 foundation_info['dimensions']='Ø5700 × 150 mm，含50mm二次浇筑；楼面EL112.000，基础顶EL112.150。'
 overrides={'version':'2.0-C41B02-02','equipment':{'C41B02':{'dir':'版本/2.0/C41B02/设备/','bounds':bounds}},'foundations':{'C41B02':foundation_info},'ledger':{'C41B02A-E':{'状态':'2.0整改 · 安装待核','建模口径或缺项':'顶侧02修正：k盖1075、b/j切向250及共座、m高座280/顶板30、g/h直套管双法兰、d带柄盖/n盲板；槽体Ø5500×5000、搅拌高2185保留。新增H160底型钢，按基础顶EL112.150换算槽底EL112.310。接口绝对方位与POS定义待核。'}}}
 if (ROOT/'equipment_versions.js').exists():
  previous=json.loads((ROOT/'equipment_versions.js').read_text().split('=',1)[1].strip().rstrip(';'))
  for key in ['equipment','foundations','ledger']:overrides[key]={**previous.get(key,{}),**overrides[key]}
 (ROOT/'equipment_versions.js').write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(overrides,ensure_ascii=False,separators=(',',':'))+';\n')
 from publish_c41b02 import publish
 publish()
 print(json.dumps({'version':parameters['version'],'parts':len(geo.parts),'ports':len(ports),'bounds_mm':bounds,'placements':len(placements),'installation_status':parameters['installation']['status']},ensure_ascii=False))
if __name__=='__main__':main()
