from pathlib import Path
import json,math,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parents[1]
def model():return json.loads((ROOT/'model_data.js').read_text().split('=',1)[1].strip().rstrip(';'))
def inside_triangle(p,t):
 a,b,c=t[:,:2];den=np.cross(b-a,c-a)
 if abs(den)<1e-7:return False
 v=np.cross(p-a,c-a)/den;w=np.cross(b-a,p-a)/den
 return v>=-1e-8 and w>=-1e-8 and v+w<=1+1e-8

def run():
 d=model();m=d['metadata'];parts=d['parts'];assert m['facade']=={'door':13,'window':133},m['facade']
 assert len([p for p in parts if p['kind']=='structure'])==88
 assert all(max(v[2] for v in p['vertices'])==9900 for p in parts if p['kind']=='room_column')
 assert {x['name'] for x in m['rooms']}=={'变压器室','配电室','机具间','机柜室','工具间','取样仪器间'}
 assert all(r['wall_source_handles'] for r in m['rooms'])
 assert {x['corner']:x['reaches_m'] for x in m['stairs']}=={'SW':23,'NE':23,'SE':12,'NW':12}
 assert all(x['tread_mm']==260 for s in m['stairs'] for x in s['flights'])
 holes=[h for h in m['holes'] if h['type']=='hoisting'];assert len(holes)==5
 assert sum(h['floor']==2 for h in holes)==3 and sum(h['floor']==3 for h in holes)==2
 for h in holes:
  assert np.allclose(h['clear_size_mm'],[3000,2850],atol=.1),h
  floor=next(p for p in parts if p['name']=='FLOOR-EL'+str(h['EL']));v=np.array(floor['vertices']);tri=v[np.array(floor['faces'])];z=(h['EL']-100)*1000
  top=tri[np.max(abs(tri[:,:,2]-z),axis=1)<1e-4]
  poly=np.array(h['polygon']);lo=poly.min(0);hi=poly.max(0)
  a=top[:,0,:2];u=top[:,1,:2]-a;v=top[:,2,:2]-a;den=u[:,0]*v[:,1]-u[:,1]*v[:,0];valid=abs(den)>1e-8
  for x in np.linspace(lo[0]+20,hi[0]-20,5):
   for y in np.linspace(lo[1]+20,hi[1]-20,5):
    q=np.array([x,y])-a;vv=np.divide(q[:,0]*v[:,1]-q[:,1]*v[:,0],den,out=np.zeros_like(den),where=valid);ww=np.divide(u[:,0]*q[:,1]-u[:,1]*q[:,0],den,out=np.zeros_like(den),where=valid)
    assert not np.any(valid&(vv>=-1e-8)&(ww>=-1e-8)&(vv+ww<=1+1e-8)),h['id']
 assert len((REPO/'水解总装工程/data/building.js').read_bytes())<300
 total=(REPO/'水解总装工程/index.html').read_text();assert '../厂房外观模型/建筑/model_data.js' in total
 print('完整门窗146处、四角楼梯两组高度、6房间、局部柱及5处真实吊装孔均通过')
if __name__=='__main__':run()
