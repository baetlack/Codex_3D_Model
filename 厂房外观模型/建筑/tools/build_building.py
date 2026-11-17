"""Authoritative building model: same mesh in standalone and assembly viewers.
Coordinates axis-local mm: east +X, north +Y, up +Z; local Z0=EL100.
Source DXF assets are read-only; every new part has a source record.
"""
from pathlib import Path
import json,math,hashlib,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
from dxf_geometry import read_entities,first,number,geometry
ARCH=next((ROOT/'原始资料').glob('*建施*'));STRUCT=next((ROOT/'原始资料').glob('*结构*'))
ORIGINS={1:(4388240.,171772.),2:(4528663.5,167930.4),3:(4684213.,163771.5)}
PARTS=[];RECORDS=[]
def doc(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def save(path,data):
 p=ROOT/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def part(name,kind,color='#aebdc5',label=None):return {'name':name,'kind':kind,'color':color,'vertices':[],'faces':[],'label':label or name}
def merge(dst,src):
 n=len(dst['vertices']);dst['vertices'].extend(src['vertices']);dst['faces'].extend([[i+n for i in f] for f in src['faces']]);return dst

def prism(name,x,y,z,w,d,h,kind='structure',color='#aebdc5'):
 p=part(name,kind,color);p['vertices']=[[x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+d,z+h],[x,y+d,z+h]]
 for f in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]:p['faces'] += [[f[0],f[i],f[i+1]] for i in range(1,3)]
 return p

def rod(dst,a,b,width=24,color=None):
 a=np.array(a,float);b=np.array(b,float);v=b-a;l=np.linalg.norm(v)
 if l<.01:return
 v/=l;u=np.cross(v,[0,0,1]) if abs(v[2])<.95 else np.array([1.,0,0]);u/=np.linalg.norm(u);w=np.cross(v,u);r=width/2
 p=part('rod',dst['kind']);p['vertices']=[(q+i*u*r+j*w*r).tolist() for q in [a,b] for i,j in [(-1,-1),(1,-1),(1,1),(-1,1)]]
 for f in [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]]:p['faces'] += [[f[0],f[k],f[k+1]] for k in range(1,3)]
 merge(dst,p)
def shift_rotate(p,x,y,yaw):
 a=math.radians(yaw);c,s=math.cos(a),math.sin(a)
 p['vertices']=[[x+c*u-s*v,y+s*u+c*v,z] for u,v,z in p['vertices']];return p

def entity_rows(path):
 section=''
 for kind,f in read_entities(path):
  if kind=='SECTION':section=first(f,2)
  elif kind=='ENDSEC':section=''
  elif section=='ENTITIES':yield kind,f

def bounds(ps):return[min(x for x,y in ps),min(y for x,y in ps),max(x for x,y in ps),max(y for x,y in ps)]
def rect(x0,y0,x1,y1):return [[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
def interval_at(poly,ym):
 es=[]
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if min(a[1],b[1])<ym<max(a[1],b[1]):es.append((a,b))
 es.sort(key=lambda e:e[0][0]+(ym-e[0][1])*(e[1][0]-e[0][0])/(e[1][1]-e[0][1]))
 return list(zip(es[::2],es[1::2]))
def edge_x(e,y):
 a,b=e;return a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1])
