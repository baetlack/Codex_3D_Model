"""Build independent, editable cable tray fitting assets. All construction uses mm.
No source DWG or screenshots are modified. See library README for assumptions.
"""
from pathlib import Path
import json,csv,re,math,struct,hashlib,shutil
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

ROOT=Path(__file__).parent
OUT=ROOT/'连接件模型库'
for d in ['glb','obj','parameters','previews','screenshots']: (OUT/d).mkdir(parents=True,exist_ok=True)
MANIFEST=json.loads((ROOT/'fitting_screenshot_manifest.json').read_text(encoding='utf-8'))
OBJS={o['handle']:o for o in json.loads((ROOT/'tray_objects.json').read_text(encoding='utf-8-sig'))}
PATHS={}
for line in (ROOT/'tray_paths.txt').read_text(errors='replace').splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)',line)
 if m: PATHS[m[1]]=[np.array([float(v) for v in m[i].split()]) for i in (2,3)]
# Configurations are indexed by SCREENSHOT filename numbers, not corrected IDs.
# w1/right main, w2/branch, w3/left main. L values copied from parameter dialogs.
CONFIG={}
def add(level,num,kind,**kw): CONFIG[f'L{level}-C{num:02d}']=dict(kind=kind,**kw)
for num in [2,3,4]:add(1,num,'tee',w1=800,w2=200,w3=800,L1=1400,L2=1100,h=200)
add(1,1,'elbow',w1=400,w2=800,L=700,h=200)
add(1,5,'elbow',w1=800,w2=800,L=1100,h=200)
add(1,6,'vertical_down',w1=800,L=500,h=200)
add(1,7,'offset',w1=400,h=200)
add(1,8,'elbow',w1=400,w2=400,L=700,h=200)
add(1,9,'vertical_up',w1=400,L=500,h=200)
add(2,1,'elbow',w1=200,w2=500,L=500,h=200)
for num,w3 in [(2,500),(5,200),(8,500)]:add(2,num,'tee',w1=500,w2=200,w3=w3,L1=1100,L2=800,h=200)
for num,sgn in [(3,1),(4,-1),(6,1),(7,-1),(12,-1),(21,-1)]:add(2,num,'slope',w1=200 if num in (12,21) else 500,h=200,slope_sign=sgn)
for num in [9,14,16]:add(2,num,'vertical_up',w1=500,L=500,h=200)
for num in [10,17]:add(2,num,'vertical_down',w1=500,L=500,h=200)
add(2,11,'elbow',w1=500,w2=500,L=800,h=200)
for num in [13,15]:add(2,num,'tee',w1=500,w2=500,w3=500,L1=1100,L2=800,h=200)
add(2,18,'offset',w1=200,h=200)
for num in [19,20]:add(2,num,'elbow',w1=200,w2=200,L=500,h=200)
add(3,1,'vertical_up',w1=500,L=500,h=200)
add(3,2,'vertical_down',w1=200,L=400,h=200)
add(3,3,'vertical_tee',w1=200,w2=200,w3=200,L1=800,L2=400,h=200)
add(3,4,'vertical_down',w1=200,L=400,h=100)
add(3,5,'vertical_tee',w1=500,w2=200,w3=500,L1=1100,L2=500,h=200)
add(3,6,'tee',w1=500,w2=200,w3=500,L1=1100,L2=800,h=200)
add(3,7,'vertical_down',w1=200,L=400,h=200)
add(3,8,'vertical_up',w1=200,L=400,h=200)
add(3,9,'elbow',w1=200,w2=200,L=500,h=200)
add(3,10,'offset',w1=500,h=200)
add(3,11,'elbow',w1=500,w2=500,L=800,h=200)
add(3,12,'tee',w1=200,w2=300,w3=200,L1=900,L2=600,h=200)
add(3,13,'tee',w1=500,w2=200,w3=500,L1=1100,L2=800,h=200)
add(3,14,'reducer',w1=300,w2=500,L=600,h=200)
add(3,15,'vertical_down',w1=200,L=400,h=200)
add(3,16,'elbow',w1=200,w2=200,L=500,h=100)
add(3,17,'vertical_tee',w1=200,w2=200,w3=200,L1=800,L2=400,h=200)
# v1.1: the user confirmed the updated tee inlet/outlet dimensions.
CONFIG['L2-C02'].update(w1=500,w2=200,w3=500)
CONFIG['L2-C05'].update(w1=500,w2=200,w3=500)

