"""Publish the corrected roof/side revision, preserving 01 and the complete equipment 1.0."""
from pathlib import Path
import json,csv,html
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B02'
def publish():
 params=json.loads((OUT/'设备/参数.json').read_text());revision=params['version'];placements=json.loads((OUT/'安装表.json').read_text())
 with (OUT/'安装对照.csv').open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.writer(f);w.writerow(['位号','X_mm','Y_mm','安装原点Z_mm','旋转_deg','Y镜像','型钢底EL','槽底EL','槽顶EL','电机顶EL','本次基础/底钢/安装变换','状态'])
  for p in sorted(placements,key=lambda p:p['id']):w.writerow([p['id'],*p['position_mm'],p['rotation_deg'],p['mirror_y'],112.15,112.31,117.31,119.495,'不变','POS定义/新接口绝对方位待核'])
 rows=''.join('<tr>'+''.join('<td>'+html.escape(str(v))+'</td>' for v in [p['id'],p['position_mm'][0],p['position_mm'][1],p['rotation_deg'],'是' if p['mirror_y'] else '否','112.150','112.310'])+'</tr>' for p in sorted(placements,key=lambda p:p['id']))
 style='body{max-width:1100px;margin:40px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.9}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{padding:10px;border-bottom:1px solid #34475c;text-align:left}img{max-width:100%;background:white}.pending{background:#453825;padding:16px;border:1px solid #806646}'
 text=f'''C41B02A—E · 顶部与侧面二次修正 · {revision}

依据：新增《钛液预热槽总图》LMT0701-03-C3302-1的俯视、主视、g/h/c/d/e/f/n局部结构与明细表。原图、完整设备1.0及上一工作版01均保留。

本次基础、底部型钢、槽体与5台安装变换保持。槽体外径5500mm、直筒高5000mm、搅拌器高出槽体顶2185mm不变；电机、联轴器、中间轴和内部轴/叶轮沿用确认总成。支架下段改为图示圆筒开窗轮廓，φ600底座、φ490架体与新m高座衔接；传动装置-6详图尚未提供，不从总图示意轮廓直接改写已确认的驱动尺寸。

本次修正：
1. m安装座：由贴盖的40mm薄框改为280mm高座、30mm顶板及对开盖板，开口2900×1020mm；顶板外轮廓约3064×1150mm按校准俯视量测。补两处400mm踏步板轮廓，厚度/准确安装层位仍是外观表达。
2. k安装口：8个中心在φ4200圆周，22.5°起每45°一处。盖板/垫片外径按明细表φ1075，垫片φ1075/φ940、厚3mm，补中央共座法兰、φ400/φ350垫片和双孔盖板。
3. b/j：两管沿切向排列、中心距250mm；原版误用了径向300mm。两管通过共盖板，按管口表外伸150mm，主视中的177mm相对高差单列核对。
4. 小口位置：用图上φ5724外圈校准转曲图，再从闭合圆轮廓提取。a/p约49.74°，e约230.57°；f在φ4200圆周、约317.23°，没有再统一套用φ4800。其余小口也逐孔对照。
5. a/p：拆成同轴套管与插入管，上下法兰分别表现；c/e/f保持开口接管；d补带竖柄取样盖；n按局部图改为φ340盲板、φ295螺栓圆。
6. g/h侧口：取消锥形管，改为同轴大端直套管、连接法兰/垫片、外端直短接和端法兰。g大端φ377、h大端φ273，h外端φ159；详图外伸链为200+13+200mm。管口表400mm保留为名义伸出记录，413mm详图链与连接面定义不混用。口内保留空腔，未展开隐藏衬里。

基础保持：φ5700×150mm、其中50mm二次浇筑；基础文件与01版逐字节比较。底部型钢27个网格对象与01版一致。

现有安装解释保持：基础顶/型钢底EL112.150，槽底EL112.310，槽顶EL117.310，电机顶EL119.495。X/Y、旋转和镜像未改变；POS定义与新接口工艺绝对方位仍待核，没有将本次相对几何校核当作现场安装确认。

依据强度：明示尺寸（280/30、1075/940、400/350、340/295、200/13/200等）按图取值；孔中心/未标法兰外廓按校准图面量测；局部板厚、踏步板安装细部及缺失零件详图继续标示意。孔位对图校核的数值仅表示模型吻合本张图，不是图纸或施工公差。

对比资料：顶侧结构图面量测.json、顶侧结构独立校验.json、顶侧二次修正对比.json、孔位偏差对比.json；可在修订对比.html中并排旋转查看01/02及g/h局部。旧01版的参数、模型、图和脚本冻结在历史/2.0-C41B02-01。
'''
 (OUT/'整改说明.md').write_text(text,encoding='utf-8')
 doc='<html lang="zh-CN"><meta charset="utf-8"><title>C41B02顶侧结构修正02</title><style>'+style+'</style><h1>C41B02A—E · 顶侧结构修正02</h1><p><a href="../../../index.html?type=C41B02">当前模型与基础</a> · <a href="修订对比.html">01/02并排对照</a> · <a href="../../1.0/index.html">设备1.0冻结原版</a> · <a href="安装对照.csv">5台安装对照CSV</a></p><div style="white-space:pre-wrap">'+html.escape(text)+'</div><table><tr><th>位号</th><th>X mm</th><th>Y mm</th><th>旋转°</th><th>Y镜像</th><th>型钢底EL</th><th>槽底EL</th></tr>'+rows+'</table><p><a href="顶侧结构独立校验.json">独立对图校验</a> · <a href="设备/参数.json">当前参数</a> · <a href="来源与差异.json">来源与差异</a></p>'
 for filename,title in [('图面校核_俯视新旧.png','孔位新旧对图'),('图面校核_双管与侧口.png','b/j与侧口结构'),('依据_小口详图.png','小口局部结构'),('依据_侧口详图.png','g/h侧口局部结构'),('依据_明细表.png','明细表'),('预览_设备与基础.png','本次模型与保留的基础'),('预览_盖面.png','本次顶部')]:
  if (OUT/filename).exists():doc+='<p>'+title+'</p><img src="'+filename+'" alt="'+title+'">'
 (OUT/'整改说明.html').write_text(doc+'</html>',encoding='utf-8')
 def wrapper(path,title,target):
  path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>'+title+'</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{height:40px;display:flex;align-items:center;justify-content:space-between;padding:0 20px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 40px);border:0}</style><header><b>'+title+'</b><a href="'+('C41B02/' if path.parent.name=='2.0' else '')+'整改说明.html">本类说明与对图</a></header><iframe src="'+target+'" title="设备2.0"></iframe></html>')
 wrapper(ROOT/'版本/2.0/index.html','设备2.0 · C41B02顶侧修正02','../../index.html?type=C41B02')
 wrapper(OUT/'index.html','C41B02 · 顶侧结构修正02','../../../index.html?type=C41B02')
 (ROOT/'版本/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>设备版本与整改进度</title><style>'+style+'</style><h1>设备模块 · 版本与逐类进度</h1><p>35个位号组、99台/处。当前C41B02已更新到顶侧结构修正02；基础、底部型钢和其余94项保持。</p><table><tr><th>版本</th><th>内容</th><th>入口</th></tr><tr><td>设备1.0冻结</td><td>整改前设备及安装</td><td><a href="1.0/index.html">原设备库</a></td></tr><tr><td>设备2.0当前</td><td>C41B02修正02</td><td><a href="2.0/index.html">当前模型</a> · <a href="2.0/C41B02/修订对比.html">01/02结构对照</a></td></tr></table><p><a href="2.0/C41B02/整改说明.html">本次图纸取值和校验</a> · <a href="../../水解总装工程/index.html">当前总装</a></p><p class="pending">POS定义与工艺绝对方位仍待核；图面量测、缺失详图与未标尺寸均单独说明。</p></html>')
 from publish_equipment_index import publish as publish_index
 publish_index()
 print('Published C41B02 revision 02 and 01/02 comparison.')
if __name__=='__main__':publish()