def floor_mesh(el,holes):
 z=(el-100)*1000;bottom=z-160;p=part('FLOOR-EL'+str(el),'floor','#9baeb9');p.update(el=el,check=False,holes=[h['id'] for h in holes],thickness_status='160mm沿用显示板厚；分区结构厚度另核')
 ys=sorted(set([-325.,72325.]+[round(y,5) for h in holes for x,y in h['polygon'] if -325<y<72325]))
 outer_left=([-325.,-100000.],[-325.,100000.]);outer_right=([44325.,-100000.],[44325.,100000.])
 def face(pts):
  start=len(p['vertices']);p['vertices'].extend(pts)
  for i in range(1,len(pts)-1):p['faces'].append([start,start+i,start+i+1])
 for ya,yb in zip(ys,ys[1:]):
  ym=(ya+yb)/2;blocked=[]
  for h in holes:blocked.extend(interval_at(h['polygon'],ym))
  blocked.sort(key=lambda e:edge_x(e[0],ym));union=[]
  for a,b in blocked:
   if union and edge_x(a,ym)<=edge_x(union[-1][1],ym):
    if edge_x(b,ym)>edge_x(union[-1][1],ym):union[-1]=(union[-1][0],b)
   else:union.append((a,b))
  edge=outer_left
  for left,right in union+[(outer_right,outer_right)]:
   pts=[[max(-325,edge_x(edge,ya)),ya,z],[min(44325,edge_x(left,ya)),ya,z],[min(44325,edge_x(left,yb)),yb,z],[max(-325,edge_x(edge,yb)),yb,z]]
   if (pts[1][0]+pts[2][0]-pts[0][0]-pts[3][0])>1e-4:
    face(pts);face([[x,y,bottom] for x,y,z in pts[::-1]])
   edge=right
 for poly in [rect(-325,-325,44325,72325)]+[h['polygon'] for h in holes]:
  for a,b in zip(poly,poly[1:]+poly[:1]):face([[*a,bottom],[*b,bottom],[*b,z],[*a,z]])
 return p

ROOMS=[
 {'id':'R1-TRANSFORMER','name':'变压器室','floor':1,'bounds':[299.8,7850.4,4824.8,12325.4],'ffl':100,'top':5840,'label_handle':'A3598'},
 {'id':'R1-SWITCHGEAR','name':'配电室','floor':1,'bounds':[299.8,12325.4,4824.8,50950.4],'ffl':300,'top':5840,'label_handle':'A3588'},
 {'id':'R1-MACHINE','name':'机具间','floor':1,'bounds':[299.8,50950.4,4824.8,65000.4],'ffl':300,'top':5840,'label_handle':'A3650'},
 {'id':'R2-CABINET','name':'机柜室','floor':2,'bounds':[39725.0,7650.0,44350.0,36325.0],'ffl':6300,'top':9900,'label_handle':'A3951'},
 {'id':'R2-TOOL','name':'工具间','floor':2,'bounds':[39725.0,36325.0,44350.0,50725.0],'ffl':6000,'top':9900,'label_handle':'A3948'},
 {'id':'R2-SAMPLE','name':'取样仪器间','floor':2,'bounds':[39725.0,50725.0,44350.0,58025.0],'ffl':6000,'top':9900,'label_handle':'A3931'},
]