def unit(v):
 v=np.asarray(v,dtype=float);n=np.linalg.norm(v)
 if n<1e-10:raise ValueError('Zero vector')
 return v/n

class Mesh:
 def __init__(self):self.v=[];self.f=[]
 def tri(self,a,b,c):
  if np.linalg.norm(np.cross(np.array(b)-a,np.array(c)-a))<1e-7:return
  n=len(self.v);self.v.extend([list(a),list(b),list(c)]);self.f.append([n,n+1,n+2])
 def quad(self,a,b,c,d):self.tri(a,b,c);self.tri(a,c,d)
 def box(self,points):
  for ids in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]:
   self.quad(*[points[i] for i in ids])

def cross2(a,b):return a[0]*b[1]-a[1]*b[0]
def triangulate(poly):
 p=np.asarray(poly,float);ids=list(range(len(p)));out=[]
 area=sum(cross2(p[i],p[(i+1)%len(p)]) for i in range(len(p)))
 if area<0:ids.reverse()
 for _ in range(len(p)**2):
  if len(ids)==3:out.append(ids);return out
  found=False
  for j in range(len(ids)):
   a,b,c=ids[j-1],ids[j],ids[(j+1)%len(ids)]
   if cross2(p[b]-p[a],p[c]-p[b])<1e-7:continue
   def inside(q):return all(cross2(p[v]-p[u],q-p[u])>=-1e-7 for u,v in [(a,b),(b,c),(c,a)])
   if any(inside(p[k]) for k in ids if k not in (a,b,c)):continue
   out.append([a,b,c]);ids.pop(j);found=True;break
  if not found:raise ValueError('Cannot triangulate footprint')
 raise ValueError('Triangulation limit')

def planar(mesh,poly,open_edges,h,t=2):
 """Solid bottom slab and wall prisms. Join overlaps retained as separate parts."""
 for a,b,c in triangulate(poly):
  pts=[[*poly[i],0] for i in [a,b,c]]
  mesh.tri(*pts[::-1]);mesh.tri(*[[x,y,t] for x,y,z in pts])
 for i in range(len(poly)):
  a=np.array(poly[i],float);b=np.array(poly[(i+1)%len(poly)],float)
  mesh.quad([*a,0],[*b,0],[*b,t],[*a,t])
  if i in open_edges:continue
  inward=unit([-(b-a)[1],(b-a)[0]])*t
  pts=[[*a,t],[*b,t],[*(b+inward),t],[*(a+inward),t]]
  mesh.box(pts+[[p[0],p[1],h] for p in pts])

def port(name,p,normal,w,h,up=(0,0,1)):
 return dict(name=name,position_mm=list(map(float,p)),outward_normal=list(map(float,normal)),width_mm=float(w),height_mm=float(h),section_up=list(map(float,up)))

def sweep(mesh,points,w,h,t=2,end_tangent=None):
 """A U cross section swept in XZ; consistent orientation at vertical turns."""
 pts=[np.array(p,float) for p in points];rings=[]
 section=[(-w/2,0),(w/2,0),(w/2,h),(w/2-t,h),(w/2-t,t),(-w/2+t,t),(-w/2+t,h),(-w/2,h)]
 for i,p in enumerate(pts):
  tangent=unit(pts[1]-p) if i==0 else unit(p-pts[i-1]) if i==len(pts)-1 else unit(unit(p-pts[i-1])+unit(pts[i+1]-p))
  if end_tangent is not None and i in (0,len(pts)-1):tangent=unit(end_tangent)
  lateral=np.array([0.,1.,0.]);up=unit(np.cross(tangent,lateral));scale=1
  if 0<i<len(pts)-1:scale=1/max(.4,np.dot(tangent,unit(pts[i+1]-p)))
  rings.append([p+lateral*a+up*b*scale for a,b in section])
 for r,s in zip(rings,rings[1:]):
  for j in range(8):mesh.quad(r[j],r[(j+1)%8],s[(j+1)%8],s[j])
 # Port rims have only the U material, never cover the cable opening.
 for ring,rev in [(rings[0],True),(rings[-1],False)]:
  for a,b,c in triangulate(section):
   v=[ring[i] for i in (a,b,c)];mesh.tri(*(v[::-1] if rev else v))
 return rings

