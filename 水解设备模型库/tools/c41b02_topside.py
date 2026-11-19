"""C41B02 roof/side structures checked against plan circles, sections and the BOM.
Only the roof, its mixer support frame, and external nozzles are authored here.
All Z values are local to the existing support datum. Tank/support/foundation stay fixed.
"""
from pathlib import Path
import math,json,hashlib
import numpy as np
from scipy.spatial import Delaunay
from matplotlib.path import Path as PolygonPath
import ezdxf
from ezdxf import bbox

R=Path(__file__).resolve().parents[2]
DRAWING=R/'水解设备模型库/水解设备图纸/钛液预热槽(C41B02A-E).dxf'
STEEL='#b7c8d0';BODY='#a5b9c3';DARK='#818b90';SEAL='#626f74'
DECK=5175.;M_TOP=DECK+280+30;DRIVE_TOP=7345.
HANDLES={'a/p':'944F','c':'944B','d':'9455','e':'94D2','f':'94C3','n':'94CA'}
K_HANDLES=['9460','945C','9458','9464','9435','9439','9440','9444']

def drawing_measurements():
 d=ezdxf.readfile(DRAWING)
 def bounds(handle):
  b=bbox.extents([d.entitydb[handle]],fast=True);return np.array(b.extmin),np.array(b.extmax)
 lo,hi=bounds('94C7');origin=(lo+hi)/2;scale=5724/(hi[0]-lo[0]);circles={}
 for name,handle in {**HANDLES,**{f'k{i+1}':h for i,h in enumerate(K_HANDLES)},'b1':'94AF','j1':'94AC','central_bj_cover':'94B1'}.items():
  a,b=bounds(handle);xy=((a+b)/2-origin)[:2]*scale
  circles[name]={'handle':handle,'center_xy_mm':xy.round(3).tolist(),'diameter_mm':round(float((b[0]-a[0])*scale),3)}
 return {'drawing_sha256':hashlib.sha256(DRAWING.read_bytes()).hexdigest(),'calibration':{'rim_handle':'94C7','dimension_mm':5724,'page_center_xy':origin[:2].tolist(),'mm_per_page_unit':scale},'circles':circles,
  'explicit_dimensions':{'k_gasket_mm':[1075,940,3],'bj_gasket_mm':[400,350,3],'m_opening_mm':[2900,1020],'m_seat_height_mm':280,'m_top_plate_thickness_mm':30,'n_cover_OD_mm':340,'n_bolt_circle_mm':295,'side_chain_mm':[200,13,200],'g_outer_sleeve_mm':[377,9,200],'h_outer_sleeve_mm':[273,6,200],'h_outer_short_pipe_mm':[159,4.5,200],'g_center_above_bottom_mm':300,'h_center_below_cover_mm':300},
  'measurement_limits':'平面用图上φ5724校准，孔中心和未标法兰外廓属于图面量测；不替代工艺绝对方位或缺失零件详图。'}

