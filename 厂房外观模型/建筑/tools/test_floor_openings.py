"""Geometry regression for labelled slab openings, using source handles and actual triangles."""
from pathlib import Path
import json,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1]

def contains(point,poly):
 x,y=point;inside=False
 for a,b in zip(poly,poly[1:]+poly[:1]):
  if (a[1]>y)!=(b[1]>y) and x<(b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:inside=not inside
 return inside

def covered(points,triangles):
 a=triangles[:,0,:2];u=triangles[:,1,:2]-a;v=triangles[:,2,:2]-a;den=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=abs(den)>1e-7
 for point in points:
  q=np.array(point)-a;b=np.divide(q[:,0]*v[:,1]-q[:,1]*v[:,0],den,out=np.zeros_like(den),where=valid);c=np.divide(u[:,0]*q[:,1]-u[:,1]*q[:,0],den,out=np.zeros_like(den),where=valid)
  if np.any(valid&(b>=-1e-8)&(c>=-1e-8)&(b+c<=1+1e-8)):return point
 return None

def run():
 model=json.loads((ROOT/'model_data.js').read_text().split('=',1)[1].strip().rstrip(';'));parts={p['name']:p for p in model['parts']};holes=[h for h in model['metadata']['holes'] if h['type']=='floor_opening']
 assert len(holes)==14 and sum(h['floor']==2 for h in holes)==3 and sum(h['floor']==3 for h in holes)==11
 assert sum(h['shape']=='circle' for h in holes)==5
 assert all(h['radius_mm']==250 and h['curb_width_mm']==100 and h['guard_height_mm']==0 for h in holes if h['shape']=='circle')
 assert {h['source_handles'][0] for h in holes if h['shape']=='circle'}=={'5F6','1F9B','600','5FC','1F9F'}
 assert [h['clear_size_mm'] for h in holes if h['floor']==2]==[[4800,2725],[4800,2725],[4800,2825.003]]
 assert all(h['source_handles'] and h['label_handles'] for h in holes)
 sample_count=0
 for hole in holes:
  poly=hole['polygon'];arr=np.array(poly);lo=arr.min(0);hi=arr.max(0);z=(hole['EL']-100)*1000
  points=[[x,y] for x in np.linspace(lo[0]+10,hi[0]-10,9) for y in np.linspace(lo[1]+10,hi[1]-10,9) if contains([x,y],poly)]
  # Sample close to all boundary edges, including the 150/300-mm column notches.
  area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1
  for a,b in zip(poly,poly[1:]+poly[:1]):
   dx,dy=b[0]-a[0],b[1]-a[1];size=math.hypot(dx,dy)
   if size<1:continue
   for t in [.25,.5,.75]:
    q=[a[0]+dx*t-sign*dy*5/size,a[1]+dy*t+sign*dx*5/size]
    if contains(q,poly):points.append(q)
  floor=parts['FLOOR-EL'+str(hole['EL'])];tri=np.array(floor['vertices'])[np.array(floor['faces'])]
  for level in [z,z-160]:
   surface=tri[np.max(abs(tri[:,:,2]-level),axis=1)<1e-4];bad=covered(points,surface);assert bad is None,(hole['id'],'slab filled',level,bad)
  curb=parts[hole['id']+'-CURB'];assert curb['faces'] and min(v[2] for v in curb['vertices'])==z and max(v[2] for v in curb['vertices'])==z+100
  tri_curb=np.array(curb['vertices'])[np.array(curb['faces'])]
  top=tri_curb[np.max(abs(tri_curb[:,:,2]-(z+100)),axis=1)<1e-4]
  assert all(not contains(p[:2].tolist(),poly) for p in top.mean(1)),(hole['id'],'curb inside clear hole')
  if hole['guard_height_mm']:
   rail=parts[hole['id']+'-GUARD'];assert rail['color']=='#a7bdc0' and rail['faces']
  else:assert hole['id']+'-GUARD' not in parts
  sample_count+=len(points)
 assert sum(h['type']=='hoisting' for h in model['metadata']['holes'])==5
 assert sum(h['type']=='equipment' for h in model['metadata']['holes'])==24
 print(f'14处楼板开孔、{sample_count}个孔内/边缘采样的板顶板底真空洞、翻边不侵入净孔、原吊装/设备孔数量及来源句柄通过')
if __name__=='__main__':run()