def inferred_offset(obj):
 a,b=np.array(obj['bounds']);center=(a+b)/2;candidates=[]
 # Plan distance only: the fitting's CAD bounding Z is often flattened.
 for handle,ends in PATHS.items():
  if OBJS[handle]['type']!='TDbECabletry':continue
  for q in ends:
   if all(q[k]>=a[k]-120 and q[k]<=b[k]+120 for k in (0,1)):
    candidates.append((float(np.linalg.norm(q[:2]-center[:2])),q,handle))
 candidates.sort(key=lambda v:v[0])
 pair=None;best=-1
 for j,(_,p,h1) in enumerate(candidates):
  for _,q,h2 in candidates[j+1:]:
   if h1==h2:continue
   dxy=np.linalg.norm(p[:2]-q[:2]);dz=abs(p[2]-q[2])
   if dxy>50 and dz>20 and dxy<2500 and dz<3500:
    score=dz-dxy*.03
    if score>best:pair=(p,q,h1,h2);best=score
 if pair:
  p,q,h1,h2=pair
  return float(np.linalg.norm(p[:2]-q[:2])),float(abs(p[2]-q[2])),[h1,h2],'DWG相邻端点推算，装配时复核'
 ext=b-a
 return max(200,float(max(ext[:2]))),400,[],'截图未标注高差，暂设400mm，待装配复核'

def offset_dimensions(obj):
 pairs={'37E7A':['37E70','37E74'],'37ECC':['37EC8','37EC6'],'37EFD':['37EF8','37EFB']}
 hs=pairs[obj['handle']];center=np.mean(obj['bounds'],axis=0)
 p,q=[min(PATHS[h],key=lambda v:np.linalg.norm(v[:2]-center[:2])) for h in hs]
 delta=np.abs(p-q);axis=int(np.argmax(delta[:2]));run=float(delta[axis]);lateral=float(delta[1-axis]);rise=float(delta[2])
 return run,lateral,rise,hs

def straight_section_sweep(mesh,points,w,h,plane='XZ',t=2):
 """Vertical rim frames for XZ profiles; exact planar miters for XY offsets."""
 pts=[np.array(p,float) for p in points];rings=[]
 section=[(-w/2,0),(w/2,0),(w/2,h),(w/2-t,h),(w/2-t,t),(-w/2+t,t),(-w/2+t,h),(-w/2,h)]
 for i,p in enumerate(pts):
  lateral=np.array([0.,1.,0.]);scale=1.
  if plane=='XY':
   before=unit(pts[i]-pts[i-1]) if i else unit(pts[1]-p)
   after=unit(pts[i+1]-p) if i<len(pts)-1 else before
   tangent=unit(before+after);lateral=unit([-tangent[1],tangent[0],0])
   scale=1/np.dot(tangent,after)
  rings.append([p+lateral*a*scale+np.array([0,0,b]) for a,b in section])
 for a,b in zip(rings,rings[1:]):
  for j in range(8):mesh.quad(a[j],a[(j+1)%8],b[(j+1)%8],b[j])
 for ring,reverse in [(rings[0],True),(rings[-1],False)]:
  for ids in triangulate(section):
   vertices=[ring[i] for i in ids];mesh.tri(*(vertices[::-1] if reverse else vertices))

