"""Publish F41B03's limited evidence and an explicitly non-installation overlay."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/F41B03'
def publish():
 p=json.loads((OUT/'设备/参数.json').read_text());r=json.loads((OUT/'支承差异.json').read_text());project=json.loads((ROOT/'project.json').read_text())
 text=f'''F41B03 · 冷凝水分汽器 · {p['version']}

本批为证据范围内的表达修正与支承核对，并非完整设备总图重建。现有台账只明确直筒段Ø1000×1000，设备资料只有俯视；尚无整机侧视、封头、盖板和管口总图，不根据设备名称补造这些结构。

设备依据：2026.5.21台账水解页第51行、示图3623/3625/3626及3629—3632。3623是名义筒径Ø1000；3626位于中心线层，半径550，穿过四个安装孔，是孔位分度圆Ø1100，不是端部实体圈。原模型据它生成了上下两个Ø1104端圈，本次撤下，原直筒段几何保持。

四耳平面：底板外端半径591.25，内端约489.230485，切向宽137.5；4个孔Ø16.5、孔心半径550，四向90度均布。原实心底板改成真实开孔。俯视还有双筋投影，但缺立面高度，不自行生成立筋高度。原筒壁12、底板厚24及耳底Z0继续作为显示暂用值，不能写成图纸明示尺寸。

基础依据：《水解设备基础图》冷凝水分汽器基础与4-4/MJ-2详图。四支墩300×300，中心沿四轴±750（对边中心距1500），预埋板中心与支墩中心相同。原四支墩/预埋板模型几何逐字节保留，独立保存于本类2.0基础目录。露出段显示高100及板厚/全局高程的解释仍列待核；2B52尺寸文字已写“板厚”，不能把其残留图形数值500当成确认楼板厚。

支承差异：四个方向耳板外端591.25，而支墩内缘600，轴向净距8.75mm；耳孔中心550与预埋板中心750径向相差200mm；平面搭接面积为0。耳板最外角半径约{r['ear_outer_corner_radius_mm']:.3f}，小于支墩最内600，所以仅旋转也不能形成直接接触。不拉长托耳、不移动支墩、不凭空加过渡板来制造“已贴合”。过渡件形式/尺寸、托耳高度与实际承托EL必须另核。

安装：布置图D9737圆心对应本地X40000/Y41750，旁注D973A为POSEL112.200。当前仍保留原暂用Z12200、零旋转；该POS究竟指筒段下端还是承托面尚不明确，四耳共同方位和管口方向也未确认。当前总装仅替换设备表达，不增加本类四支墩实例，不认定承托链闭合。

对照功能：设备和四支墩可各自独立查看/下载；另提供“支承差异诊断”三维页。诊断页把耳底与墩顶临时设为同高本地Z0，只为检查平面搭接，不是厂房安装方案、没有改变总装就位表。可切换俯视、轴测和东侧局部查看8.75mm净距；孔心与埋件中心200mm差异同时记录。1.0/2.0页保留原端圈与修正后模型对照。

1.0、所有原始图、原四墩及其他设备/建筑/桥架保持。缺完整总图、过渡件及承托EL的限制在参数、安装表和界面明确标示。模型校核针对当前暂用位置，不替代安装确认；不检查检修空间。
'''
 (OUT/'整改说明.md').write_text(text)
 style='body{max-width:1100px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.9}a{color:#7cdce6}img{max-width:100%}pre{white-space:pre-wrap}.pending{padding:15px;background:#3c3324;border:1px solid #786244}'
 doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>冷凝水分汽器校核</title><style>'+style+'</style><h1>F41B03 · 直筒段与四墩支承核对</h1><p><a href="../../../index.html?type=F41B03">当前模型/独立基础</a> · <a href="支承对照.html">支承差异三维诊断</a> · <a href="修订对比.html">1.0/2.0对照</a> · <a href="校验报告.json">校验记录</a></p><p class="pending">仅直筒段模型；四耳与四墩无平面搭接，过渡件/托耳高度/承托EL及完整总图待核。</p><pre>'+html.escape(text)+'</pre>'
 for name,title in [('依据_设备俯视.png','设备俯视原图'),('依据_基础.png','四墩基础原图'),('预览_设备.png','当前直筒段与开孔底板'),('预览_支承俯视.png','同高平面诊断，非安装方案'),('预览_支承局部.png','东侧局部净距')]:
  if (OUT/name).exists():doc+='<p>'+title+'</p><img src="'+name+'" alt="'+title+'">'
 (OUT/'整改说明.html').write_text(doc+'</html>')
 (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>F41B03设备2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>F41B03 · <a href="整改说明.html">校核说明/待核项</a> · <a href="支承对照.html">四耳/四墩诊断</a> · <a href="修订对比.html">1.0/2.0对照</a></header><iframe title="当前直筒段模型" src="../../../index.html?type=F41B03"></iframe></html>')
 diagnostic='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>四耳/四墩支承诊断</title><style>html,body{margin:0;background:#101923;color:#dce8ef;font:15px sans-serif}header{padding:15px 20px;line-height:1.8}a{color:#7cdce6}button{background:#1c3040;color:#dce8ef;border:1px solid #486170;padding:8px;margin:3px;cursor:pointer}.pending{padding:10px 20px;background:#403325}main{display:grid;grid-template-columns:minmax(0,1fr) 310px}canvas{width:100%;height:72vh;display:block}aside{padding:25px;line-height:2}b{color:#f1c183}@media(max-width:850px){main{grid-template-columns:1fr}}</style><header><strong>F41B03 · 支承平面差异诊断</strong> · <a href="整改说明.html">来源与待核项</a><br><button data-view="top">俯视全图</button><button data-view="iso">轴测</button><button data-view="east">东侧局部</button></header><div class="pending">耳底和支墩顶暂设同高本地Z0，仅诊断平面搭接；不是厂房安装方案，未确认实际承托标高。</div><main><canvas id="scene"></canvas><aside>四耳外端：591.25 mm<br>四墩内缘：600 mm<br><b>轴向净距：8.75 mm</b><br>耳孔中心：550 mm<br>预埋板中心：750 mm<br><b>中心差：200 mm</b><br>直接搭接面积：0 mm²<br><br>原设备与支墩尺寸保持。过渡件、托耳高度与承托EL待核。<p><a href="支承差异.json">四向数值记录</a><br><a href="../../../index.html?type=F41B03">设备/基础独立下载</a></p></aside></main><script src="../../../orthographic_viewer.js"></script><script>
async function load(src){return await new Promise((resolve,reject)=>{const s=document.createElement('script');s.src=src;s.onload=()=>{const p=window.MODEL_PARTS;delete window.MODEL_PARTS;s.remove();resolve(p);};s.onerror=reject;document.head.append(s);});}
(async()=>{const equipment=await load('设备/model_data.js'),base=await load('基础/model_data.js');const viewer=createEquipmentViewer(document.getElementById('scene'),{doubleSided:true,centerProjection:true});window.diagnosticView=mode=>{let parts=[...equipment,...base];if(mode==='east')parts=[...equipment.filter(p=>p.name.includes('R1_')),...base.filter(p=>Math.min(...p.vertices.map(v=>v[0]))>=599)];viewer.setParts(parts);viewer.view(mode==='top'?-Math.PI/2:-Math.PI/4,mode==='top'?Math.PI/2:.35,mode);viewer.fit();window.diagnosticMode=mode;window.diagnosticParts=parts.length;};for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>window.diagnosticView(b.dataset.view);window.diagnosticView('top');window.diagReady=true;})();
</script></html>'''
 (OUT/'支承对照.html').write_text(diagnostic)
 (OUT/'修订对比.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>F41B03修订对照</title><style>body{margin:0;background:#101923;color:#dce8ef;font:15px sans-serif}header{padding:15px}a{color:#7cdce6}main{display:grid;grid-template-columns:1fr 1fr;height:calc(100vh - 100px)}iframe{width:100%;height:100%;border:1px solid #344957}button{padding:8px;background:#1c3040;color:#dce8ef;border:1px solid #486170}p{margin:15px}</style><header>F41B03 · 1.0/2.0 · <button data-view="all">筒段与底板</button> <button data-view="top">俯视孔位</button> · <a href="支承对照.html">四墩支承差异</a></header><main><iframe src="对照视图.html?version=old" title="原版"></iframe><iframe src="对照视图.html?version=new" title="修正版"></iframe></main><p>撤下无外形依据的两端圈，修正四块底板孔；未补造完整封头、管口或支承过渡件。</p><script>for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{for(const f of document.querySelectorAll('iframe'))f.contentWindow.postMessage({type:'preview-view',mode:b.dataset.view},'*');};</script></html>''')
 (OUT/'对照视图.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}#label{position:absolute;top:15px;left:18px}canvas{width:100vw;height:100vh}</style><div id="label"></div><canvas id="scene"></canvas><script src="../../../orthographic_viewer.js"></script><script>const old=new URLSearchParams(location.search).get('version')==='old';document.getElementById('label').textContent=old?'1.0 · 原表达':'2.0 · 仅直筒段/四耳孔修正';const s=document.createElement('script');s.src=old?'../../1.0/快照/水解设备模型库/示图建模_20260521/模型/F41B03/model_data.js':'设备/model_data.js';s.onload=()=>{const mesh=window.MODEL_PARTS,v=createEquipmentViewer(document.getElementById('scene'),{doubleSided:true,centerProjection:true});window.previewView=mode=>{v.setParts(mesh);v.view(mode==='top'?-Math.PI/2:-Math.PI/4,mode==='top'?Math.PI/2:.35,mode);v.fit();window.previewMode=mode;};window.addEventListener('message',e=>{if(e.data?.type==='preview-view'&&['all','top'].includes(e.data.mode))window.previewView(e.data.mode);});window.previewView('all');window.compareReady=true;};document.head.append(s);</script></html>''')
 progress=json.loads((ROOT/'data/设备整改进度.json').read_text());progress.update(version=p['version'],revised_items=project['counts']['revised_items'],unchanged_items=project['counts']['other_items_unchanged'],next_class=project['next_class'])
 for q in progress['rows']:
  if q['位号组']=='F41B03':q.update(本批状态='撤无依据端圈、补四耳孔并核对四墩；8.75边距/200中心差，支承未闭合',本批依据='台账直筒段规格、原设备俯视与基础图；缺完整总图/过渡件/承托EL，不造支承')
 from build_c41b04_v2 import save
 save(ROOT/'data/设备整改进度.json',progress)
 from publish_equipment_index import publish as index
 index()
if __name__=='__main__':publish()
