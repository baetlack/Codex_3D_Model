"""Reconcile model origins, DXF mirrored INSERTs and upper-plan nozzle directions."""
import math,json,sys
from pathlib import Path
import numpy as np

SPEC={
 'C41B01':(90,1,(0,0),'七处顶口/人孔方位与原图对应；模型相对块定义转90度'),
 'C41B02':(0,-1,(0,-.41335),'六处顶口Y向与图块定义相反；叠加INSERT实际镜像，保留模型尺寸'),
 'C41B03':(0,-1,(0,0),'顶口中心核对：(-514.2,+296.9)对应块内(-514.2,-296.9)'),
 'D41B01':(0,1,(0,0),'七处顶口与块定义一致，应用原图INSERT镜像'),
 'F41B02':(-90,1,(53.6,0),'顶口方位转-90度；槽中心相对块插入点偏X+53.6mm'),
 'F41B05':(-90,1,(53.6,0),'复用F41B02类型；按对应事故槽块中心和方位就位'),
 'F41B06':(-90,1,(53.6,0),'复用F41B02类型；按对应事故槽块中心和方位就位'),
}
PUMPS={'P41B01':'FB3D3','P41B02':'B5E5D','P41B08':'B5E59'}

def rotation(deg):
 a=math.radians(deg);return np.array([[math.cos(a),-math.sin(a)],[math.sin(a),math.cos(a)]])
def matrix(e):return rotation(e.dxf.rotation)@np.diag([e.dxf.xscale,e.dxf.yscale])
def decompose(m):
 # Preserve geographic directions and mirror signs, never stretch an approved mesh.
 return (math.degrees(math.atan2(m[1,0],m[0,0]))%360, bool(np.linalg.det(m)<0))