def funnel_tee(mesh,c):
 """Three-view reconstruction: tray, tapered outlet, then a straight neck.
 X runs along the main tray. C04 additionally narrows toward the -Y edge.
 """
 L,w,h=c['L1'],c['w1'],c['h'];neck_x=w;neck_y=c['w2'];drop=c['L2']-h
 taper=drop/2;join_x=neck_x+2*taper;neck_offset=(neck_y-w)/2
 c.update(aperture_length_mm=join_x,neck_length_mm=neck_x,neck_width_mm=neck_y,
          taper_drop_mm=taper,neck_straight_mm=drop-taper,neck_offset_y_mm=neck_offset,drop_below_floor_mm=drop)
 # Full-length side rails. Only the end strips have a floor: no cap across throat.
 for x0,x1 in [(-L/2,-join_x/2),(join_x/2,L/2)]:
  p=[[x0,-w/2],[x1,-w/2],[x1,w/2],[x0,w/2]]
  planar(mesh,p,{0,1,2,3},2)
 for sy in [-1,1]:
  y=sy*w/2
  mesh.box([[-L/2,y,0],[L/2,y,0],[L/2,y-sy*2,0],[-L/2,y-sy*2,0],
            [-L/2,y,h],[L/2,y,h],[L/2,y-sy*2,h],[-L/2,y-sy*2,h]])
 def ring(l,ww,cy,z,inset=0):
  return [np.array(p,float) for p in [(-l/2+inset,cy-ww/2+inset,z),(l/2-inset,cy-ww/2+inset,z),
    (l/2-inset,cy+ww/2-inset,z),(-l/2+inset,cy+ww/2-inset,z)]]
 dims=[(join_x,w,0,0),(neck_x,neck_y,neck_offset,-taper),(neck_x,neck_y,neck_offset,-drop)]
 outer=[ring(*d) for d in dims];inner=[ring(*d,inset=2) for d in dims]
 for j in range(2):
  for k in range(4):
   nxt=(k+1)%4
   mesh.quad(outer[j][k],outer[j+1][k],outer[j+1][nxt],outer[j][nxt])
   mesh.quad(inner[j][nxt],inner[j+1][nxt],inner[j+1][k],inner[j][k])
 for j in [0,2]:
  for k in range(4):mesh.quad(outer[j][k],outer[j][(k+1)%4],inner[j][(k+1)%4],inner[j][k])
 return [port('A',[-L/2,0,0],[-1,0,0],w,h),port('B',[L/2,0,0],[1,0,0],w,h),
         port('C',[0,neck_offset,-drop],[0,0,-1],neck_y,neck_x,up=(1,0,0))]

