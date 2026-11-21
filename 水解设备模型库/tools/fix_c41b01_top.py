"""Restore the removable through-pipe covers in C41B01 detail II only."""
from pathlib import Path
import json,shutil,hashlib
import numpy as np
from build_c41b04_v2 import geo,pipe,export,STEEL
from review_c41b01_v2 import read,write,mesh
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B01';H=OUT/'历史/2.0-C41B01-02_顶部修正前'
def main():
 if not H.exists():
  H.mkdir(parents=True)
  for n in ['设备','整改说明.html','整改说明.md','逐类复核.json','预览_设备.png','安装表.json']:
   p=OUT/n
   if p.is_dir():shutil.copytree(p,H/n)
   else:shutil.copy2(p,H/n)
  write(H/'归档清单.json',{str(p.relative_to(H)):hashlib.sha256(p.read_bytes()).hexdigest() for p in H.rglob('*') if p.is_file()})
 old=mesh(H/'设备/model_data.js');geo.parts.clear()
 for q in old:geo.add(q['name'],q['color'],q['vertices'],q['faces'])
 params=read(OUT/'设备/参数.json')
 for p in params['ports']:
  if p['id'] not in ['b1/k1','b2/k2']:continue
  x,y,z=p['face_center_mm'];mid=z-150;r=p['neck_OD_mm']/2
  # Detail II: DN200 sleeve terminates at a removable cover through which
  # the small pipe passes; the previous model left the large annulus open.
  pipe('接口_'+p['id']+'_穿管盖板',(x,y,mid),(x,y,mid+10),p['outside_flange_OD_mm']/2,r)
  p['connection']='DN200套管法兰＋穿管盖板＋贯穿小接管；详图II'
  p['cover_thickness_display_mm']=10
 newbounds=export(OUT/'设备','C41B01');new=mesh(OUT/'设备/model_data.js')
 assert new[:len(old)]==old and len(new)==35
 assert np.allclose(newbounds,params['bounds_mm'])
 params['top_revision']='顶部连接修正：补b1/k1、b2/k2穿管盖板；10mm盖厚为展示值，未标紧固件不补造'
 write(OUT/'设备/参数.json',params);top=read(ROOT/'parameters/C41B01.json');top.update(params);write(ROOT/'parameters/C41B01.json',top)
 write(OUT/'顶部接口修正.json',{'source':params['source_drawing'],'detail':'II及主视图b1/k1、b2/k2','change':'补两块带中心穿管孔的可拆盖板，封闭原误留的DN200套管敞口','retained_parts':33,'added_parts':2,'cover_thickness_mm':10,'thickness_status':'未标，展示值','positions_foundations_other_parts':'unchanged'})
 for name in ['整改说明.md','整改说明.html']:
  p=OUT/name;s=p.read_text();note='顶部补正：b1/k1、b2/k2按详图II补穿管盖板，修正套管中部敞口；盖厚10mm为展示值。原33件、h盖和安装位置保持。'
  if note not in s:s=s.replace('</html>','<p>'+note+'</p></html>') if name.endswith('html') else s+'\n\n'+note+'\n'
  p.write_text(s)
 print('PASS: 33 original parts unchanged; two through-pipe covers added.')
if __name__=='__main__':main()
