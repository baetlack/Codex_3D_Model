"""Publish this class only; common index reads the revision registry."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/L41B02'
STYLE='body{max-width:1100px;margin:28px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.85}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #344957;text-align:left}img{max-width:100%;max-height:850px;background:white}'
def publish():
    report=OUT/'支承相交校核.json';r=json.loads(report.read_text()) if report.exists() else {'old_hits':[],'new_hits':[],'status':'待执行本类校核'}
    table=''.join('<tr><td>'+html.escape(q['equipment'])+'</td><td>'+html.escape(q['frame'])+'</td></tr>' for q in r['new_hits']) or '<tr><td colspan="2">校核结果见本类记录，不代表绝对安装确认。</td></tr>'
    text='''L41B02 尾气洗涤塔 · 2.0-L41B02-01

台账第105行为1台、Ø2200×10300。没有新增制造总图，本次采用原设备示图的完整侧视2689—2723和俯视2E93，并核对专用圆基础图及增补钢塔架图。

本体：直段上端9400，锥段至10100，顶口至10300；原顶口/锥段分界和底部130高圆柱修正。底部恢复R50转角及环形锚板，撤下原推断四托座。底部立边按连续环表达仅为展示假定，真实分段/构造待详图。2800×100示意支承块不并入设备，不替代专用圆基础。

侧口：西侧低口中心250；北侧大口1500；南侧下口800、中下5000、中上7000、上口8900。原模型375、2120、1150、3050、5750、8420均有修正。口径/外廓按侧视量测，不写成确认DN。喷淋锥线、内部喷管和除雾件不作为外部梁架补造。

图纸取舍：侧视顶法兰955、俯视1182.5；侧视底锚圈2600、俯视2750，存在差异。本体外形统一按侧视；底锚圈结合专用基础Ø2400/12-M24配套；俯视只取相对方位。制造总图和绝对工艺方位待核。壁厚18、法兰厚20、螺栓孔Ø30为显示值，不能视为制造确认。

基础与塔架：原Ø2600圆基础、50厚二次浇筑、12-M24、四柱2400×2400菱形塔架均逐字节保留。局部对照沿用基础顶Z0、钢架楼面Z-300；原23.000楼面对应总装EL123，基顶EL123.300、架顶EL131.300。不擅自改动受力柱、斜撑或限位杆躲开接口。

安装：旧文字插点不能唯一确认设备中心，绝对X/Y及工艺方位仍待核，不进入总装、不计入全厂碰撞结论。钢架局部对照不能代替厂房安装确认。其他98项台账、72台已定位设备、27台待定位分类及建筑/桥架保持；1.0和原始资料保留。
'''
    (OUT/'整改说明.md').write_text(text)
    body=''.join('<p>'+html.escape(s)+'</p>' for s in text.strip().split('\n\n'))
    (OUT/'整改说明.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B02整改与待核项</title><style>'+STYLE+'</style><h1>尾气洗涤塔 · 来源、修正与待核项</h1><p><a href="index.html">模型/基础/塔架</a> · <a href="修订对比.html">1.0/2.0对照</a> · <a href="支承相交校核.json">相对支承校核</a> · <a href="安装待核.json">定位待核</a></p>'+body+f'<h2>钢塔架局部检查</h2><p>原模型相交构件对 {len(r["old_hits"])}，本次模型相交构件对 {len(r["new_hits"])}。仅此同心组合，绝对位置/方位未确认。</p><table><tr><th>设备构件</th><th>钢架构件（原索引）</th></tr>'+table+'</table><h2>原侧视与俯视</h2><img src="../../../示图建模_20260521/视图/L41B02_侧视.svg" alt="原侧视"><img src="../../../示图建模_20260521/视图/L41B02_俯视.svg" alt="原俯视">')
    (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B02尾气洗涤塔</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>尾气洗涤塔2.0 · <a href="整改说明.html">来源与待核项</a> · <a href="修订对比.html">1.0/2.0</a></header><iframe title="L41B02" src="../../../index.html?type=L41B02"></iframe></html>')
    (OUT/'修订对比.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B02新旧对照</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header,p{padding:12px}main{display:grid;grid-template-columns:1fr 1fr;height:calc(100vh - 100px)}iframe{width:100%;height:100%;border:1px solid #344957}a{color:#7cdce6}</style><header>尾气洗涤塔 · 1.0 / 2.0 · <a href="整改说明.html">图纸取舍与支承校核</a></header><main><iframe src="对照视图.html?old" title="1.0"></iframe><iframe src="对照视图.html" title="2.0"></iframe></main><p>本体局部Z0对照；厂房绝对位置待核。</p></html>''')
    (OUT/'对照视图.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}#label{position:absolute;top:14px;left:16px}canvas{width:100vw;height:100vh}</style><div id="label"></div><canvas id="scene"></canvas><script src="../../../orthographic_viewer.js"></script><script>const old=location.search.includes('old');document.getElementById('label').textContent=old?'1.0 · 原比例侧口/四托座':'2.0 · 侧视修正/底锚圈';const s=document.createElement('script');s.src=old?'../../1.0/快照/水解设备模型库/示图建模_20260521/模型/L41B02/model_data.js':'设备/model_data.js';s.onload=()=>{const v=createEquipmentViewer(document.getElementById('scene'),{doubleSided:true,centerProjection:true});v.setParts(window.MODEL_PARTS);v.view(-Math.PI/4,.2,'SE');v.fit();window.compareReady=true;};document.head.append(s);</script></html>''')
if __name__=='__main__':publish()