def geometry(c,obj):
 m=Mesh();ports=[];kind=c['kind'];w=c['w1'];h=c['h'];notes=[];t=2
 if kind=='elbow':
  wb=c['w2'];L=c['L'];cut=min(200,max(20,(L-wb/2)*.5))
  p=[[-L,-w/2],[wb/2,-w/2],[wb/2,L],[-wb/2,L],[-wb/2,w/2+cut],[-wb/2-cut,w/2],[-L,w/2]]
  planar(m,p,{2,6},h);ports=[port('A',[-L,0,0],[-1,0,0],w,h),port('B',[0,L,0],[0,1,0],wb,h)]
  notes.append('水平弯头内角倒角未单独标注，采用参数化倒角；L按中心线臂长解释，装配需对照CAD轮廓。')
 elif kind=='tee':
  wr=c['w1'];wl=c['w3'];wb=c['w2'];L=c['L1'];extent=c['L2'];half=L/2;top=max(wr,wl)/2;end=extent-top
  cut=min(200,(L-wb)/4,max(20,(end-top)*.6))
  p=[[-half,-wl/2],[0,-(wr+wl)/4],[half,-wr/2],[half,wr/2],[wb/2+cut,top],[wb/2,top+cut],[wb/2,end],[-wb/2,end],[-wb/2,top+cut],[-wb/2-cut,top],[-half,wl/2]]
  planar(m,p,{2,6,10},h)
  ports=[port('A',[-half,0,0],[-1,0,0],wl,h),port('B',[half,0,0],[1,0,0],wr,h),port('C',[0,end,0],[0,1,0],wb,h)]
  notes.append('三口宽度独立；内角倒角为参数化近似。')
 elif kind in ('vertical_up','vertical_down'):
  L=c['L'];sgn=-1 if kind=='vertical_up' else 1
  # CAD dialog names describe the back-plate turn. Path gets an explicit normal.
  pts=[[-L,0,0],[0,0,0],[0,0,sgn*L]];sweep(m,pts,w,h)
  ports=[port('A',pts[0],[-1,0,0],w,h),port('B',pts[-1],[0,0,sgn],w,h,up=(-sgn,0,0))]
  notes.append('L采用局部两臂长度，垂直转向以接口法向为准；最终旋转姿态由装配端口确定。')
 elif kind in ('offset','slope'):
  run,rise,neighbors,source=inferred_offset(obj);c.update(run_mm=round(run,3),rise_mm=round(rise,3),neighbor_handles=neighbors,inference_source=source)
  if obj['handle'] in ('37EAD','37EAF'):
   run=400;rise=400;c.update(run_mm=400,rise_mm=400,geometry_equivalence_group='L2-C04=L2-C07',inference_source='用户确认两件相同；统一400mm水平投影与400mm高差')
  sgn=c.get('slope_sign',1)
  if kind=='offset':
   run,shift,rise,neighbors=offset_dimensions(obj)
   c.update(run_mm=run,rise_mm=rise,lateral_mm=shift,neighbor_handles=neighbors,inference_source='DWG指定相邻段端点差值；端点仅约0.5mm精度')
   source=c['inference_source']
   if rise<1:
    run=1175;shift=-850;first=162;last=163
    pts=[[-run/2,0,0],[-run/2+first,0,0],[run/2-last,shift,0],[run/2,shift,0]]
    straight_section_sweep(m,pts,w,h,plane='XY');ports=[port('A',pts[0],[-1,0,0],w,h),port('B',pts[-1],[1,0,0],w,h)]
    c.update(offset_plane='XY',offset_mm=shift,run_mm=run,lateral_mm=shift,rise_mm=0,straight_in_mm=first,straight_out_mm=last,diagonal_projection_mm=850)
    source='1174.9mm取整1175mm；用户确认偏移方向反向，局部Y偏移=-850mm；斜段45度，端部直段162/163mm'
    c['inference_source']=source
    notes.append('按新增俯视图改为45度平面斜向偏移；所有主尺寸及折点坐标为整毫米。')
   else:
    run=480 if obj['handle']=='37E7A' else 350;rise=200;end=(run-rise)/2
    pts=[[-run/2,0,0],[-run/2+end,0,0],[run/2-end,0,-rise],[run/2,0,-rise]]
    straight_section_sweep(m,pts,w,h);ports=[port('A',pts[0],[-1,0,0],w,h),port('B',pts[-1],[1,0,0],w,h)]
    c.update(offset_plane='XZ',run_mm=run,rise_mm=rise,straight_in_mm=end,straight_out_mm=end,diagonal_projection_mm=rise,diagonal_angle_deg=45)
    notes.append('新增侧视图重建：两端水平直段+中间45度斜降；上下边竖向距离保持槽高。')
  else:
   pts=[[-run/2,0,0],[run/2,0,sgn*rise]];sweep(m,pts,w,h,end_tangent=[1,0,0])
   ports=[port('A',pts[0],[-1,0,0],w,h),port('B',pts[1],[1,0,0],w,h)]
   notes.append('坡段高差/水平投影由DWG邻近端点推算，两端截面保持与水平桥架接口一致。')
  notes.append(source)
 elif kind=='reducer':
  L=c['L'];wb=c['w2'];p=[[0,0],[L,0],[L,wb],[L*.7,wb],[L*.3,w],[0,w]]
  planar(m,p,{1,5},h);ports=[port('A',[0,w/2,0],[-1,0,0],w,h),port('B',[L,wb/2,0],[1,0,0],wb,h)]
  notes.append('偏置变径L=600、300→500mm来自截图；斜边过渡占总长40%，分段位置未标注，待复核。')
 elif kind=='vertical_tee':
  ports=funnel_tee(m,c)
  notes.append('按新增三视图重建为主管槽+收口斜面+短直颈；L2为含主管高度的总高。侧向收口朝-Y侧，与原视图同侧。')
  notes.append('垂直出口为矩形收口，接口的宽/深按实际出口包络记录，不再沿用主管槽高。斜面分段值按三视图比例与已知标称尺寸推定，待DWG叠合确认。')
  if w==200:c['geometry_equivalence_group']='L3-C02=L3-C15'
 else:raise ValueError(kind)
 notes.append('板厚2mm为建模假定；无盖、无孔、无法兰及螺栓。壁板分体相交，未做实体布尔合并。')
 return m,ports,notes

