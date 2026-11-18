"""Reproducible 1.0 -> 2.0 column-contact rectification, without altering approved assets.
Build from the immutable snapshot; solve rigid XY fitting movements and parallel straight
lengths together, respecting port offsets, the continuous riser and the 10 mm minimum.
"""
from pathlib import Path
import sys, json, copy, hashlib, csv, shutil, argparse
import numpy as np
from scipy.linalg import null_space
from scipy.optimize import minimize, LinearConstraint, linprog
import tray_mesh_exports as mesh

PROJECT=Path(__file__).resolve().parents[2]
REPO=PROJECT.parent
sys.path.insert(0,str(REPO/'水解总装工程/tools'))
import check_assembly as ck
import audit_bridge_columns as audit
BASE=PROJECT/'版本/1.0/models/整体'
NUMERIC_GUARD_MM=.002  # below the 0.1 mm contact tolerance, not an installation clearance

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):
 path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def frozen_check():
 archive=PROJECT/'版本/1.0';manifest=json.loads((archive/'冻结清单.json').read_text())
 for name,digest in manifest['files'].items():assert sha(archive/name)==digest, '1.0 changed: '+name
 return manifest

class Rectification:
 def __init__(self):
  frozen_check()
  self.data=json.loads((BASE/'assembly.json').read_text());self.parts=self.data['parts']
  self.ix={p['id']:i for i,p in enumerate(self.parts)};self.n=2*len(self.parts)
  geo=ck.script(BASE/'viewer_data.js','GEOMETRY')
  allv=np.array([[float(x)*1000 for x in line.split()[1:]] for line in (BASE/'models/三层桥架.obj').read_text().splitlines() if line.startswith('v ')])
  self.vertices={};self.faces={};cursor=0
  for g in geo:
   self.vertices[g['id']]=allv[cursor:cursor+len(g['v'])];self.faces[g['id']]=np.array(g['f']);cursor+=len(g['v'])
  assert cursor==len(allv)
  _,self.columns=audit.load();self.owners={};eq=[];self.ineq=[];self.bounds=[]
  def row(a,b,v):
   r=np.zeros(self.n);r[self.ix[a]*2:self.ix[a]*2+2]+=v;r[self.ix[b]*2:self.ix[b]*2+2]-=v;return r
  for p in self.parts:
   if p['category']!='straight':continue
   ident=p['id'];owners=[ident,ident]
   for link in p['links']:
    if 'fitting' in link:owners[link['end']]=link['fitting']
   self.owners[ident]=owners;a,b=np.array(p['assembled_centerline_mm']);d=mesh.unit(b-a)
   normals=list(np.eye(2)) if abs(d[2])>.01 else [np.array([-d[1],d[0]])]
   for normal in normals:
    for owner in owners:eq.append(row(ident,owner,normal))
   self.ineq.append(row(owners[1],owners[0],d[:2]));self.bounds.append(10-np.linalg.norm(b-a))
  for c in self.data['connections']:
   if 'other_fitting' in c:
    for normal in np.eye(2):eq.append(row(c['fitting'],c['other_fitting'],normal))
   if c.get('kind')=='straight_splice':
    a=self.owners[c['straight']][c['straight_end']];b=self.owners[c['other_straight']][c['other_straight_end']]
    for normal in np.eye(2):eq.append(row(a,b,normal))
  self.z=null_space(np.array(eq),rcond=1e-10)
  weights=np.repeat([1 if p['category']=='fitting' else .1 for p in self.parts],2)
  self.h=self.z.T@(weights[:,None]*self.z)

 def delta(self,x,ident):return np.r_[x[self.ix[ident]*2:self.ix[ident]*2+2],0]

 def rebuild(self,x):
  parts=copy.deepcopy(self.parts);bridges=[]
  for p in parts:
   ident=p['id'];delta=self.delta(x,ident)
   if p['category']=='fitting':
    v=self.vertices[ident]+delta;faces=self.faces[ident]
    for port in p['ports']:port['center_mm']=(np.array(port['center_mm'])+delta).tolist()
    for key in ['translation_mm','CAD_translation_mm']:
     if key in p.get('placement',{}):p['placement'][key]=(np.array(p['placement'][key])+delta).tolist()
    if 'parameters' in p and 'path_centerline_mm' in p['parameters']:
     p['parameters']['path_centerline_mm']=(np.array(p['parameters']['path_centerline_mm'])+delta).tolist()
   else:
    line=np.array(p['assembled_centerline_mm'])+np.array([self.delta(x,o) for o in self.owners[ident]])
    p['assembled_centerline_mm']=line.tolist();p['length_mm']=float(np.linalg.norm(line[1]-line[0]))
    v,faces=mesh.straight_mesh(*line,p['width_mm'],p['height_mm'],np.array(p['up']))
   p['v']=v;p['f']=faces;p['bbox_mm']=[v.min(0).tolist(),v.max(0).tolist()];p['triangles']=len(faces)
   bridges.append(ck.object_mesh(ident,'bridge',v[faces]))
  return parts,bridges

 def penetrations(self,bridges):
  hits=[]
  for b in bridges:
   for c in self.columns:
    if np.any(np.minimum(b['high'],c['high'])-np.maximum(b['low'],c['low'])<=.1):continue
    if ck.column_penetration(b,c,.1):hits.append((b,c))
  return hits

 def solve(self):
  constraints={};x=np.zeros(self.n);history=[]
  for iteration in range(20):
   _,bridges=self.rebuild(x);hits=self.penetrations(bridges)
   history.append({'iteration':iteration,'penetration_pairs':len(hits)})
   print('Column rectification',history[-1],flush=True)
   if not hits:
    return x,history,[{'bridge':k[0],'column':k[1],'direction':k[2],'bound_mm':v[1]} for k,v in constraints.items()]
   for b,c in hits:
    ident=b['id'];p=self.parts[self.ix[ident]];options=audit.translations(b,c)
    if p['kind']=='horizontal_straight':
     d=np.diff(np.array(p['assembled_centerline_mm']),axis=0)[0];axis=0 if abs(d[1])>abs(d[0]) else 1
     options={k:v for k,v in options.items() if k.startswith('XY'[axis])}
    # The nearest X+ exit of these south-row elbows makes the connected north
    # run EC8 enter COL-084/093. Y- clears the complete route without new elbows.
    direction='Y-' if ident in ['L2-C02','L2-C08'] else min(options,key=options.get)
    axis='XY'.index(direction[0]);sign=1 if direction[1]=='+' else -1
    row=np.zeros(self.n);row[self.ix[ident]*2+axis]=sign
    limit=float(row@x+options[direction]+NUMERIC_GUARD_MM);key=(ident,c['id'],direction);old=constraints.get(key)
    constraints[key]=(row,max(limit,old[1] if old else -np.inf))
   a=np.array(self.ineq+[v[0] for v in constraints.values()])@self.z
   low=np.array(self.bounds+[v[1] for v in constraints.values()])
   feasible=linprog(np.zeros(self.z.shape[1]),A_ub=-a,b_ub=-low,bounds=[(None,None)]*self.z.shape[1],method='highs')
   assert feasible.success,'Contact constraints infeasible; route review required: '+feasible.message
   result=minimize(lambda y:.5*y@self.h@y,self.z.T@x,jac=lambda y:self.h@y,method='SLSQP',constraints=[LinearConstraint(a,low,np.inf)],options={'maxiter':500,'ftol':1e-8})
   assert np.min(a@result.x-low)>-.0001,result.message
   x=self.z@result.x
  raise RuntimeError('Rectification did not converge')

 def other_collisions(self,bridges):
  obstacles=[];closed={}
  for p in ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
   if p['kind']!='frame':continue
   for i in range(len(p['vertices'])//8):
    off=i*8;faces=[[j-off for j in f] for f in p['faces'] if all(off<=j<off+8 for j in f)]
    assert len(faces)==12
    obstacles.append(ck.object_mesh(p['name']+'-'+str(i+1),'beam',ck.tri([{'vertices':p['vertices'][off:off+8],'faces':faces}])))
  cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text())
  for p in cfg['equipment']:
   pp=ck.script(REPO/cfg['assets'][p['asset']]['source'],'MODEL_PARTS')
   obstacles.append(ck.object_mesh(p['id'],'equipment',ck.tri(pp,p['position_mm'],p['rotation_deg'],mirror_y=p.get('mirror_y',False))))
   closed[p['id']]=ck.closed_components(pp,p['position_mm'],p['rotation_deg'],p.get('mirror_y',False))
  hits=[]
  for i,a in enumerate(bridges):
   for b in bridges[i+1:]+obstacles:
    if np.any(np.minimum(a['high'],b['high'])-np.maximum(a['low'],b['low'])<=.1):continue
    proof=ck.column_penetration(a,b,.1) if b['kind']=='beam' else ck.surface(a,b)
    if proof is not None or any(ck.inside(a['t'][0,0],t) for t in closed.get(b['id'],[])):hits.append((a['id'],b['id'],b['kind']))
  return hits,{'beams':sum(p['kind']=='beam' for p in obstacles),'placed_equipment':len(cfg['equipment']),'unplaced_equipment_excluded':len(cfg['unplaced'])}

 def build(self,out):
  html=(BASE/'index.html').read_text().replace('整体装配预览 v0.2','桥架 2.0 · 柱面接触整改')
  html='\n'.join(line.rstrip() for line in html.splitlines())+'\n'
  (out/'index.html').write_text(html,encoding='utf-8')
  x,history,constraints=self.solve();parts,bridges=self.rebuild(x)
  _,oldbridges=self.rebuild(np.zeros(self.n));before,scope=self.other_collisions(oldbridges);after,_=self.other_collisions(bridges)
  assert not set(after)-set(before),('New geometry pairs',set(after)-set(before))
  d=copy.deepcopy(self.data);d['version']='2.0-column-contact';d['baseline_version']='1.0'
  d['placement_policy']='建筑柱位与截面固定；连接件仅XY刚性平移；直段保持原方向、截面、标高及端口对齐规则后调整长度。0.1mm接触容差；0.002mm数值保护非安装净距。'
  byid={p['id']:p for p in parts}
  for conn in d['connections']:
   ident=conn.get('fitting') or self.owners[conn['straight']][conn['straight_end']]
   delta=self.delta(x,ident)
   for key in ['contact_on_fitting_mm','contact_on_straight_mm','contact_mm']:
    if key in conn:conn[key]=(np.array(conn[key])+delta).tolist()
   if 'straight' in conn and 'fitting' in conn:
    p=byid[conn['straight']];line=np.array(p['assembled_centerline_mm']);end=conn['straight_end'];direction=mesh.unit(line[1-end]-line[end]);port=next(p for p in byid[conn['fitting']]['ports'] if p['name']==conn['port'])
    conn['normal_error_deg']=float(np.degrees(np.arccos(np.clip(np.dot(direction,port['normal']),-1,1))))
    assert conn['normal_error_deg']<.2
  d['parts']=[{k:v for k,v in p.items() if k not in ['v','f']} for p in parts]
  mesh.LAYERS={int(k):v for k,v in d['layers'].items()}
  for i in range(4):
   selected=parts if i==0 else [p for p in parts if p['layer']==i];name='三层桥架' if i==0 else f'L{i}_桥架'
   mesh.export_obj(selected,out/'models'/f'{name}.obj');mesh.export_glb(selected,out/'models'/f'{name}.glb')
  custom=[p for p in parts if p['id']=='L3-X01'];mesh.export_obj(custom,out/'models/L3-X01_45度乙字弯.obj');mesh.export_glb(custom,out/'models/L3-X01_45度乙字弯.glb');save(out/'models/L3-X01_参数.json',custom[0]['parameters'])
  save(out/'assembly.json',d)
  display=[{'id':p['id'],'layer':p['layer'],'category':p['category'],'v':np.round(p['v']/1000,6).tolist(),'f':p['f'].tolist()} for p in parts]
  (out/'viewer_data.js').write_text('window.ASSEMBLY='+json.dumps(d,ensure_ascii=False)+';\nwindow.GEOMETRY='+json.dumps(display,separators=(',',':'))+';',encoding='utf-8')
  changes=[]
  for old,new in zip(self.parts,parts):
   ident=old['id'];change={'id':ident,'layer':old['layer'],'category':old['category'],'label':old['label'],'reference_translation_mm':self.delta(x,ident).tolist()}
   if old['category']=='fitting':change['translation_mm']=self.delta(x,ident).tolist();change['moved']=bool(np.linalg.norm(self.delta(x,ident))>.01)
   else:
    shift=np.array(new['assembled_centerline_mm'])-np.array(old['assembled_centerline_mm']);change.update(endpoint_displacements_mm=shift.tolist(),old_length_mm=old['length_mm'],new_length_mm=new['length_mm'],length_change_mm=new['length_mm']-old['length_mm'],moved=bool(np.max(np.abs(shift))>.01))
   changes.append(change)
  report={'version':'2.0','baseline':'1.0','units':'mm','columns':len(self.columns),'bridge_parts':len(parts),'before_penetrations':history[0]['penetration_pairs'],'after_penetrations':history[-1]['penetration_pairs'],'contact_tolerance_mm':.1,'numeric_guard_mm':NUMERIC_GUARD_MM,'solver_history':history,'constraints':constraints,'changes':changes,
    'changed_fittings':sum(p['moved'] and p['category']=='fitting' for p in changes),'changed_straights':sum(p['moved'] and p['category']=='straight' for p in changes),'max_fitting_translation_mm':max(np.linalg.norm(p['translation_mm']) for p in changes if p['category']=='fitting'),
    'other_collision_scope':scope,'other_geometry_pairs_before':before,'other_geometry_pairs_after':after,'new_other_geometry_pairs':[],'unchanged':['建筑柱位、柱截面及全部建筑网格','设备源网格和全部就位参数','连接件库形状、朝向、截面、标高','桥架数量、拓扑及原有3处特殊端口对齐规则'],
    'routing_note':'L2-C02/C08沿Y-整改；若只取最近X+方向，会使相连L2-S-37EC8新增穿入COL-084/093。长直段按沿线最不利柱外轮廓统一避让，较小截面处允许留缝。',
    'basis_sha256':{'厂房外观模型/建筑/model_data.js':sha(REPO/'厂房外观模型/建筑/model_data.js'),'水解桥架工程/版本/1.0/冻结清单.json':sha(PROJECT/'版本/1.0/冻结清单.json')},
    'limits':['按当前建筑柱网和截面校核；上部柱截面沿用现有模型，仍待原结构图逐段复核。','不检查检修空间；几何校核不代替施工确认。','桥架相接端部三角面接触仍保留，不把正常接口判作新增冲突。']}
  save(out/'reports/2.0整改核对.json',report)
  with (out/'reports/2.0构件变更.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.writer(f);w.writerow(['编号','类别','是否变化>0.01mm','参考X位移mm','参考Y位移mm','Z位移mm','原长mm','新长mm','长度变化mm','端点位移mm'])
   for p in changes:w.writerow([p['id'],p['category'],p['moved'],*p['reference_translation_mm'],p.get('old_length_mm',''),p.get('new_length_mm',''),p.get('length_change_mm',''),json.dumps(p.get('endpoint_displacements_mm',[]))])
  with (out/'reports/接口核对.csv').open('w',encoding='utf-8-sig',newline='') as f:
   keys=sorted({k for c in d['connections'] for k in c});w=csv.DictWriter(f,fieldnames=keys);w.writeheader();w.writerows(d['connections'])
  save(out/'reports/endpoint_adjustments.json',{'baseline_CAD_adjustments_project_relative':'版本/1.0/models/整体/reports/endpoint_adjustments.json','revision_2_changes':changes})
  save(out/'reports/summary.json',{k:v for k,v in report.items() if k not in ['constraints','changes']})
  text=f"""# 桥架 2.0 整改记录

1.0 冻结保留；2.0 以当前建筑柱外轮廓为固定约束。112件桥架、120根柱（88主体柱、8房间柱、24楼梯柱），实际穿入由69组降至0组，接触容差0.1mm。

{report['changed_fittings']}件连接件刚性平移，{report['changed_straights']}段直桥架随接口调整；连接件最大平移{report['max_fitting_translation_mm']:.3f}mm。所有Z标高、截面、朝向和48个连接件形状保持。原有底板/侧边对齐及45°乙字弯保留。0.002mm仅为小于接触容差的数值保护。

{report['routing_note']}

检查全部沿线柱，不将每根柱都强行贴合。另对72台已定位设备、76段梁及桥架间真实三角面做前后对比，无新增相交配对；6组既有桥架接口面配对保留。27台待定位设备未纳入。

[逐件位移、直段长度对比 CSV](2.0构件变更.csv) · [约束、迭代与校核 JSON](2.0整改核对.json)

上部柱截面依据仍沿用当前建筑模型；这是模型位置整改，不能替代施工图确认。不检查检修空间。
"""
  (out/'reports/装配说明.md').write_text(text,encoding='utf-8')
  import html
  (out/'reports/装配说明.html').write_text('<!doctype html><meta charset="utf-8"><title>桥架2.0整改核对</title><style>body{max-width:1000px;margin:40px auto;font:16px sans-serif;white-space:pre-wrap;line-height:1.8;background:#101923;color:#dce8ef}a{color:#7cdce6}</style>'+html.escape(text)+'<p><a href="2.0构件变更.csv">下载逐件变更</a> · <a href="2.0整改核对.json">完整校核数据</a></p>',encoding='utf-8')
  # Regenerate the overview from current vertices rather than retaining the old image.
  import matplotlib
  matplotlib.use('Agg')
  import matplotlib.pyplot as plt
  from mpl_toolkits.mplot3d.art3d import Poly3DCollection
  fig=plt.figure(figsize=(16,10))
  for n in [1,2,3,0]:
   ax=fig.add_subplot(2,2,4 if n==0 else n,projection='3d')
   for p in parts:
    if n and p['layer']!=n:continue
    ax.add_collection3d(Poly3DCollection(p['v'][p['f']]/1000,facecolors=mesh.LAYERS[p['layer']]['color'],edgecolors='none'))
   ax.set(xlim=(0,46),ylim=(0,74),zlim=(0,20));ax.set_box_aspect([44,72,28]);ax.view_init(28,-57);ax.set_title('Stacked | v2.0' if n==0 else f'L{n} | EL{mesh.LAYERS[n]["EL"]} | v2.0')
  fig.tight_layout();fig.savefig(out/'previews/三层桥架总览.png',dpi=120);plt.close(fig)
  return report

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=PROJECT/'models/整体');args=parser.parse_args()
 out=args.output
 if not (out/'assembly.json').exists():shutil.copytree(BASE,out,dirs_exist_ok=True)
 result=Rectification().build(out);print(json.dumps({k:result[k] for k in ['before_penetrations','after_penetrations','changed_fittings','changed_straights','max_fitting_translation_mm']},ensure_ascii=False))
if __name__=='__main__':main()