class Builder:
 def __init__(self,geo):self.g=geo;self.ports=[];self.trace=drawing_measurements()
 def ring(self,name,xy,z0,z1,ro,ri,color=STEEL):
  self.g.ring(name,z0,z1,ro,ri,color,96);n,c,v,f=self.g.parts[-1];self.g.parts[-1]=(n,c,[(x+xy[0],y+xy[1],z) for x,y,z in v],f)
 def cyl(self,name,xy,z0,z1,r,color=STEEL):
  self.g.cyl(name,z0,z1,r,color,96);n,c,v,f=self.g.parts[-1];self.g.parts[-1]=(n,c,[(x+xy[0],y+xy[1],z) for x,y,z in v],f)
 def plate(self,name,outer,holes,z0,z1,color=STEEL,xy=(0,0),angle=0):
  """Watertight extruded polygon with circular holes, avoiding fake plugged mouths."""
  loops=[np.asarray(outer,float)]+[np.array([[cx+r*math.cos(t),cy+r*math.sin(t)] for t in np.linspace(0,2*math.pi,49)[:-1]]) for cx,cy,r in holes]
  points=np.vstack(loops);tri=Delaunay(points).simplices;centers=points[tri].mean(1)
  keep=PolygonPath(np.asarray(outer)).contains_points(centers,radius=1e-7)
  for cx,cy,r in holes:keep &= np.linalg.norm(centers-[cx,cy],axis=1)>r-1e-8
  tri=tri[keep];v=np.vstack([np.column_stack([points,np.full(len(points),z)]) for z in [z0,z1]]);n=len(points);faces=[]
  for t in tri:
   a=points[t[1]]-points[t[0]];b=points[t[2]]-points[t[0]]
   if a[0]*b[1]-a[1]*b[0]<0:t=t[::-1]
   faces.extend([t[::-1].tolist(),(t+n).tolist()])
  offset=0
  for i,loop in enumerate(loops):
   for j in range(len(loop)):
    a=offset+j;b=offset+(j+1)%len(loop)
    faces.append([a,b,b+n,a+n] if i==0 else [b,a,a+n,b+n])
   offset+=len(loop)
  co,si=math.cos(angle),math.sin(angle);v=np.array([[x*co-y*si+xy[0],x*si+y*co+xy[1],z] for x,y,z in v]);self.g.add(name,color,v.tolist(),faces)
 def vertical(self,label,xy,dn,od,flange,projection):
  face=DECK+projection
  self.ring(f'接口_{label}_接管',xy,DECK-10,face-16,od/2,dn/2)
  self.ring(f'接口_{label}_法兰',xy,face-16,face,flange/2,dn/2)
  self.ports.append({'id':label,'dn':dn,'center_mm':[*xy,face],'normal':[0,0,1],'projection_mm':projection,'flange_OD_mm':flange,'source':self.trace['circles'][label],'status':'DN/外伸按管口表；中心按校准俯视图，未当作工艺绝对方位'})
  return face
 def radial_tube(self,name,angle,z,r0,r1,ro,ri,color=STEEL):
  u=np.array([math.cos(angle),math.sin(angle),0]);side=np.array([-math.sin(angle),math.cos(angle),0]);up=np.array([0,0,1]);v=[];f=[];n=96
  for distance,r in [(r0,ro),(r1,ro),(r0,ri),(r1,ri)]:
   center=u*distance+[0,0,z]
   v.extend((center+side*r*math.cos(a)+up*r*math.sin(a)).tolist() for a in np.linspace(0,2*math.pi,n+1)[:-1])
  for i in range(n):j=(i+1)%n;f.extend([[i,j,n+j,n+i],[2*n+j,2*n+i,3*n+i,3*n+j],[n+i,n+j,3*n+j,3*n+i],[j,i,2*n+i,2*n+j]])
  self.g.add(name,color,v,f)
 def side(self,label,angle,z):
  # Sections specify concentric lined sleeves, not a conical reducer.
  big_od,big_dn,small_od,small_dn,big_flange,small_flange=(377,350,273,250,505,395) if label=='g' else (273,250,159,150,395,285)
  self.radial_tube(f'接口_{label}_大端直套管',angle,z,2730,2950,big_od/2,small_dn/2)
  self.radial_tube(f'接口_{label}_大端法兰',angle,z,2934,2950,big_flange/2,small_dn/2)
  self.radial_tube(f'接口_{label}_连接垫片',angle,z,2950,2953,(big_flange-25)/2,small_dn/2,SEAL)
  self.radial_tube(f'接口_{label}_短接连接法兰',angle,z,2953,2963,big_flange/2,small_dn/2)
  self.radial_tube(f'接口_{label}_外端直短接',angle,z,2963,3163,small_od/2,small_dn/2)
  self.radial_tube(f'接口_{label}_外端法兰',angle,z,3147,3163,small_flange/2,small_dn/2)
  u=[math.cos(angle),math.sin(angle),0];self.ports.append({'id':label,'dn':f'{big_dn}/{small_dn}','center_mm':[u[0]*3163,u[1]*3163,z],'normal':u,'section_chain_mm':[200,13,200],'outer_sleeve_OD_mm':big_od,'outer_short_OD_mm':small_od,'status':'按g/h局部结构拆分大端套管、连接法兰/垫片、外端直短接；未作锥形变径；局部法兰厚度仍为外观量测'})
 def roof(self):
  self.g.cyl('Tank_cover_lid',5163,DECK,2862,BODY,128)
  self.g.ring('Lid_edge_rim',5130,5160,2862,2750,STEEL,128)
  self.g.ring('Lid_gasket',5160,5163,2850,2770,SEAL,128)
  # Raised rectangular m neck: H280, top plate t30. Opening and perimeter read
  # separately; a thin planar outline was not a substitute for this seat.
  phi=math.radians(112.5)
  for label,c,size in [('长边1',(0,-516,DECK+140),(2924,12,280)),('长边2',(0,516,DECK+140),(2924,12,280)),('短边1',(-1456,0,DECK+140),(12,1020,280)),('短边2',(1456,0,DECK+140),(12,1020,280))]:
   self.g.box('盖面_m_高座_'+label,c,size,STEEL);n,col,v,f=self.g.parts[-1];co,si=math.cos(phi),math.sin(phi);self.g.parts[-1]=(n,col,[(x*co-y*si,x*si+y*co,z) for x,y,z in v],f)
  half=[(-1532,0),(-200,0)]+[(200*math.cos(t),200*math.sin(t)) for t in np.linspace(math.pi,0,49)[1:]]+[(1532,0),(1532,575),(-1532,575)]
  self.plate('盖面_m_对开顶板1',half,[],M_TOP-30,M_TOP,angle=phi)
  self.plate('盖面_m_对开顶板2',[(-x,-y) for x,y in half],[],M_TOP-30,M_TOP,color='#b1c3cb',angle=phi)
  for i,u in enumerate([-775,775],1):
   self.g.box(f'盖面_m_踏步板{i}',(u,0,M_TOP+1.5),(400,1314,3),DARK);n,c,v,f=self.g.parts[-1];co,si=math.cos(phi),math.sin(phi);self.g.parts[-1]=(n,c,[(x*co-y*si,x*si+y*co,z) for x,y,z in v],f)
  # Visible cover seam is a narrow recess, not overlapping coplanar faces.
  # Four triangular corner stiffeners on the raised seat, aligned with the plan.
  for i,(u,v) in enumerate([(-1100,-522),(1100,-522),(-1100,522),(1100,522)],1):
   sign=1 if v>0 else -1;profile=[(v,DECK),(v+sign*53,DECK),(v,DECK+250)];verts=[]
   for x in [u-6,u+6]:verts.extend([(x,y,z) for y,z in profile])
   faces=[[0,2,1],[3,4,5],[0,1,4,3],[1,2,5,4],[2,0,3,5]];co,si=math.cos(phi),math.sin(phi);self.g.add(f'盖面_m_补强肋{i}',STEEL,[(x*co-y*si,x*si+y*co,z) for x,y,z in verts],faces)
  # The approved motor/drive positions and total +2185 remain. Only the old
  # tapered frame is replaced by the drawing's cylindrical windowed support.
  self.g.ring('06_Frame_foot',M_TOP,M_TOP+30,300,200,STEEL,96)
  bottom=M_TOP+30;top=6465.405
  levels=[bottom,bottom+(top-bottom)/3,bottom+2*(top-bottom)/3,top-30]
  for i,z in enumerate(levels):self.g.ring(f'06_圆筒开窗支架_环{i+1}',z,min(z+30,top),245,180,DARK,96)
  # Axial bars follow the cylinder; three open tiers preserve the side view.
  for i in range(4):
   angle=math.radians(45+i*90);cx,cy=212.5*math.cos(angle),212.5*math.sin(angle)
   self.g.box(f'06_圆筒开窗支架_立肋{i+1}',(cx,cy,(bottom+top)/2),(48,48,top-bottom),DARK)
  # Eight k covers on phi4200. Outer gasket/plate phi1075 is explicit in BOM15.
  for i in range(8):
   a=math.radians(22.5+45*i);rad=np.array([math.cos(a),math.sin(a)]);tangent=np.array([-math.sin(a),math.cos(a)]);xy=rad*2100
   face=DECK+150;k_top=face+3+20
   self.ring(f'接口_k{i+1}_DN800安装口',xy,DECK,face-12,485,470)
   self.ring(f'接口_k{i+1}_下法兰',xy,face-12,face,537.5,470)
   self.ring(f'接口_k{i+1}_垫片1075_940',xy,face,face+3,537.5,470,SEAL)
   self.ring(f'接口_k{i+1}_盘管检修盖',xy,face+3,k_top,537.5,175)
   self.ring(f'接口_k{i+1}_共座法兰',xy,k_top,k_top+12,230,175)
   self.ring(f'接口_k{i+1}_共座垫片400_350',xy,k_top+12,k_top+15,200,175,SEAL)
   outer=[(230*math.cos(t),230*math.sin(t)) for t in np.linspace(0,2*math.pi,97)[:-1]]
   # b/j on the tangent, 250 mm apart: directly measured from 94AF/94AC.
   self.plate(f'接口_k{i+1}_双管共盖板',outer,[(0,125,24),(0,-125,24)],k_top+15,k_top+27,xy=xy,angle=a)
   self.ports.append({'id':f'k{i+1}','dn':800,'center_mm':[*xy.tolist(),face],'normal':[0,0,1],'cover_OD_mm':1075,'gasket_mm':[1075,940,3],'cover_top_z_mm':k_top,'pitch_circle_mm':4200,'angle_deg':22.5+45*i,'source':self.trace['circles'][f'k{i+1}'],'status':'孔位与法兰/垫片按总图和明细表；局部未标板厚保留量测性质'})
   for label,sign in [('b',1),('j',-1)]:
    p=xy+tangent*sign*125;z0=k_top+27;z1=z0+150
    self.ring(f'接口_{label}{i+1}_DN40接管',p,z0-12,z1-16,24,20)
    self.ring(f'接口_{label}{i+1}_法兰',p,z1-16,z1,75,20)
    self.ports.append({'id':f'{label}{i+1}','dn':40,'center_mm':[*p.tolist(),z1],'normal':[0,0,1],'projection_mm':150,'pair_spacing_mm':250,'pair_direction':'与φ4200圆相切','height_above_k_cover_mm':177,'status':'管口表DN40/150；共盖、切向位置和177高差参照主视及俯视'})
  # c,d,e,f,n measured independently instead of snapping every small nozzle to
  # phi4800. f is on phi4200 and a/p is ~49.74 degrees, not 45 degrees.
  for label,dn,od,flange,projection in [('c',150,159,265,150),('d',200,219,320,150),('e',65,76,185,100),('f',80,89,200,100),('n',200,219,340,150)]:
   xy=self.trace['circles'][label]['center_xy_mm'];face=self.vertical(label,xy,dn,od,flange,projection)
   if label in ['d','n']:
    self.ring(f'接口_{label}_密封垫',xy,face,face+3,(flange-20)/2,dn/2,SEAL)
    self.cyl('接口_d_带柄取样盖' if label=='d' else '接口_n_PP盲板',xy,face+3,face+19,flange/2,DARK if label=='n' else STEEL)
    if label=='d':self.ring('接口_d_取样盖竖柄',xy,face+19,face+169,14,10,DARK)
    else:
     for i in range(8):
      t=i*math.pi/4;p=np.array(xy)+147.5*np.array([math.cos(t),math.sin(t)]);self.cyl(f'接口_n_螺栓{i+1}',p,face+19,face+31,16,DARK)
  xy=self.trace['circles']['a/p']['center_xy_mm']
  self.ring('接口_p_DN250套管',xy,DECK,DECK+150-16,136.5,125)
  self.ring('接口_p_法兰375',xy,DECK+150-16,DECK+150,187.5,125)
  self.ring('接口_a_DN200插入管',xy,DECK-200,DECK+300-16,109.5,100)
  self.ring('接口_a_法兰340',xy,DECK+300-16,DECK+300,170,100)
  self.ports.extend([{'id':'p','dn':250,'coaxial_with':'a','center_mm':[*xy,DECK+150],'normal':[0,0,1],'flange_OD_mm':375,'source':self.trace['circles']['a/p'],'status':'按a,p共轴结构及管口表，套管与插入管分别表示'}, {'id':'a','dn':200,'coaxial_with':'p','center_mm':[*xy,DECK+300],'normal':[0,0,1],'flange_OD_mm':340,'source':self.trace['circles']['a/p'],'status':'插入管内伸与上下层法兰按主视构造；详图未提供部分不作为制造尺寸'}])
  self.side('g',0,460);self.side('h',math.pi,4860)
  return self.ports,self.trace

def add_topside(geo):return Builder(geo).roof()
