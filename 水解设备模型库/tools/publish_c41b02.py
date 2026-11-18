"""Publish the first equipment revision with a readable, offline version comparison."""
from pathlib import Path
import json,csv,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B02'
def publish():
 placements=json.loads((OUT/'安装表.json').read_text())
 with (OUT/'安装对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['位号','X_mm','Y_mm','安装原点Z_mm','旋转_deg','Y镜像','1.0槽底EL','2.0型钢底EL','2.0槽底EL','2.0槽顶EL','2.0电机顶EL','承托间隙mm','状态'])
  for p in sorted(placements,key=lambda p:p['id']):w.writerow([p['id'],*p['position_mm'],p['rotation_deg'],p['mirror_y'],112.15,112.15,112.31,117.31,119.495,0,'POS定义/新接口方位待核'])
 rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [p['id'],p['position_mm'][0],p['position_mm'][1],p['rotation_deg'],'是' if p['mirror_y'] else '否','112.150','112.310'])+'</tr>' for p in sorted(placements,key=lambda p:p['id']))
 style='body{max-width:1100px;margin:40px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.9}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #34475c;text-align:left}img{max-width:100%;background:white}.pending{background:#453825;padding:16px;border:1px solid #806646}'
 text='''C41B02A—E · 第一类设备整改

1.0完整保存当前设备库、基础、72台安装表及27台待定位记录；2.0目前仅整改C41B02五台，其他94项不变。

已确认尺寸保留：槽体外径5500mm、直筒高5000mm、搅拌器高出槽体顶部2185mm。原搅拌、轴和叶轮保持形状，不重新缩放。

经用户选择，新盖面及外部接口采用新增《钛液预热槽总图》LMT0701-03-C3302-1：8组k检修盖，蒸汽进口b和冷凝水出口j各8处；另按管口表补a/p、c、d、e、f、n、g、h。新盖外径按φ5724，m安装框开口2900×1020。内部盘管、衬里、焊缝和螺栓细节不展开。

槽底新增H160型钢，按主视8×650=5200排布9道；I16截面细部与弦长端部属于展示包络。设备本体、底部型钢和土建基础可分别查看。

基础圆台几何不改：直径5700mm，总高150mm，其中50mm二次浇筑。圆台顶=设备型钢底，接触间隙为0mm。

安装链：楼面EL112.000 → 基础顶/型钢底EL112.150 → 槽底EL112.310 → 槽顶EL117.310 → 搅拌器顶EL119.495。设备安装原点仍放在原位置，含义明确改为型钢承托面；槽体及驱动在模型内上移160mm。

5台X/Y、旋转和镜像数值保留。新总图注明管口方位按工艺专业方位图，不能沿用旧6孔符号的匹配结论；这5台的新接口方位重新标待核。

待核与边界：POS EL112.150是否指型钢底仍需确认；第2—8张详图未提供。检修盖外径1000mm、b/j间距300mm、小口角度、法兰外廓和未明示厚度为量测/包络，不作为制造尺寸。φ5500保留用户确认外径，新图剖面内外径/底圈φ5560定义不作擅自替换。

模型几何和现有安装解释的相交检查与最终安装确认分别记录。该版本不是无待核项的施工模型。
'''
 (OUT/'整改说明.md').write_text(text,encoding='utf-8')
 doc='<html lang="zh-CN"><meta charset="utf-8"><title>C41B02第一类整改</title><style>'+style+'</style><h1>C41B02A—E · 2.0整改与对比</h1><p><a href="../../../index.html?type=C41B02">打开新模型与基础</a> · <a href="../../1.0/index.html">1.0冻结原版</a> · <a href="安装对照.csv">5台安装对照CSV</a> · <a href="校验报告.json">几何校验</a></p><div style="white-space:pre-wrap">'+html.escape(text)+'</div><table><tr><th>位号</th><th>X mm</th><th>Y mm</th><th>旋转°</th><th>Y镜像</th><th>型钢底EL</th><th>槽底EL</th></tr>'+rows+'</table><p><a href="来源与差异.json">来源取舍与差异</a> · <a href="设备/参数.json">全部参数与33条接口记录</a> · <a href="变更对比.json">新旧几何对比JSON</a></p>'
 for filename,title in [('来源_主视.png','新增总图主视（按原图核读，页面坐标不作设备实尺寸）'),('来源_俯视.png','新增总图俯视'),('来源_管口表.png','管口表'),('预览_设备与基础.png','设备与基础'),('预览_盖面.png','盖面与外部接口')]:
  if (OUT/filename).exists():doc+='<p>'+title+'</p><img src="'+filename+'" alt="'+title+'">'
 (OUT/'整改说明.html').write_text(doc+'</html>',encoding='utf-8')
 def wrapper(path,title,target):
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+title+'</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{height:40px;display:flex;align-items:center;justify-content:space-between;padding:0 20px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 40px);border:0}</style><header><b>'+title+'</b><a href="'+('C41B02/' if path.parent.name=='2.0' else '')+'整改说明.html">本类说明与待核项</a></header><iframe src="'+target+'" title="设备2.0"></iframe></html>')
 wrapper(ROOT/'版本/2.0/index.html','设备2.0 · 首批C41B02（安装待核）','../../index.html?type=C41B02')
 wrapper(OUT/'index.html','C41B02 · 新总图盖面与支承整改','../../../index.html?type=C41B02')
 (ROOT/'版本/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>设备版本与整改进度</title><style>'+style+'</style><h1>设备模块 · 版本与逐类进度</h1><p>35个位号组、99台/处。1.0为整改前冻结版；2.0按类别逐批更新，本批仅C41B02五台，其余94项保持。</p><table><tr><th>版本</th><th>范围</th><th>入口</th></tr><tr><td>1.0冻结版</td><td>全部现有类型、基础和原总装安装</td><td><a href="1.0/index.html">原设备库</a> · <a href="1.0/快照/水解总装工程/index.html">原安装总装</a></td></tr><tr><td>2.0工作版</td><td>C41B02新盖面/接口/型钢；安装解释及绝对方位待核</td><td><a href="2.0/index.html">查看新模型</a> · <a href="2.0/C41B02/整改说明.html">本类对比</a></td></tr></table><p class="pending">明确尺寸、图面量测和展示假设分别记录。POS EL定义、新接口绝对方位仍待核；不将零碰撞视为安装已确认。</p><p>下一类：C41B04偏钛酸冷却器。当前建筑和桥架2.0几何未改。</p><p><a href="../../水解总装工程/index.html">当前总装</a> · <a href="../data/设备整改问题清单_35组99台.csv">99项原始整改清单</a></p></html>')
 print('Published C41B02 review, placement CSV and 1.0/2.0 entries.')
if __name__=='__main__':publish()
