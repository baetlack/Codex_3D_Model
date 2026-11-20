"""F41B04 datum review: unchanged tube, explicit installation and unresolved dimensions."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/F41B04'
STYLE='body{max-width:1100px;margin:30px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.85}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{border-bottom:1px solid #344957;padding:10px;text-align:left}'
def publish():
    p=json.loads((OUT/'设备/参数.json').read_text());measure=json.loads((OUT/'俯侧视量测.json').read_text())
    text='''F41B04 尾气烟囱 · 2.0-F41B04-01

本轮重点是安装基准与基础配合。当前本体已按增补钢塔架背立面采用Ø1000×15100，本次完整保留其网格、法线、材质和GLB/OBJ，不为增加细节而补造接口、底法兰或连接孔。

高度取舍：台账水解页第53行为Ø1000×17000；旧设备示图2582为1000×11000；增补钢塔架背立面8DFD/8DFF实量1000×15098.60，当前15100为其圆整显示值。三者差异未解决，本次保留现有15100，不能认定为整机制造高度。新版平面8F98圆外径约1099.76，与立面/台账1000不同，继续待核，不据此放大筒体。原壁厚16仍为显示值。

安装修正：背立面8ED2明确300，端点Y76130.852为23.000楼面、Y76430.852为筒底/基础顶。按EL100为总装Z0换算，楼面EL123.000，筒底及基础顶EL123.300。旧总装把筒底放在23000且未实例化圆基础，本次筒底Z改23300、X26000/Y31900及零旋转保持，并补入Ø1400×300圆基础，基础底23000、顶23300。原模型显示筒顶随之为EL138.400，整机高度差异仍待核。

圆基础与钢塔架：原混凝土/50厚二次浇筑、PCD1200/12-M24及200mm露头、153件钢塔架均逐字节保留。只有圆基础进入厂房总装。塔架方位尚未确认，继续仅供独立局部对照；原mount=-300表示筒底/基顶Z0、钢架楼面Z-300，不能当作厂房安装方案。

锚固限制：原模型只有直筒，没有设备底部连接板及螺栓孔详图。地脚螺栓在筒体外侧，径向净距约88mm；几何上不相交不能说明锚固已经连接。本轮不补造法兰、支腿或地脚孔来闭合该关系。钢架限位杆间隙按原网格量测记录，不以挪杆强行贴合。

图纸追溯：屋面定位圆33EAC、增补塔架8DFD/8DFE/8DFF、8ED2/8ED8、8E0F及8F98、专用烟囱基础图3142/3114等。1.0、其他98项台账与71条设备位置、原基础、建筑和桥架保持。
'''
    (OUT/'整改说明.md').write_text(text)
    body=''.join('<p>'+html.escape(q)+'</p>' for q in text.strip().split('\n\n'))
    review=OUT/'校验报告.json';r=json.loads(review.read_text()) if review.exists() else {}
    summary='<p>本类校核完成后记录局部相交、限位间隙与新增基础的空间检查。</p>'
    if r:summary=f'<p>筒体/钢架局部相交 {r["relative_frame_pairs"]} 对，筒体/基础局部相交 {r["relative_base_pairs"]} 对，本次筒体和基础的空间检查相交 {len(r["world_intersections"])} 对。表面接触正常；锚固及塔架方位仍待核。</p>'
    table='''<table><tr><th>项目</th><th>原总装</th><th>本次</th></tr><tr><td>X / Y</td><td>26000 / 31900</td><td>保持</td></tr><tr><td>筒底Z</td><td>23000</td><td>23300（EL123.300）</td></tr><tr><td>圆基础</td><td>未实例化</td><td>底23000 / 顶23300</td></tr><tr><td>筒体网格/显示高度</td><td>Ø1000×15100</td><td>逐字节保持；高度差异待核</td></tr><tr><td>钢塔架</td><td>独立对照</td><td>保持；不入总装</td></tr></table>'''
    (OUT/'整改说明.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>F41B04安装基准与待核项</title><style>'+STYLE+'</style><h1>尾气烟囱 · 安装修正与图纸差异</h1><p><a href="index.html">独立查看</a> · <a href="安装表.json">安装表</a> · <a href="支承复核.json">锚固/限位记录</a> · <a href="俯侧视量测.json">句柄与量测</a> · <a href="../../1.0/index.html">1.0原版</a></p>'+table+body+summary)
    (OUT/'安装对照.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>F41B04安装对照</title><style>'+STYLE+'</style><h1>烟囱安装前后对照</h1>'+table+'<p>筒体外形与导出不变，本次修正安装高差并补基础。原版保留在设备1.0。</p><a href="整改说明.html">来源及未决差异</a> · <a href="../../../index.html?type=F41B04">查看当前模型</a>')
    (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>尾气烟囱2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>尾气烟囱2.0 · <a href="整改说明.html">来源与待核项</a> · <a href="安装对照.html">安装前后</a> · <a href="../../../../水解总装工程/index.html">总装</a></header><iframe title="F41B04" src="../../../index.html?type=F41B04"></iframe></html>')
if __name__=='__main__':publish()
