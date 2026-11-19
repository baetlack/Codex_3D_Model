"""Check actual mesh against independent source outlines, dimensions, and section topology."""
from pathlib import Path
import sys,json,math,collections
import numpy as np
import ezdxf
from ezdxf import bbox
R=Path(__file__).resolve().parents[2];OUT=R/'水解设备模型库/版本/2.0/C41B02'
def verify_topside(parts):
 by={p['name']:p for p in parts};d=ezdxf.readfile(R/'水解设备模型库/水解设备图纸/钛液预热槽(C41B02A-E).dxf')
 def box(handle):
  b=bbox.extents([d.entitydb[handle]],fast=True);return np.array(b.extmin),np.array(b.extmax)
 lo,hi=box('94C7');origin=(lo+hi)/2;scale=5724/(hi[0]-lo[0]);errors={}
 def compare(name,handle,diameter=None):
  a,b=box(handle);ref=((a+b)/2-origin)[:2]*scale;v=np.array(by[name]['vertices']);actual=(v[:,:2].min(0)+v[:,:2].max(0))/2
  err=float(np.linalg.norm(actual-ref));assert err<1,(name,actual,ref,err)
  if diameter is not None:
   assert abs(float(v[:,0].max()-v[:,0].min())-diameter)<.0001,name
   assert abs((b[0]-a[0])*scale-diameter)<1,(name,'source OD')
  errors[name]=round(err,6)
 for i,h in enumerate(['9460','945C','9458','9464','9435','9439','9440','9444'],1):compare(f'接口_k{i}_盘管检修盖',h,1075)
 for name,h,diam in [('c','944B',265),('d','9455',320),('e','94D2',185),('f','94C3',200),('n','94CA',340)]:compare(f'接口_{name}_法兰',h,diam)
 compare('接口_p_法兰375','944F',375)
 compare('接口_b1_法兰','94AF',150);compare('接口_j1_法兰','94AC',150)
 compare('接口_k1_共座法兰','94B1',460);compare('06_Frame_foot','9469',600);compare('06_圆筒开窗支架_环1','9481',490)
 # A radial offset would pass a loose radius check but fails the tangent condition.
 for i in range(1,9):
  b=np.array(by[f'接口_b{i}_法兰']['vertices']);j=np.array(by[f'接口_j{i}_法兰']['vertices']);k=np.array(by[f'接口_k{i}_盘管检修盖']['vertices'])
  center=lambda v:(v[:,:2].min(0)+v[:,:2].max(0))/2
  cb,cj,ck=center(b),center(j),center(k)
  assert abs(np.linalg.norm(cb-cj)-250)<.001
  assert abs(np.dot(cb-cj,ck/np.linalg.norm(ck)))<.001
  assert abs(b[:,2].max()-k[:,2].max()-177)<.001
 # Four high walls and a true pair of cover plates, not four flat rails.
 walls=[p for p in parts if p['name'].startswith('盖面_m_高座_')];assert len(walls)==4
 assert all(abs(np.ptp(np.array(p['vertices'])[:,2])-280)<.0001 for p in walls)
 plates=[p for p in parts if p['name'].startswith('盖面_m_对开顶板')];assert len(plates)==2
 assert all(abs(np.ptp(np.array(p['vertices'])[:,2])-30)<.0001 for p in plates)
 assert '接口_d_取样盖竖柄' in by and '接口_n_PP盲板' in by
 assert len([p for p in parts if p['name'].startswith('接口_n_螺栓')])==8
 # The corrected concentric sleeves have a constant diameter at each station.
 # The previous conical reducer could not satisfy this check.
 for key,outerOD,smallOD in [('g',377,273),('h',273,159)]:
  for suffix,diam in [('大端直套管',outerOD),('外端直短接',smallOD)]:
   v=np.asarray(by[f'接口_{key}_{suffix}']['vertices']);z=460 if key=='g' else 4860;radius=np.hypot(v[:,1],v[:,2]-z)
   assert abs(radius.max()-diam/2)<.0001
   stations=np.unique(np.round(v[:,0],5));assert len(stations)==2
   for station in stations:assert abs(radius[np.isclose(v[:,0],station)].max()-diam/2)<.0001
  assert len([p for p in parts if p['name'].startswith(f'接口_{key}_') and '法兰' in p['name']])==3
  v=np.vstack([p['vertices'] for p in parts if p['name'].startswith(f'接口_{key}_')]);assert abs(abs(v[:,0]).max()-2750-413)<.0001
  assert not any('变径' in p['name'] for p in parts if p['name'].startswith(f'接口_{key}_'))
 # Actual caps and two-hole plates must be closed meshes with unfilled openings.
 # Every edge has two incident faces; holes are side walls rather than surface plugs.
 for p in plates+[p for p in parts if '双管共盖板' in p['name']]:
  edges=collections.Counter(tuple(sorted((f[i],f[(i+1)%len(f)]))) for f in p['faces'] for i in range(len(f)))
  assert set(edges.values())=={2},(p['name'],collections.Counter(edges.values()))
 result={'status':'passed','source_outline_mesh_comparisons':errors,'max_center_error_mm':max(errors.values()),'m_seat_height_mm':280,'m_plate_mm':30,'k_plate_OD_mm':1075,'bj_pair_mm':250,'bj_orientation':'tangent','side_sleeves':'constant OD, separate connecting flanges and gasket','d_handle_n_blind_cover':True,'plate_hole_meshes_watertight':True,'limits':'孔中心图面校准误差是模型对该图的吻合度，不是图纸或现场安装公差。'}
 (OUT/'顶侧结构独立校验.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');return result
if __name__=='__main__':
 sys.path.insert(0,str(R/'水解总装工程/tools'));from check_assembly import script
 print(json.dumps(verify_topside(script(OUT/'设备/model_data.js','MODEL_PARTS')),ensure_ascii=False))
