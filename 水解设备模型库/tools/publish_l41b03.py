"""Publish L41B03 scope, evidence and side-by-side revision views."""
from pathlib import Path
import html,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/L41B03'
STYLE='body{margin:28px auto;max-width:1120px;padding:0 24px;background:#101923;color:#dce8ef;font:15px/1.8 sans-serif}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{padding:9px;border:1px solid #38505f;text-align:left}img{max-width:100%}'
def publish():
    text='''L41B03 旋流除雾器 · 2.0

按用户选择保留台账Ø1800×3100：3100沿用锥尖至顶法兰口径，底排接管另计。本体原示图实量Ø2000、锥尖至顶法兰约4168，差异未解决；没有厂家总图，本轮按台账主尺寸对原图分别作平面0.9和竖向比例表达，不将接口和托耳的图面量测标为制造尺寸。

上封头按椭圆轮廓，修正顶部口、东侧下口、北侧偏东上口和锥底排口。局部XY延续旧模型相对原俯视逆时针90°的轴向，尚未确认厂房绝对工艺方位。接口DN、壁厚、法兰厚及筋板厚等待详图；不加推断地脚孔、法兰螺栓或内部叶片。

原示图模型含4根立柱和4段横梁，旧净模运行时已过滤。本轮直接保存不含旧框架的新本体，原净模22件改为23件，保留四向托耳。本体与专用钢架分开；原31件钢支架及导出逐字节保持。原设备示图框架高3000，专用基础图钢架高2000；本轮只使用专用钢架作局部对照，不能把两套框架重复组合。

新本体以四托耳底为Z0。局部组合设备偏移[0,-175,2000]，托耳对齐钢架顶2000、中心对齐2050开口的中心Y-175。基础图楼面23.000/承托25.000仅用于相对标高；钢架绝对X/Y、设备中心与工艺方位未核，仍保留27台待定位，本类不加入总装。

1.0、原始图纸、已确认的其他设备、建筑和桥架保留。四托耳与支架的接触和本体/接口穿插结果见支承复核；模型接触不代替结构承载和制造详图。
'''
    (OUT/'整改说明.md').write_text(text)
    body=''.join('<p>'+html.escape(p)+'</p>' for p in text.split('\n\n'))
    report=OUT/'支承复核.json';r=json.loads(report.read_text()) if report.exists() else {}
    summary=''
    if 'intersections' in r:summary=f'<p>局部复核：实体相交{len(r["intersections"])}对；四耳有效接触{len(r["bearing_contacts"])}处。接触面积及模型限制详见JSON记录。</p>'
    nav='<p><a href="index.html">当前模型</a> · <a href="修订对比.html">1.0/2.0外形对比</a> · <a href="俯侧视量测.json">句柄与比例</a> · <a href="安装待核.json">安装待核</a> · <a href="支承复核.json">支承复核</a></p>'
    images=''.join(f'<p>{label}（原始示图，不是厂家确认尺寸）</p><img src="{name}" alt="{label}">' for name,label in [('来源_侧视.png','原侧视'),('来源_俯视.png','原俯视')])
    (OUT/'整改说明.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B03整改说明</title><style>'+STYLE+'</style><h1>旋流除雾器 · 本体与支架分离</h1>'+nav+body+summary+images)
    (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>旋流除雾器2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>旋流除雾器2.0 · <a href="整改说明.html">来源与待核</a> · <a href="修订对比.html">新旧对照</a></header><iframe title="L41B03" src="../../../index.html?type=L41B03"></iframe></html>')
    (OUT/'修订对比.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>L41B03修订对比</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:12px}a{color:#7cdce6}.views{display:grid;grid-template-columns:1fr 1fr}iframe{width:100%;height:calc(100vh - 90px);border:0}</style><header>左：1.0净模 · 右：2.0（本体/支架独立） · <a href="整改说明.html">取舍与安装待核</a><p>主尺寸仍Ø1800×3100；各视图可独立旋转，底排接管另计；新本体以托耳底Z0。</p></header><div class="views"><iframe title="1.0" src="../../1.0/快照/水解设备模型库/index.html?type=L41B03"></iframe><iframe title="2.0" src="../../../index.html?type=L41B03"></iframe></div>')
if __name__=='__main__':publish()