def review(drawing, origins, placements, assets, root, read):
 root=Path(root);report=[];paths=None
 for p in placements:
  key=p['asset'];e=drawing.entitydb.get(p['source_insert']);old=p['position_mm'][:];oldangle=p['rotation_deg']
  if not e or e.dxftype()!='INSERT':
   report.append({'id':p['id'],'status':'圆轮廓位置可核，朝向缺少特征待核'});continue
  ref=e;floor=origins.index(p['source_floor_origin_mm']);top_evidence=None
  if key in ('D41B02','F41B01','C41B04'):
   name={'D41B02':'水解锅顶','F41B01':'水解料浆缓冲槽顶盖','C41B04':'石墨换热器-顶'}[key]
   choices=[t for t in drawing.modelspace().query('INSERT') if t.dxf.name==name]
   choices=[t for t in choices if abs(t.dxf.insert.x-origins[1][0]-old[0])<300 and abs(t.dxf.insert.y-origins[1][1]-old[1])<300]
   if len(choices)==1:
    ref=choices[0];floor=1
    xy=np.array(list(ref.dxf.insert)[:2])-origins[1];p['position_mm'][:2]=xy.round(4).tolist()
    top_evidence={'handle':ref.dxf.handle,'block':ref.dxf.name,'plan_origin_mm':origins[1],'local_xy_mm':xy.round(4).tolist()}
    phi,mirror,offset,note=(0,1,(0,0),'以EL106顶盖/上部轮廓的真实管口朝向为准，不用EL100底部对称轮廓推断朝向')
   else:
    report.append({'id':p['id'],'status':'未唯一关联顶视图，保留方位待核'});continue
  elif key in SPEC:phi,mirror,offset,note=SPEC[key]
  elif key in PUMPS:
   if paths is None:
    sys.path.insert(0,str(root/'水解设备模型库/tools'))
    from read_equipment_dxf import read_drawing
    paths,_=read_drawing(root/'水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf')
    read('水解设备模型库/tools/read_equipment_dxf.py')
   sample=drawing.entitydb[PUMPS[key]]
   geo=[q for q in paths if q.parent==sample.dxf.handle and not any(t in q.layer for t in ('中心线','点划线'))]
   v=np.array([point for q in geo for point in q.points]);normalizer=rotation(-90 if key in ('P41B02','P41B08') else 0)
   uv=v@normalizer.T;model_world=normalizer.T@np.array([uv[:,0].min(),(uv[:,1].min()+uv[:,1].max())/2])
   native=np.linalg.solve(matrix(sample),model_world-np.array(list(sample.dxf.insert)[:2]))
   xy=np.array(list(e.dxf.insert)[:2])+matrix(e)@native-np.array(origins[0])
   m=matrix(e)@np.linalg.inv(matrix(sample))@normalizer.T
   yaw,flip=decompose(m);p.update(rotation_deg=round(yaw,5)%360,mirror_y=flip)
   p['position_mm'][:2]=xy.round(4).tolist();p['xy_status']='按进液端模型原点与图块轮廓重新对齐'
   p['orientation_status']='泵长轴/进液端已按布置图校正；示意管口细节仍待总图'
   evidence={'sample_handle':sample.dxf.handle,'sample_model_origin_world_mm':model_world.round(4).tolist(),'native_origin_offset_mm':native.round(4).tolist(),'source_block_rotation_deg':float(e.dxf.rotation),'source_block_scale':[e.dxf.xscale,e.dxf.yscale]}
   p['layout_review']=evidence
   report.append({'id':p['id'],'status':'泵原点及长轴已校正','before_xy_mm':old[:2],'after_xy_mm':p['position_mm'][:2],'before_rotation_deg':oldangle,'after_rotation_deg':p['rotation_deg'],'evidence':evidence});continue
  else:
   p['layout_review']={'source_rotation_deg':float(e.dxf.rotation),'source_scale':[e.dxf.xscale,e.dxf.yscale],'status':'原点或类型方向未充分对应，保留待核'}
   report.append({'id':p['id'],'status':'原点或类型方向未充分对应，保留待核','evidence':p['layout_review']});continue
  m=matrix(ref)@rotation(phi)@np.diag([1,mirror]);yaw,flip=decompose(m)
  if top_evidence is None:
   xy=np.array(list(ref.dxf.insert)[:2])+matrix(ref)@np.array(offset)-np.array(origins[floor])
   p['position_mm'][:2]=xy.round(4).tolist()
  p.update(rotation_deg=round(yaw,5)%360,mirror_y=flip,orientation_status='已核对布置图顶视特征及INSERT镜像；未缩放源模型')
  evidence={'reference_handle':ref.dxf.handle,'reference_block':ref.dxf.name,'source_rotation_deg':float(ref.dxf.rotation),'source_scale':[ref.dxf.xscale,ref.dxf.yscale],'model_to_block_rotation_deg':phi,'model_to_block_mirror_y':mirror<0,'native_center_offset_mm':list(offset),'basis':note,'top_plan':top_evidence}
  # Independent witness: compare actual modeled top-port centers to DXF circles.
  parts=json.loads(read(assets[key]['source']).split('=',1)[1].strip().rstrip(';'))
  feature=[]
  for part in parts:
   if part['name'].startswith('接口_顶盖法兰') or part['name']=='接口_人孔座圈':
    v=np.array(part['vertices']);xy=(v[:,:2].max(0)+v[:,:2].min(0))/2
    if np.linalg.norm(xy)>100 and not any(np.linalg.norm(xy-q)<1 for q in feature):feature.append(xy)
  circles=[t for t in drawing.blocks[ref.dxf.name].query('CIRCLE') if 70<t.dxf.radius<650]
  if feature and circles:
   world=np.array([list(t.dxf.center)[:2] for t in circles])@matrix(ref).T+np.array(list(ref.dxf.insert)[:2])
   local_to_world=rotation(p['rotation_deg'])@np.diag([1,-1 if p['mirror_y'] else 1])
   modeled=np.array(feature)@local_to_world.T+np.array(p['position_mm'][:2])+np.array(origins[floor])
   distances=np.linalg.norm(modeled[:,None,:]-world[None,:,:],axis=2).min(1)
   evidence['top_port_witness']={'model_features':len(feature),'matched_within_5mm':int(sum(distances<5)),'nearest_error_mm':distances.round(3).tolist()}
  if evidence.get('top_port_witness',{}).get('matched_within_5mm',1)==0:
   p['orientation_status']='中心/图块方向已记录；类型接口与布置符号不一致，朝向待核'
  p['layout_review']=evidence
  if key=='D41B02' and np.linalg.norm(np.array(old[:2])-np.array(p['position_mm'][:2]))>3:
   p['position_correction']={'source_position_mm':old,'reason':'EL100底部图块偏约200mm；EL106顶视中心与建筑基础相互印证，按顶视中心就位'}
  report.append({'id':p['id'],'status':'位置已核，接口方位待核' if '朝向待核' in p['orientation_status'] else '位置与顶视方位已复核','before_xy_mm':old[:2],'after_xy_mm':p['position_mm'][:2],'before_rotation_deg':oldangle,'after_rotation_deg':p['rotation_deg'],'mirror_y':flip,'evidence':evidence})
 return {'version':'0.2','source':'3.水解工段设备布置图+2026.5.21.dxf','records':report,'reviewed':sum(r['status'] in ('位置与顶视方位已复核','泵原点及长轴已校正') for r in report),'pending':sum('待核' in r['status'] for r in report),'rule':'位置/朝向按真实图块与顶视特征复核；负比例只取镜像与方向，设备净模尺寸不缩放；无法对应的保留待核'}
