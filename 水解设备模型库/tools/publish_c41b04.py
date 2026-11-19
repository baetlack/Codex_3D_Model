"""Publish C41B04 source decisions, geometry comparison and installed supports."""
from pathlib import Path
import csv,json,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B04'
def publish():
    p=json.loads((OUT/'设备/参数.json').read_text());difference=json.loads((OUT/'来源与差异.json').read_text());installs=json.loads((OUT/'安装表.json').read_text());f=json.loads((OUT/'支架/参数.json').read_text())
    policy={'pending':'AB/CD组间距200mm差异暂按两图分别保留，AB组南北两只托耳不能标作贴合验收。','layout':'按用户选择保留设备布置位置，AB组钢架随设备调整约200mm。','move-equipment':'按用户选择采用钢架基础图4200mm，AB两台设备北移200mm。'}[f['frame_policy']]
    text=f'''C41B04A—F · 偏钛酸冷却器 · {p['version']}

精度与风格：沿用用户接受的C41B02-02工程展示精度；明确尺寸依图取值，未标细部继续注明图面量测。设备1.0及全部旧源文件保留。

设备依据：厂家条件图SS-XYK1200-240S(10)，Rev.0（2026.01.09），图面签字2026.4.14；原PDF文件名“偏钛酸酸冷却器(C41B04A-F).pdf”。原台账230㎡、部分旧逐台参数240㎡、新条件图240㎡存在容量口径差异；本次几何按该条件图明确尺寸，不以面积比例缩放设备。

本体与接口：壳体Ø1300、换热块规格Ø1200分别记录；端面间4812mm，顶部端面至托耳承托面2200mm。改为四向托耳，孔位对边1875、最外对边2055、孔Ø30；N1/N2两只DN200顶口位于±240、+390；N3/N4为270°侧DN300，端面距中心858，中心距下/上端分别830/802；N5/N6为90°侧DN32，伸出120；N7a—e五只DN50底部排净口按Ø800圆及布置图位置建立。

取消旧中央顶口、两只大底口及四处相同的示意侧口。补可见端部压板、拉杆、弹簧和吊耳；20组拉杆孔位参考布置DXF。内部石墨流道及10流程不展开。弹簧最高另计约200mm外观包络，不把它并入4812mm明示端面高度。法兰未标厚度、过渡段、弹簧、吊耳及N5/N6准确标高属于外观量测。

支架：单组梁网4275×1875、顶高4500，设备中心距2400；GZ1/GL1/ZC1截面继续沿用原基础模型展示口径。设备与钢架分文件，提供三组组合及单组模型；总装补入三组钢架。{policy}

安装：设备局部Z0为托耳底，全局承托EL104.500；底端EL101.888、顶端EL106.700，弹簧上包络约EL106.900。四耳孔位在单组钢架梁网有明确对应。除上述位置策略明确的AB差异外，6台X/Y和原图旋转/镜像保持。两个顶口的+Y方向已与EL106顶视图核对，避免沿用旧模型的反向布置。

其余设备及已接受的C41B02本体/基础/安装、建筑和桥架源几何均不改。碰撞校核单列钢架，不将正常托耳承托面接触报作穿入。建筑梁架、楼板孔边及相邻设备的新增接触需按本类检查记录判断，不用零碰撞代替支承验收。
'''
    (OUT/'整改说明.md').write_text(text)
    style='body{max-width:1150px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.8}a{color:#7cdce6}img{max-width:100%}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #344957;padding:10px;text-align:left}'
    doc='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>C41B04整改与资料整合</title><style>'+style+'</style><h1>C41B04 · 偏钛酸冷却器</h1><p><a href="../../../index.html?type=C41B04">当前设备与钢架</a> · <a href="修订对比.html">1.0/2.0三维对照</a> · <a href="../../../水解设备图纸/偏钛酸酸冷却器(C41B04A-F).pdf">厂家条件图PDF</a> · <a href="../../1.0/index.html">设备1.0</a></p><div style="white-space:pre-wrap">'+html.escape(text)+'</div><p><a href="设备/参数.json">本体参数</a> · <a href="来源与差异.json">资料取舍与冲突</a> · <a href="安装对照.csv">逐台安装表</a> · <a href="校验报告.json">本类检查</a></p>'
    for image,caption in [('来源_主视.png','厂家主视'),('来源_俯视.png','厂家俯视'),('预览_设备与钢架.png','当前设备与钢架'),('预览_设备.png','当前单台设备'),('预览_新旧对照.png','承托面Z0对齐的新旧对照')]:
        if (OUT/image).exists():doc+='<h2>'+caption+'</h2><img src="'+image+'" alt="'+caption+'">'
    (OUT/'整改说明.html').write_text(doc+'</html>')
    (OUT/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>C41B04设备2.0</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}a{color:#7cdce6}header{padding:10px 20px}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>C41B04 · 偏钛酸冷却器 <a href="整改说明.html">来源/安装差异</a> · <a href="修订对比.html">新旧对照</a></header><iframe title="当前冷却器与钢架" src="../../../index.html?type=C41B04"></iframe></html>')
    with (OUT/'安装对照.csv').open('w',encoding='utf-8-sig',newline='') as file:
        w=csv.writer(file);w.writerow(['位号','X_mm','Y_mm','托耳底Z_mm','旋转_deg','Y镜像','底端EL','顶端EL','位置策略'])
        for i in installs:w.writerow([i['id'],*i['position_mm'],i['rotation_deg'],i['mirror_y'],101.888,106.7,f['frame_policy']])
    from publish_equipment_index import publish as index
    index()
if __name__=='__main__':publish()
