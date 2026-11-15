"""User-confirmed contact rules and continuous SE riser for assembly v0.2."""
import math
import numpy as np

def apply_revision(parts,connections,issues,straight_mesh):
 byid={p['id']:p for p in parts};changes=[]
 def translate_fitting(ident,delta):
  p=byid[ident];delta=np.array(delta,float);p['v']+=delta
  for port in p['ports']:port['center_mm']=(np.array(port['center_mm'])+delta).tolist()
  for key in ('translation_mm','CAD_translation_mm'):p['placement'][key]=(np.array(p['placement'][key])+delta).tolist()
  changes.append(dict(part=ident,translation_mm=delta.tolist()))
 def getport(ident,name):return next(p for p in byid[ident]['ports'] if p['name']==name)
 rules={('L3-C03','A'):'bottom',('L3-C17','A'):'bottom',('L3-C04','C'):'side_edges_min_X_min_Y'}
 # Keep horizontal trays at their existing elevation. Lift the larger elbow
 # until its floor coincides; trim the connected vertical segment accordingly.
 for ident,straight in [('L3-C03','L3-S-37C27'),('L3-C17','L3-S-37C21')]:
  port=getport(ident,'A');s=byid[straight];floor=np.array(s['assembled_centerline_mm'][0])[2]-s['height_mm']/2
  fit_floor=port['center_mm'][2]-port['height_mm']/2
  translate_fitting(ident,[0,0,floor-fit_floor])
  for conn in connections:
   if conn.get('fitting')==ident and conn.get('port')=='B':
    byid[conn['straight']]['assembled_centerline_mm'][conn['straight_end']]=getport(ident,'B')['center_mm'].copy()
 # Side-aligned narrow vertical leg: place its two minimum XY exterior edges
 # on the same edges of the C04 throat. Move the lower elbow and its open-ended
 # horizontal branch together so no joint becomes diagonal or disconnected.
 c04=getport('L3-C04','C');fitting=byid['L3-C04'];v=fitting['v'];mask=np.abs(v[:,2]-c04['center_mm'][2])<1e-4
 throat_min=v[mask].min(0);s=byid['L3-S-37C74'];a,b=np.array(s['assembled_centerline_mm']);up=np.array(s['up']);d=(b-a)/np.linalg.norm(b-a);side=np.cross(up,d);side/=np.linalg.norm(side)
 halfspan=np.abs(side)*s['width_mm']/2+np.abs(up)*s['height_mm']/2
 target=np.array(c04['center_mm']);target[:2]=throat_min[:2]+halfspan[:2];delta=target-b
 s['assembled_centerline_mm']=(np.array(s['assembled_centerline_mm'])+delta).tolist()
 translate_fitting('L3-C05',delta)
 lower=byid['L3-S-37C70'];lower['assembled_centerline_mm']=(np.array(lower['assembled_centerline_mm'])+delta).tolist()
 # The two drawings depict consecutive sections of one physical 500x200 riser.
 lower=byid['L2-S-37C18'];upper=byid['L3-S-37C11'];anchor=np.array(lower['assembled_centerline_mm'][1]);upper['up']=lower['up'].copy()
 line=np.array(upper['assembled_centerline_mm']);line[:,:2]=anchor[:2];line[1]=anchor
 end=np.array(byid['L3-S-37C12']['assembled_centerline_mm'][1]);horizontal=end[:2]-anchor[:2];run=float(np.linalg.norm(horizontal))
 # Ensure the mitered 500mm-wide diagonal does not cross its end-rim planes.
 width,height=upper['width_mm'],upper['height_mm'];stub=max(100,math.ceil((width/2*math.tan(math.pi/8)+20)/50)*50)
 rise=run;total_rise=rise+2*stub;line[0,2]=end[2]-total_rise
 if line[0,2]<=anchor[2]+10:raise ValueError('Insufficient height for 45-degree offset')
 upper['assembled_centerline_mm']=line.tolist();start=line[0].copy()
 points=[start,start+np.array([0,0,stub]),end-np.array([0,0,stub]),end]
 # Centered U sections, with a consistent back-plate orientation across both
 # risers. Miter each change of direction in the bisector plane.
 vertices=[];faces=[];reference_up=np.array(upper['up']);t=2
 section=[(-width/2,-height/2),(width/2,-height/2),(width/2,height/2),(width/2-t,height/2),(width/2-t,-height/2+t),(-width/2+t,-height/2+t),(-width/2+t,height/2),(-width/2,height/2)]
 def unit(v):return v/np.linalg.norm(v)
 rings=[]
 for i,p in enumerate(points):
  before=unit(p-points[i-1]) if i else unit(points[1]-p);after=unit(points[i+1]-p) if i<3 else before;tangent=unit(before+after)
  up=unit(reference_up-tangent*np.dot(reference_up,tangent));side=unit(np.cross(up,tangent));miter=1/np.dot(tangent,after)
  rings.append([p+side*x*miter+up*y for x,y in section])
 def tri(a,b,c):
  if np.linalg.norm(np.cross(b-a,c-a))<1e-8:return
  k=len(vertices);vertices.extend([a,b,c]);faces.append([k,k+1,k+2])
 def quad(a,b,c,d):tri(a,b,c);tri(a,c,d)
 for a,b in zip(rings,rings[1:]):
  for j in range(8):quad(a[j],a[(j+1)%8],b[(j+1)%8],b[j])
 for ring in [rings[0],rings[-1]]:
  for ids in [(0,1,4,5),(1,2,3,4),(0,5,6,7)]:quad(*[ring[j] for j in ids])
 new=dict(id='L3-X01',category='fitting',layer=3,kind='computed_45_vertical_offset',label='立管45°乙字弯',handle='USER-L3-X01',
  v=np.array(vertices),f=np.array(faces),source_kind='computed_from_user_confirmed_riser_connection',
  ports=[dict(name='A',center_mm=start.tolist(),normal=[0,0,-1],up=reference_up.tolist(),width_mm=width,height_mm=height),dict(name='B',center_mm=end.tolist(),normal=[0,0,1],up=reference_up.tolist(),width_mm=width,height_mm=height)],
  parameters=dict(width_mm=width,height_mm=height,horizontal_offset_mm=run,offset_X_mm=float(horizontal[0]),offset_Y_mm=float(horizontal[1]),diagonal_rise_mm=rise,straight_end_mm=stub,total_rise_mm=total_rise,diagonal_angle_deg=45,
   path_centerline_mm=[p.tolist() for p in points],construction='Horizontal offset equals diagonal rise exactly; end stubs sized for miter clearance; dimensions in mm'),
  placement=dict(rotation=np.eye(3).tolist(),orientation=np.eye(3).tolist(),mirrored_local_Y=False,translation_mm=[0,0,0],scale=[1,1,1]))
 parts.append(new);byid[new['id']]=new
 connections.extend([dict(fitting='L3-X01',port='A',straight='L3-S-37C11',straight_end=0),dict(fitting='L3-X01',port='B',straight='L3-S-37C12',straight_end=1),
  dict(kind='straight_splice',straight='L2-S-37C18',straight_end=1,other_straight='L3-S-37C11',other_straight_end=1,alignment='continuous_riser')])
 # Rebuild straight geometry after all translations/trims and the 90-degree
 # correction of the upper riser's back-plate orientation.
 for p in parts:
  if p['category']!='straight':continue
  a,b=np.array(p['assembled_centerline_mm']);p['length_mm']=float(np.linalg.norm(b-a));p['v'],p['f']=straight_mesh(a,b,p['width_mm'],p['height_mm'],np.array(p['up']))
  p['links']=[]
 for conn in connections:
  if conn.get('kind')=='straight_splice':
   a=byid[conn['straight']];b=byid[conn['other_straight']];pa=np.array(a['assembled_centerline_mm'][conn['straight_end']]);pb=np.array(b['assembled_centerline_mm'][conn['other_straight_end']]);conn.update(gap_mm=float(np.linalg.norm(pa-pb)),contact_mm=pa.tolist(),status='connected')
   for this,other,end0,end1 in [(a,b,conn['straight_end'],conn['other_straight_end']),(b,a,conn['other_straight_end'],conn['straight_end'])]:this['links'].append(dict(end=end0,other_straight=other['id'],other_end=end1,kind='straight_splice'))
   continue
  a=getport(conn['fitting'],conn['port']);pa=np.array(a['center_mm']);alignment=rules.get((conn['fitting'],conn['port']),'center')
  if 'straight' in conn:
   s=byid[conn['straight']];pb=np.array(s['assembled_centerline_mm'][conn['straight_end']]);qa,qb=pa.copy(),pb.copy()
   if alignment=='bottom':qa-=np.array(a['up'])*a['height_mm']/2;qb-=np.array(s['up'])*s['height_mm']/2
   elif alignment.startswith('side_edges'):
    d=unit(np.array(s['assembled_centerline_mm'][1])-s['assembled_centerline_mm'][0]);side=unit(np.cross(s['up'],d));hs=np.abs(side)*s['width_mm']/2+np.abs(s['up'])*s['height_mm']/2
    qa[:2]=throat_min[:2];qb[:2]-=hs[:2]
   mismatch=a['width_mm']!=s['width_mm'] or a['height_mm']!=s['height_mm']
   direction=unit(np.array(s['assembled_centerline_mm'][1])-s['assembled_centerline_mm'][0]);expected=direction if conn['straight_end']==0 else -direction
   conn.update(alignment=alignment,contact_on_fitting_mm=qa.tolist(),contact_on_straight_mm=qb.tolist(),gap_mm=float(np.linalg.norm(qa-qb)),center_gap_mm=float(np.linalg.norm(pa-pb)),
    fitting_section_mm=[a['width_mm'],a['height_mm']],straight_section_mm=[s['width_mm'],s['height_mm']],section_mismatch=mismatch,accepted_alignment=alignment!='center',normal_error_deg=float(np.degrees(np.arccos(np.clip(np.dot(a['normal'],expected),-1,1)))) ,status='connected')
   s['links'].append(dict(end=conn['straight_end'],fitting=conn['fitting'],port=conn['port'],alignment=alignment))
  else:
   b=getport(conn['other_fitting'],conn['other_port']);conn.update(gap_mm=float(np.linalg.norm(pa-b['center_mm'])),alignment='center',status='connected')
 issues[:]=[i for i in issues if (i.get('fitting'),i.get('port')) not in rules]
 return dict(version='0.2',geographic_axes=dict(east='+X',north='+Y',up='+Z'),default_camera=dict(view='southeast',yaw_deg=-45,elevation_deg=35,roll_deg=0,elevation_limits_deg=[0,90]),
  accepted_alignment_rules=[dict(fitting=k[0],port=k[1],alignment=v) for k,v in rules.items()],riser_splice=dict(lower='L2-S-37C18',upper='L3-S-37C11',at_mm=anchor.tolist(),up=upper['up']),
  new_offset=new['parameters'],fitting_translations=changes)
