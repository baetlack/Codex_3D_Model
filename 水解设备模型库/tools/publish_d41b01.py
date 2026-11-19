"""Readable source/installation record and before/after viewer for D41B01."""
from pathlib import Path
import csv,html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/D41B01'
def publish():
 p=json.loads((OUT/'设备/参数.json').read_text());installs=json.loads((OUT/'安装表.json').read_text())
 text=f'''D41B01A—E · 晶种制备槽 · {p['version']}

本次5台统一采用新本体，按用户选择保留A槽支架待核。已确认的C41B02/C41B04、建筑和桥架几何保持。设备1.0、原图及旧支架源文件保留，可独立下载本体和支架。

依据：《晶种制备槽总图》LMT1501-03-D4110-1（施工图，总计5张的第1张），与2026.5.21布置图平剖面、台账及既有支架记录整合。原图注明共4台，台账为5台；用户明确A—E五台均用新本体，不删减位号。其余4张详图及工艺管口方位图尚未取得。

本体：内径1800、钢壳外径1816/壁厚8、保温60外包络1936；内筒段1600与钢壳用料高1690分别记录。槽底按主剖面10度浅锥表现，不再把1800作为钢壳外径。顶盖约1942、盖高21，按图保留孔位；a碱液与b钛液为不同口径的插管总成；c/d共座管距180；e洗水、f液位、h取样人孔独立表达；m1—3为盘管支撑侧口，g为西南45度斜温度口，j为中心底排，k为搅拌安装口。

四向托耳：底板250×400×12、孔36及双筋按详图；补强圈1832×8高530、两只2072/1832厚12贴身刚性环有明确明细表依据。耳孔跨2102按主视明示尺寸，俯视量测2118另留差异；不按无依据符号另加外露杆架。搅拌架/减速/电机分段高645/302/340，外廓按主视展示，内部衬胶、衬砖、盘管和叶轮不展开。

尺度校准：主视与俯视2个CAD单位/mm，1:8托耳详图2.5单位/mm。尺寸覆盖文字优先于被拉伸的图元：电机340（图元361）、盖高21（图元26）、c/d高154（图元169）、耳板厚12（图元20）。图示总高约3410与本次分段/量测链3415.117mm并列保留，约数不作为制造精确尺寸。

安装：新局部Z0改为四托耳底；世界承托面仍为EL111.000，原设备原点Z9820加原托耳1180等于11000。本次改变局部原点，不移动承托面。槽体顶EL111.600，电机顶EL113.103，底排端面约EL109.688；5台X/Y、旋转、镜像保持。总图要求“按工艺专业管口方位图”，所以旧七孔匹配不能当新接口绝对方位确认，五台新方向状态均待核。A无支架依据，保留其旧承托标高作为暂取，降为待核。

支架：B/C、D/E按两组成对支架加入总装。平面两槽中心距2600mm（F1C1C/F1B80），剖面水平距另标2500mm（57BF9），确有100mm图纸差异；本次保留既有平面2600mm，并将差异留待图纸复核。支架竖向高度另由EL108.500至EL111.000标高差得2500mm，与剖面水平2500不是同一尺寸。现有支架网格保留，梁160×200、柱160×160仍属示意截面；仅校核当前展示模型的托耳接触及空间关系。A不复制任何支架。

未决：平面/剖面水平槽距100mm差异、A支架与承托标高适用性、支架施工截面及节点、新接口现场绝对方位；缺失详图的局部小厚度和驱动外廓仍属图面展示。60mm保温仅外包络，不额外补雨棚、外接管线或检修空间。
'''
 (OUT/'整改说明.md').write_text(text)
 with (OUT/'安装对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['位号','X_mm','Y_mm','托耳底Z_mm','旋转_deg','Y镜像','承托EL','槽顶EL','电机顶EL','支架','状态'])
  for q in installs:w.writerow([q['id'],*q['position_mm'],q['rotation_deg'],q['mirror_y'],111,111.6,113.103,'待核' if q['id'].endswith('A') else 'B/C或D/E成对支架',q['z_status']+'；新接口绝对方位待核'])
 style='body{max-width:1100px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.9}a{color:#7cdce6}img{max-width:100%}pre{white-space:pre-wrap}'
 doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>D41B01整改说明</title><style>'+style+'</style><h1>晶种制备槽 · 新总图整改</h1><p><a href="../../../index.html?type=D41B01">当前模型与成对支架</a> · <a href="修订对比.html">1.0/2.0并排对比</a> · <a href="安装对照.csv">5台安装对照</a> · <a href="校验报告.json">几何与碰撞校验</a></p><pre>'+html.escape(text)+'</pre>'
 for name,title in [('依据_主视.png','主视结构依据'),('依据_俯视.png','顶盖接口依据'),('依据_托耳.png','刚性环耳式支座依据'),('预览_设备.png','当前本体'),('预览_双槽支架.png','B/C双槽与支架'),('预览_总装定位.png','总装定位')]:
  if (OUT/name).exists():doc+='<p>'+title+'</p><img src="'+name+'" alt="'+title+'">'
 (OUT/'整改说明.html').write_text(doc+'</html>')
 (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>D41B01设备2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>晶种制备槽2.0 · <a href="整改说明.html">图纸、来源与校验</a> · <a href="修订对比.html">1.0/2.0对比</a></header><iframe title="D41B01" src="../../../index.html?type=D41B01"></iframe></html>')
 (OUT/'修订对比.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>D41B01新旧模型对比</title><style>body{margin:0;background:#101923;color:#dce8ef;font:15px sans-serif}header{padding:12px}a{color:#7cdce6}main{display:grid;grid-template-columns:1fr 1fr;height:calc(100vh - 110px)}iframe{width:100%;height:100%;border:1px solid #344957}button{padding:8px;margin:4px;background:#1c3040;color:#dce8ef;border:1px solid #486170}p{margin:12px}</style><header>晶种制备槽 · 1.0/2.0对比 · <button data-view="all">完整设备</button><button data-view="top">顶部俯视</button><button data-view="lugs">四向托耳</button> · <a href="整改说明.html">来源与变更</a></header><main><iframe title="1.0原版" src="对照视图.html?version=old"></iframe><iframe title="2.0新版" src="对照视图.html?version=new"></iframe></main><p>两侧均以托耳底Z0对齐；5台统一新本体，A支架待核。可独立旋转、缩放。</p><script>for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{for(const f of document.querySelectorAll('iframe'))f.contentWindow.previewView?.(b.dataset.view);};</script></html>''')
 (OUT/'对照视图.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>晶种制备槽对照</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}#label{position:absolute;top:15px;left:18px}#scene{width:100vw;height:100vh}</style><div id="label"></div><canvas id="scene"></canvas><script src="../../../orthographic_viewer.js"></script><script>const old=new URLSearchParams(location.search).get('version')==='old';document.getElementById('label').textContent=old?'设备1.0 · 冻结原版':'设备2.0 · 按新总图';const s=document.createElement('script');s.src=old?'../../1.0/快照/水解桥架工程/models/设备/设备基础_20261106/设备净模/D41B01/model_data.js':'设备/model_data.js';s.onload=()=>{const parts=window.MODEL_PARTS.map(p=>({...p,vertices:p.vertices.map(([x,y,z])=>[x,y,z-(old?1180:0)])}));const v=createEquipmentViewer(document.getElementById('scene'),{doubleSided:true,centerProjection:true});window.previewView=mode=>{const selected=mode==='lugs'?parts.filter(p=>/托耳|支撑_.*耳/.test(p.name)):parts;v.setParts(selected);v.view(mode==='top'?-Math.PI/2:-Math.PI/4,mode==='top'?Math.PI/2:.35,mode);v.fit();};window.previewView('all');window.compareReady=true;};document.head.append(s);</script></html>''')
 progress=json.loads((ROOT/'data/设备整改进度.json').read_text());project=json.loads((ROOT/'project.json').read_text());progress.update(revised_items=project['counts']['revised_items'],unchanged_items=project['counts']['other_items_unchanged'],next_class=project['next_class'])
 if len(project['revisions'])==3:progress['version']=p['version']
 for row in progress['rows']:
  if row['位号组']=='D41B01A-E':
   row.update(本批状态='5台新本体与BC/DE成对支架已更新；平剖面槽距100差异、A支架/新接口绝对方位待核',本批依据='LMT1501-03-D4110-1、布置图、用户确认5台统一本体；支架截面仍示意',Z有安装基准=4,Z待核=1)
 save=__import__('build_c41b04_v2').save;save(ROOT/'data/设备整改进度.json',progress)
 from publish_equipment_index import publish as index
 index()
if __name__=='__main__':publish()