def stairs(corner,group,x,y,yaw):
 levels=[0,2000,4000,6000,8000,10000,12000]+([14200,16400,18600,20800,23000] if group=='B' else [])
 records=[]
 for j,(z0,z1) in enumerate(zip(levels,levels[1:])):
  # 260 mm tread pitch read in both architectural and structural details.
  # 12 risers per 2.0m flight, 13 per 2.2m upper flight.
  n=12 if z1-z0==2000 else 13;run=(n-1)*260.;near=1600.;far=near+run;forward=j%2==0
  xx=1525 if forward else -25;width=1375
  p=part(f'STAIR-{corner}-FLIGHT-{j+1}','stair','#b5c0c6',f'{corner}楼梯 {z0/1000:g}–{z1/1000:g}m')
  rise=(z1-z0)/n
  for i in range(n-1):
   y0=near+i*260 if forward else far-i*260;y1=y0+260 if forward else y0-260;zt=z0+(i+1)*rise
   low0=z0+i*rise-180;low1=z0+(i+1)*rise-180
   q=part('step','stair');q['vertices']=[[xx,y0,low0],[xx+width,y0,low0],[xx+width,y1,low1],[xx,y1,low1],[xx,y0,zt],[xx+width,y0,zt],[xx+width,y1,zt],[xx,y1,zt]]
   for f in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]:
    q['faces'] += [[f[0],f[k],f[k+1]] if forward else [f[0],f[k+1],f[k]] for k in range(1,3)]
   merge(p,q)
  PARTS.append(shift_rotate(p,x,y,yaw))
  landing_y=far if forward else near-1275
  lp=prism(f'STAIR-{corner}-LANDING-{j+1}',-25,landing_y,z1-180,2925,1275,180,'stair','#bbc5cb');PARTS.append(shift_rotate(lp,x,y,yaw))
  za=z0 if forward else z1;zb=z1 if forward else z0
  rail=part(f'STAIR-{corner}-RAIL-{j+1}','stair','#a0b7bc')
  for edge in [xx+45,xx+width-45]:
   for height in [650,1100]:rod(rail,[edge,near,za+height],[edge,far,zb+height],32)
   for t in np.linspace(0,1,math.ceil(run/105)+1):
    yy=near+run*t;zz=za+(zb-za)*t;progress=t if forward else 1-t;postbase=za if t==0 else zb if t==1 else z0+min(n-1,max(1,math.ceil(progress*(n-1))))*rise;rod(rail,[edge,yy,postbase],[edge,yy,zz+1100],16)
  PARTS.append(shift_rotate(rail,x,y,yaw));records.append({'from_mm':z0,'to_mm':z1,'risers':n,'tread_mm':260,'flight_width_mm':1375,'run_mm':run})
 # First landing and long final landing connect to doors/floor circulation.
 PARTS.append(shift_rotate(prism('STAIR-'+corner+'-ENTRY',-25,325,-160,2925,1275,160,'stair'),x,y,yaw))
 last_far=1600+(12 if group=='B' else 11)*260
 if group=='B':PARTS.append(shift_rotate(prism('STAIR-'+corner+'-ROOF-EXIT',-25,last_far,22840,2925,7525-last_far,160,'stair'),x,y,yaw))
 return {'corner':corner,'group':group,'reaches_m':levels[-1]/1000,'transform':{'x':x,'y':y,'rotation_deg':yaw},'flights':records,'source_arch':['A4575','A4758','A4D0B','A4F2D'],'source_struct':['5139C','52D84'] if group=='A' else ['51D8D','51E4E','54908','549C9']}

