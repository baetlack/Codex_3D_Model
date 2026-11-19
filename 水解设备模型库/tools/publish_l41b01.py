"""Publish traceable L41B01 geometry and explicit unresolved support decisions."""
from pathlib import Path
import csv,html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/L41B01'
def publish():
 p=json.loads((OUT/'设备/参数.json').read_text());installs=json.loads((OUT/'安装表.json').read_text());project=json.loads((ROOT/'project.json').read_text())
 text=f'''L41B01A—F · 水解过滤器 · {p['version']}

本轮6台统一按适用新总图重建，精度和风格沿用用户接受的C41B02-02。旧1.0、暂定圆台及所有原图保留；已确认设备、建筑和桥架几何保持。

适用性：2026.5.21设备台账水解页第103行，L41B01A-F、6台、规格Ø1200/H1220，明确复用LMBLJC2001-03L4103。新增《水解过滤器总图》图号LMBLJC2001-03L4103-1、共4张的第1张，注明共6台；适用系列和数量一致。缺-2下筒体、-3筛板/垫片、-4上筒体详图，不补造隐藏制造细节。

本体：Ø1200为内径，8mm钢壳外径1216。下筒段500、锥斗轴高350、底排伸出100，上筒段450；分筒连接层含两片5mm垫片和20mm PP筛板。盖顶距底排密封面约1446mm，两个顶口另高120，整机包络1566mm；台账H1220保留为历史名义值，不把新图压缩成1220。平盖Ø1256/厚8，补两条高50、图面厚5的长立筋，它们不是吊耳。

五管口：a进料DN300/内衬DN250瓷管，端面X-750，偏心Y445.5，距下筒锥斗起点250；旧模型Y500不再沿用。b出料DN300在南侧，伸出150、距上筒顶200；c为中心底排渣DN300。d/e为顶盖清洗/呼吸DN50，X400/Y±200，伸出120。顶口法兰外径165；侧/底DN300法兰外廓按图面445。Ø400是底口螺栓圆，不是其外径。

分筒主法兰：外廓按CAD主视/俯视约1375，明示螺栓圆1320，24-M20×130跨中均布。只表达图中明确的连接螺栓、垫圈、螺母，不附加无依据的长拉杆或外笼。隐藏筛孔和衬里不展开，仅保留外露筛板边缘。

三耳：60/180/300度，耳孔圈1382、孔30；底板局部Z650，板径向125/切向160/厚10，补贴体板和双筋。1320主连接螺栓圆与1382三耳孔圆用途不同；支座外廓按原图弧/线复核，未提供完整支座零件图，不作施工放样。

安装与支承：新局部原点是底部c口密封端面Z0。按用户明确选择，保持6台原X/Y与暂用Z，三耳承托EL仍待核。记录中的“原暂用EL+0.650”只是当前模型算术关系，不是已确认承托标高。A/C/E原图INSERT为180度并带X负比例，等价于0度+Y镜像；原总装仅取180度漏掉了镜像，本次按源矩阵纠正。B/D/F为0度无镜像。两个顶口中心可与布置符号对应，但总图注明“按工艺专业管口方位图”，不能据此把新接口绝对方位标作确认。

旧Ø1300×200圆台是此前暂定方案，无法作为本次三耳悬挂结构的依据。按用户选择，旧圆台保留1.0，当前新本体不再与其组合。未取得承托梁/支墩及承托EL，不新造支墩、钢腿或地脚连接；当前总装不新增本类基础实例。待支承资料明确后再闭合托耳—承托面—全局标高链。

版本与验证：本体、GLB/OBJ、逐台安装表和来源差异独立保存；可与1.0平底示意模型并排旋转对照。校验读取原生DXF尺寸、孔中心、耳孔弧、布置INSERT原始矩阵，并检查实际网格、现有柱梁、桥架、楼板及其他设备；未确认标高下的检查只代表当前暂用位置，不是现场安装验收。不检查检修空间。
'''
 (OUT/'整改说明.md').write_text(text)
 with (OUT/'安装对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['位号','X_mm','Y_mm','底口暂用Z_mm','原旋转_deg','新旋转_deg','Y镜像','暂用托耳EL_不是确认值','支承/标高','工艺方位'])
  for q in installs:w.writerow([q['id'],*q['position_mm'],q['installation_review']['before_rotation_deg'],q['rotation_deg'],q['mirror_y'],q['installation_review']['temporary_bearing_EL'],'待核；不采用旧圆台','新接口绝对方位待核'])
 style='body{max-width:1100px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.9}a{color:#7cdce6}img{max-width:100%}pre{white-space:pre-wrap}.pending{padding:15px;background:#3c3324;border:1px solid #786244}'
 doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B01水解过滤器整改</title><style>'+style+'</style><h1>水解过滤器 · 六台本体整改</h1><p><a href="../../../index.html?type=L41B01">当前本体与下载</a> · <a href="修订对比.html">1.0/2.0并排对照</a> · <a href="安装对照.csv">6台安装对照</a> · <a href="校验报告.json">几何及当前暂用位置检查</a></p><p class="pending">承托结构、承托EL及新接口工艺绝对方位待核。按用户选择保持原位置作暂用展示，当前本体不与旧圆台组合。</p><pre>'+html.escape(text)+'</pre>'
 for name,title in [('依据_主视.png','新总图主视'),('依据_俯视.png','新总图俯视'),('预览_设备.png','当前本体'),('预览_三耳.png','三耳与承托面'),('预览_总装定位.png','当前暂用位置')]:
  if (OUT/name).exists():doc+='<p>'+title+'</p><img src="'+name+'" alt="'+title+'">'
 (OUT/'整改说明.html').write_text(doc+'</html>')
 (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B01设备2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>水解过滤器2.0 · <a href="整改说明.html">图纸、安装与待核项</a> · <a href="修订对比.html">1.0/2.0对照</a></header><iframe title="L41B01" src="../../../index.html?type=L41B01"></iframe></html>')
 (OUT/'修订对比.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>水解过滤器新旧对照</title><style>body{margin:0;background:#101923;color:#dce8ef;font:15px sans-serif}header{padding:12px}a{color:#7cdce6}main{display:grid;grid-template-columns:1fr 1fr;height:calc(100vh - 110px)}iframe{width:100%;height:100%;border:1px solid #344957}button{padding:8px;margin:4px;background:#1c3040;color:#dce8ef;border:1px solid #486170}p{margin:12px}</style><header>水解过滤器 · 1.0/2.0 · <button data-view="all">完整本体</button><button data-view="top">顶部俯视</button><button data-view="ears">三耳</button><button data-view="bottom">锥斗与底排</button> · <a href="整改说明.html">来源与待核项</a></header><main><iframe title="1.0原版" src="对照视图.html?version=old"></iframe><iframe title="2.0新版" src="对照视图.html?version=new"></iframe></main><p>旧平底模型基准/新底排端面各取Z0，仅作外形对照；不代表同一承托面。新模型承托结构与EL待核。</p><script>for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{for(const f of document.querySelectorAll('iframe'))f.contentWindow.postMessage({type:'preview-view',mode:b.dataset.view},'*');};</script></html>''')
 (OUT/'对照视图.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}#label{position:absolute;top:15px;left:18px}#scene{width:100vw;height:100vh}</style><div id="label"></div><canvas id="scene"></canvas><script src="../../../orthographic_viewer.js"></script><script>const old=new URLSearchParams(location.search).get('version')==='old';document.getElementById('label').textContent=old?'设备1.0 · 平底示意':'设备2.0 · 按适用总图';const s=document.createElement('script');s.src=old?'../../1.0/快照/水解设备模型库/示图建模_20260521/模型/L41B01/model_data.js':'设备/model_data.js';s.onload=()=>{const mesh=window.MODEL_PARTS,v=createEquipmentViewer(document.getElementById('scene'),{doubleSided:true,centerProjection:true});window.previewView=mode=>{window.previewMode=mode;let parts=mesh;if(mode==='ears')parts=mesh.filter(p=>p.name.startsWith('托耳_'));if(mode==='bottom')parts=mesh.filter(p=>p.name.includes('锥')||p.name.startsWith('接口_c_'));if(!parts.length)parts=mesh;v.setParts(parts);v.view(mode==='top'?-Math.PI/2:-Math.PI/4,mode==='top'?Math.PI/2:mode==='bottom'?-.28:.35,mode);v.fit();};window.addEventListener('message',e=>{if(e.data?.type==='preview-view'&&['all','top','ears','bottom'].includes(e.data.mode))window.previewView(e.data.mode);});window.previewView('all');window.compareReady=true;};document.head.append(s);</script></html>''')
 progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=p['version'],revised_items=project['counts']['revised_items'],unchanged_items=project['counts']['other_items_unchanged'],next_class=project['next_class'])
 for q in progress['rows']:
  if q['位号组']=='L41B01A-F':q.update(本批状态='6台新本体/三耳完成，A/C/E镜像纠正；承托结构/EL与新接口方位待核',本批依据='台账复用图号与LMBLJC2001-03L4103-1一致；新图6台；用户确认暂按旧位置展示，不与旧圆台组合')
 from build_c41b04_v2 import save
 save(ROOT/'data/设备整改进度.json',progress)
 from publish_equipment_index import publish as index
 index()
if __name__=='__main__':publish()