def export_obj(mesh,path,name):
 lines=[f'# {name}; units=m; CAD Z-up; local coordinates','o '+name]
 lines += ['v '+' '.join(f'{x/1000:.7f}' for x in p) for p in mesh.v]
 lines += ['f '+' '.join(str(i+1) for i in f) for f in mesh.f]
 path.write_text('\n'.join(lines)+'\n',encoding='ascii')

def export_glb(mesh,path,name,extras):
 # CAD Z-up -> glTF Y-up is a proper 90-degree rotation about X.
 p=np.array(mesh.v,dtype=np.float32)/1000;p=p[:,[0,2,1]];p[:,2]*=-1
 idx=np.array(mesh.f,dtype=np.uint32).ravel();normals=np.zeros_like(p)
 for a,b,c in mesh.f:
  n=np.cross(p[b]-p[a],p[c]-p[a]);n/=np.linalg.norm(n);normals[[a,b,c]]=n
 blobs=[p.astype('<f4').tobytes(),normals.astype('<f4').tobytes(),idx.astype('<u4').tobytes()]
 binary=b''.join(blobs);offsets=[0,len(blobs[0]),len(blobs[0])+len(blobs[1])]
 g={'asset':{'version':'2.0','generator':'CableTrayFittingLibrary 1.0'},'scene':0,'scenes':[{'nodes':[0]}],
 'nodes':[{'mesh':0,'name':name,'extras':extras}],
 'meshes':[{'name':name,'primitives':[{'attributes':{'POSITION':0,'NORMAL':1},'indices':2,'material':0}]}],
 'materials':[{'name':'galvanized_steel','doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[.48,.67,.75,1],'metallicFactor':.55,'roughnessFactor':.38}}],
 'buffers':[{'byteLength':len(binary)}],
 'bufferViews':[{'buffer':0,'byteOffset':offsets[i],'byteLength':len(b),'target':34963 if i==2 else 34962} for i,b in enumerate(blobs)],
 'accessors':[{'bufferView':0,'componentType':5126,'count':len(p),'type':'VEC3','min':p.min(0).tolist(),'max':p.max(0).tolist()},
 {'bufferView':1,'componentType':5126,'count':len(p),'type':'VEC3'}, {'bufferView':2,'componentType':5125,'count':len(idx),'type':'SCALAR'}]}
 raw=json.dumps(g,ensure_ascii=False,separators=(',',':')).encode();raw+=b' '*((-len(raw))%4);binary+=b'\0'*((-len(binary))%4)
 total=12+8+len(raw)+8+len(binary)
 path.write_bytes(struct.pack('<III',0x46546c67,2,total)+struct.pack('<II',len(raw),0x4e4f534a)+raw+struct.pack('<II',len(binary),0x004e4942)+binary)

def preview(ax,m,ports,title):
 v=np.array(m.v)/1000;faces=[v[f] for f in m.f]
 ax.add_collection3d(Poly3DCollection(faces,facecolor='#8fb7c5',edgecolors='#527080',linewidths=.17,alpha=1))
 for p in ports:
  pos=np.array(p['position_mm'])/1000;ax.scatter(*pos,color='#f0993b',s=9);ax.text(*pos,p['name'],color='#a34f04',fontsize=7)
 lo=v.min(0);hi=v.max(0);center=(lo+hi)/2;size=max(hi-lo)*.57
 ax.set_xlim(center[0]-size,center[0]+size);ax.set_ylim(center[1]-size,center[1]+size);ax.set_zlim(center[2]-size,center[2]+size);ax.set_box_aspect([1,1,1]);ax.view_init(27,-58);ax.set_axis_off();ax.set_title(title,fontsize=9,pad=-2)

catalog=[];renderdata=[];allmeshes=[]
for image_path in (ROOT/'连接件').glob('*.png'):shutil.copy2(image_path,OUT/'screenshots'/image_path.name)
for entry in sorted(MANIFEST,key=lambda e:e['建议对应模型编号']):
 src=entry['文件名编号'];ident=entry['建议对应模型编号'];obj=OBJS[entry['DWG句柄']];c=dict(CONFIG[src]);mesh,ports,notes=geometry(c,obj)
 shutil.copy2(ROOT/'连接件'/entry['截图'],OUT/'screenshots'/entry['截图'])
 view_id='L3C02' if ident=='L3-C15' else ident.replace('-','')
 source_views=[{'label':p.stem,'path':'screenshots/'+p.name,'SHA256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted((ROOT/'连接件').glob(view_id+'-*.png')) if any(s in p.stem for s in ('侧视图','俯视图','正视图'))]
 meta={'id':ident,'source_screenshot_id':src,'source_screenshot':'screenshots/'+entry['截图'],'dwg_handle':obj['handle'],'kind':c['kind'],'shape':entry['形状识别'],
 'units':'mm','coordinate_system':'local right-handed Z-up; GLB stores meters Y-up','parameters':c,'ports':ports,'construction_notes':notes,
 'association_status':'proposed_swap_pending_assembly_check' if src!=ident else 'filename_association_pending_assembly_check',
 'geometry_status':'updated_from_supplemental_views_pending_CAD_overlay' if source_views or ident in ['L2-C02','L2-C04','L2-C05','L2-C07','L3-C15'] else 'parametric_reference_model_pending_CAD_overlay',
 'source_views':source_views,'revision':'1.2' if ident=='L2-C18' else '1.1','source_CAD_bbox_mm':obj['bounds'],'source_screenshot_SHA256':hashlib.sha256((ROOT/'连接件'/entry['截图']).read_bytes()).hexdigest(),
 'files':{'glb':f'glb/{ident}.glb','obj':f'obj/{ident}.obj','parameters':f'parameters/{ident}.json'}}
 meta['mesh']={'vertices':len(mesh.v),'triangles':len(mesh.f),'bbox_mm':[np.min(mesh.v,axis=0).tolist(),np.max(mesh.v,axis=0).tolist()]}
 export_obj(mesh,OUT/meta['files']['obj'],ident);export_glb(mesh,OUT/meta['files']['glb'],ident,{'id':ident,'source':entry['截图'],'status':meta['geometry_status']})
 (OUT/meta['files']['parameters']).write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
 catalog.append(meta);renderdata.append(dict(id=ident,v=np.round(np.array(mesh.v)/1000,6).tolist(),f=mesh.f,ports=ports));allmeshes.append((mesh,ports))
 # Each model gets a standalone, shareable preview too.
 fig=plt.figure(figsize=(5,4));ax=fig.add_subplot(111,projection='3d');preview(ax,mesh,ports,ident+' | '+c['kind']);fig.savefig(OUT/'previews'/f'{ident}.png',dpi=120,bbox_inches='tight');plt.close(fig)

(OUT/'catalog.json').write_text(json.dumps({'version':'1.2-direction-fix','count':len(catalog),'models':catalog},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'viewer_data.js').write_text('window.FITTING_CATALOG='+json.dumps(catalog,ensure_ascii=False)+';\nwindow.FITTING_MESHES='+json.dumps(renderdata,separators=(',',':'))+';',encoding='utf-8')
with (OUT/'模型目录.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(['模型编号','形状','来源截图编号','DWG句柄','接口数','三角面数','状态'])
 for c in catalog:w.writerow([c['id'],c['shape'],c['source_screenshot_id'],c['dwg_handle'],len(c['ports']),c['mesh']['triangles'],c['geometry_status']])
for level in range(1,4):
 indices=[i for i,c in enumerate(catalog) if c['id'].startswith(f'L{level}-')];cols=4;rows=math.ceil(len(indices)/cols)
 fig=plt.figure(figsize=(16,rows*3.2));fig.suptitle(f'Layer {level} | Independent fitting models | reference geometry',fontsize=17)
 for j,i in enumerate(indices):ax=fig.add_subplot(rows,cols,j+1,projection='3d');preview(ax,*allmeshes[i],catalog[i]['id']+' | '+catalog[i]['parameters']['kind'])
 fig.tight_layout(rect=(0,0,1,.96));fig.savefig(OUT/'previews'/f'L{level}_library.png',dpi=130);plt.close(fig)
print('Created',len(catalog),'GLB + OBJ + parameters; types:',dict(Counter(c['kind'] for c in CONFIG.values())))