def build():
 global PARTS,RECORDS;PARTS=[];RECORDS=[]
 arch=[]
 for kind,f in entity_rows(ARCH):
  if kind in ('LINE','LWPOLYLINE','CIRCLE','INSERT'):
   ps=geometry(kind,f) if kind!='INSERT' else [(number(f,10),number(f,20))]
   if ps:arch.append({'kind':kind,'handle':first(f,5),'layer':first(f,8),'points':ps,'radius':number(f,40),'block':first(f,2)})
 facade=json.loads(subprocess.check_output(['node',str(ROOT/'tools/export_facade.js'),str(ROOT)],text=True));PARTS.extend(facade)
 columns=doc('结构立柱数据.json')['columns']
 for i,c in enumerate(columns):
  if c['width']==400 and c['x']>38000:continue
  PARTS.append(prism('COL-%03d'%i,c['x']-c['width']/2,c['y']-c['depth']/2,0,c['width'],c['depth'],23000))
 # Restore complete frame shown in the original standalone model; sections remain its existing display sizes.
 xs=[0,6000,13000,19000,26000,32000,38000,44000];ys=list(range(0,72001,7200))
 for el in [0,6000,12000,23000]:
  p=part('FRAME-BEAMS-'+str(el),'frame','#b58d5b')
  for yy in ys:merge(p,prism('',0,yy-150,el-450,44000,300,450))
  for xx in xs:merge(p,prism('',xx-150,0,el-450,300,72000,450))
  PARTS.append(p)
 # Exact labelled lifting apertures, kept separate from adjacent lifting areas.
 holes=[]
 ids={2:['383','39A','3B9'],3:['543','547']}
 for floor,handles in ids.items():
  ox,oy=ORIGINS[floor]
  for handle in handles:
   e=next(q for q in arch if q['handle']==handle and q['kind']=='LWPOLYLINE');poly=[[round(x-ox-325,3),round(y-oy-325,3)] for x,y in e['points']];bb=bounds(poly)
   holes.append({'id':f'HOIST-{floor}-{handle}','type':'hoisting','floor':floor,'EL':100+(floor-1)*6,'polygon':poly,'source_handle':handle,'clear_size_mm':[round(bb[2]-bb[0],3),round(bb[3]-bb[1],3)]})
 # Explicitly labelled equipment floor holes in the second floor (outer R3100 / R2600).
 for e in arch:
  if e['kind']=='CIRCLE' and abs(e['radius']-3100)<.1 or e['kind']=='CIRCLE' and abs(e['radius']-2600)<.1:
   cx=sum(x for x,y in e['points'])/len(e['points']);cy=sum(y for x,y in e['points'])/len(e['points'])
   # Circle paths duplicate first point; derive center from opposite extrema.
   bb=bounds(e['points']);cx=(bb[0]+bb[2])/2;cy=(bb[1]+bb[3])/2;ox,oy=ORIGINS[2]
   if ox<cx<ox+44650 and oy<cy<oy+72650:
    x,y=cx-ox-325,cy-oy-325;r=e['radius'];poly=[[x+r*math.cos(i*math.tau/96),y+r*math.sin(i*math.tau/96)] for i in range(96)]
    if not any(h['type']=='equipment' and math.hypot(bounds(h['polygon'])[0]-(x-r),bounds(h['polygon'])[1]-(y-r))<1 for h in holes):holes.append({'id':'EQHOLE-'+e['handle'],'type':'equipment','floor':2,'EL':106,'polygon':poly,'source_handle':e['handle'],'radius_mm':r})
 stair_specs=[('SW','B',-26.39,.43,0),('NE','B',43999.78,72000.44,180),('SE','A',41124.74,.45,0),('NW','A',2874.64,72000.44,180)]
 stair_records=[]
 for corner,group,x,y,yaw in stair_specs:
  stair_records.append(stairs(corner,group,x,y,yaw))
  for floor in ([2,3,4] if group=='B' else [2,3]):
   poly=[]
   for u,v in rect(-25,1600,2900,4720 if group=='B' and floor>=3 else 4460):
    a=math.radians(yaw);poly.append([x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a)])
   holes.append({'id':f'STAIR-HOLE-{corner}-{floor}','type':'stair','floor':floor,'EL':{2:106,3:112,4:123}[floor],'polygon':poly,'source_handle':'楼梯放大平面图/结构详图'})
 # Room partition faces are paired WALL-layer edges, preserving actual door gaps.
 room_records=[]
 for room in ROOMS:
  ox,oy=ORIGINS[room['floor']];x0,y0,x1,y1=room['bounds'];p=part(room['id']+'-WALL','room','#aebdc4',room['name']);edges=[]
  for e in arch:
   if e['kind']!='LINE' or e['layer']!='WALL':continue
   ps=[[x-ox,y-oy] for x,y in e['points']]
   if all(x0-350<x<x1+350 and y0-350<y<y1+350 for x,y in ps):edges.append((e,ps))
  used=[]
  for i,(e,a) in enumerate(edges):
   for f,b in edges[i+1:]:
    for axis in [0,1]:
     other=1-axis
     if abs(a[0][axis]-a[1][axis])>.8 or abs(b[0][axis]-b[1][axis])>.8:continue
     thick=abs(a[0][axis]-b[0][axis]);lo=max(min(q[other] for q in a),min(q[other] for q in b));hi=min(max(q[other] for q in a),max(q[other] for q in b))
     if 195<thick<205 and hi-lo>80:
      base=min(a[0][axis],b[0][axis])-325
      if axis==0:merge(p,prism('',base,lo-325,room['ffl'],thick,hi-lo,room['top']-room['ffl']))
      else:merge(p,prism('',lo-325,base,room['ffl'],hi-lo,thick,room['top']-room['ffl']))
      used.extend([e['handle'],f['handle']])
  # Doorway lintels/closed leaves, using the plan's actual WALL-edge gaps.
  doors={'R2-CABINET':[(39725,7950,200,1100),(39725,34525,200,1500)],'R2-TOOL':[(39725,49325,200,1100)],'R2-SAMPLE':[(40225,57825,1100,200)]}.get(room['id'],[])
  for di,(dx,dy,dw,dd) in enumerate(doors):
   merge(p,prism('',dx-325,dy-325,room['ffl']+2200,dw,dd,room['top']-room['ffl']-2200))
   leaf=prism(room['id']+'-DOOR-'+str(di),dx-325,dy-325,room['ffl'],min(dw,50) if dw==200 else dw,min(dd,50) if dd==200 else dd,2200,'room','#6d8793')
   PARTS.append(leaf)
  PARTS.append(p);b=[x0-325,y0-325,x1-325,y1-325]
  deck=prism(room['id']+'-ROOF',b[0],b[1],room['top']-160,b[2]-b[0],b[3]-b[1],160,'room_roof','#b4c0c7');deck['room_id']=room['id'];
  if room['floor']==2:PARTS.append(deck)
  # Floor plinths reflect explicit +0.100 / +0.300 room levels.
  base=(room['floor']-1)*6000
  if room['ffl']>base:PARTS.append(prism(room['id']+'-PLINTH',b[0],b[1],base,b[2]-b[0],b[3]-b[1],room['ffl']-base,'room','#acbbc2'))
  room_records.append({**room,'bounds_axis_mm':b,'wall_source_handles':sorted(set(used)),'height_basis':'A5B8B/A5B93/A5B9B 顶高3900、470DB 结构9.900m屋面' if room['floor']==2 else 'A5D87/A5DBE 剖面6.000m板层；首层隔墙接二层板底，不另造吊顶'})
 # Correctly limited room columns: not the previous incorrect 23 m full-height thin columns.
 for i,c in enumerate(columns):
  if c['width']==400 and c['x']>38000 and 7200<=c['y']<=58000:
   p=prism('ROOM-COL-%03d'%i,c['x']-200,c['y']-200,5970,400,400,3930,'room_column');p['source']='结构5.970~9.900m柱平面';PARTS.append(p)
 # Stair TZ columns: 300x400 outlines from 5140C/51410/51414/5142D/51431/5146A.
 # Their inside/outside locations follow the corner axes, not the flight rotation.
 for corner,group,x,y,yaw in stair_specs:
  support=part('STAIR-'+corner+'-TZ','stair','#a9bbc6');north=corner in ('NW','NE');east=corner in ('SE','NE');base_y=64800 if north else 0
  mids=[2340,5600] if north else [1200,4460]
  for xx,yy in [(2850,-325),(2850,mids[0]),(2850,mids[1]),(2850,7125),(-325,mids[0]),(-325,mids[1])]:
   world_x=44000-xx-300 if east else xx
   merge(support,prism('',world_x,base_y+yy,0,300,400,12000 if group=='A' else 23000))
  support['source_handles']=['5140C','51410','51414','5142D','51431','5146A'];PARTS.append(support)
 # Hoisting rims and simple metal guards exactly follow the inner aperture rectangles.
 for hole in [h for h in holes if h['type']=='hoisting']:
  x0,y0,x1,y1=bounds(hole['polygon']);z=(hole['EL']-100)*1000;p=part(hole['id']+'-CURB','guard','#b5c0c5')
  for x,y,w,d in [(x0-200,y0,200,y1-y0+200),(x1,y0,200,y1-y0+200),(x0-200,y1,x1-x0+400,200)]:merge(p,prism('',x,y,z,w,d,100))
  PARTS.append(p);rail=part(hole['id']+'-GUARD','guard','#a7bdc0')
  for a,b in [([x0-100,y0],[x0-100,y1+100]),([x1+100,y0],[x1+100,y1+100]),([x0-100,y1+100],[x1+100,y1+100])]:
   for h in [650,1100]:rod(rail,[*a,z+h],[*b,z+h],32)
   for t in np.linspace(0,1,math.ceil(math.dist(a,b)/110)+1):
    q=[a[k]+t*(b[k]-a[k]) for k in range(2)];rod(rail,[*q,z+100],[*q,z+1100],16)
  PARTS.append(rail)
 # Four correctly cut floor plates; roof skin reuses the same apertures.
 for el in [100,106,112,123]:PARTS.append(floor_mesh(el,[h for h in holes if h['EL']==el]))
 roof=floor_mesh(123,[h for h in holes if h['EL']==123]);roof.update(name='ROOF',kind='roof',color='#aebcc4');PARTS.append(roof)
 for i,(x,y,w,d) in enumerate([(3100,-325,41225,300),(44025,-25,300,64500),(-325,72025,41225,300),(-325,7525,300,64500)]):PARTS.append(prism('PARAPET-'+str(i),x,y,23000,w,d,1500,'roof','#aabac3'))
 # Roof stair enclosures have actual FM1522 doors and separated slabs, no opaque solid blocks.
 for corner,x,y,north in [('SW',-325,-325,True),('NE',40900,64475,False)]:
  width,depth=3425,7850;p=part('ROOF-STAIR-'+corner,'roof','#b1bfc6')
  for xx,thick in [(x,300 if north else 200),(x+width-(200 if north else 300),200 if north else 300)]:merge(p,prism('',xx,y,23000,thick,depth,3300))
  solid_y=y if north else y+depth-300;door_y=y+depth-200 if north else y
  merge(p,prism('',x,solid_y,23000,width,300,3300));door0=x+(width-1500)/2
  for xx,ww in [(x,door0-x),(door0+1500,x+width-door0-1500)]:merge(p,prism('',xx,door_y,23000,ww,200,3300))
  merge(p,prism('',door0,door_y,25200,1500,200,1100));merge(p,prism('',x,y,26300,width,depth,600))
  PARTS.append(p);PARTS.append(prism('ROOF-DOOR-'+corner,door0,door_y,23000,1500,50,2200,'roof','#718995'))
 metadata={'version':'1.0-complete-building','units':'mm','EL_at_local_z0':100,'wall_origin_to_axis_mm':[-325,-325],'facade':doc('立面门窗数据.json')['counts'],'stairs':stair_records,'rooms':room_records,'holes':holes,'primary_columns':88,'source_files':{q.name:hashlib.sha256(q.read_bytes()).hexdigest() for q in [ARCH,STRUCT]},'limits':['房间首层隔墙顶按二层板底接合，吊顶未另造','保留旧建筑浏览的300x450示意梁截面；非逐根结构梁配筋模型','160mm为楼板显示厚度，孔位与内轮廓按建施图','未修改设备/桥架模型与就位表']}
 save('building.json',metadata);save('data/建模依据.json',metadata)
 data={'metadata':metadata,'parts':PARTS};(ROOT/'model_data.js').write_text('window.BUILDING_MODEL='+json.dumps(data,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
 print(json.dumps({'parts':len(PARTS),'triangles':sum(len(p['faces']) for p in PARTS),'stairs':len(stair_records),'rooms':len(room_records),'hoisting_holes':sum(h['type']=='hoisting' for h in holes),'equipment_floor_holes':sum(h['type']=='equipment' for h in holes)},ensure_ascii=False))
 return data
if __name__=='__main__':build()
