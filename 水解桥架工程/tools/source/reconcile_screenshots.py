from pathlib import Path
import csv,json,re,hashlib
from collections import Counter
root=Path(__file__).parent
base={r['编号']:r for r in csv.DictReader((root/'fitting_checklist.csv').open(encoding='utf-8-sig'))}
# Visual classification from all 47 user screenshots. Names describe the displayed
# shape rather than the user-editable CAD model string.
kinds={
1:['水平弯头','水平三通','水平三通','水平三通','水平弯头','垂直下弯','乙字弯','水平弯头','垂直上弯'],
2:['水平弯头','水平三通','上坡过渡','下坡过渡','水平三通','上坡过渡','下坡过渡','水平三通','垂直上弯','垂直下弯','水平弯头','下坡过渡','水平三通','垂直上弯','水平三通','垂直上弯','垂直下弯','乙字弯','水平弯头','水平弯头','下坡过渡'],
3:['垂直上弯','垂直下弯','垂直三通','垂直下弯','垂直三通','水平三通','垂直下弯','垂直上弯','水平弯头','乙字弯','水平弯头','水平三通','水平三通','偏置变径','垂直下弯','水平弯头','垂直三通']}
swap={2:3,3:2,4:5,5:4,7:8,8:7,15:17,17:15}
records=[]; hashes=[]
for f in sorted((root/'连接件').glob('*.png')):
 m=re.match(r'L(\d)C(\d+)',f.stem);level,num=map(int,m.groups());src=f'L{level}-C{num:02d}'
 target=f'L{level}-C{swap.get(num,num):02d}' if level==3 else src
 b=base[target]
 digest=hashlib.sha256(f.read_bytes()).hexdigest();hashes.append(digest)
 records.append({'截图':f.name,'文件名编号':src,'建议对应模型编号':target,'DWG句柄':b['DWG句柄'],'形状识别':kinds[level][num-1],
 '定位依据':'截图标高、截面与上下连接形状交叉匹配，建议对调' if src!=target else '暂沿用原编号；需随模型端口校验',
 'DWG宽mm':b['宽mm'],'DWG高mm':b['高mm'],'DWG_Z_mm':b['CAD中心Z_mm'],
 '状态':'形状已识别；几何尚未补建','SHA256':digest})
with (root/'连接件截图核对表.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
(root/'fitting_screenshot_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
lines=['# 47张连接件截图核对记录','','已逐张查看截图。第1层9张、第2层21张、第3层17张。文件内容哈希无完全相同文件；这不代表已证明几何对应关系无重复。','','## 第三层建议更正的对应关系','','以下根据截图中的标高、截面、三通/弯头形状交叉判断，保留原文件名，仅在对应表中记录。最终还需校验实际端口位置。','','|截图编号|建议模型编号|判断依据|','|---|---|---|',
'|L3-C02|L3-C03|截图为Z=3 m、200×200垂直下弯|',
'|L3-C03|L3-C02|截图为Z=6 m、200×200垂直三通|',
'|L3-C04|L3-C05|截图为Z=3 m、200×100垂直下弯|',
'|L3-C05|L3-C04|截图为Z=6.2 m垂直三通，主管500、支路200|',
'|L3-C07|L3-C08|截图为Z=4.9 m、200×200垂直下弯|',
'|L3-C08|L3-C07|截图为Z=6.2 m、200×200垂直上弯|',
'|L3-C15|L3-C17|截图为Z=3 m、200×200垂直下弯|',
'|L3-C17|L3-C15|截图为Z=6 m、200×200垂直三通|',
'','## 建模要点','','- 不可用原对象Type字符串判断实际形状：第二层C11等截图显示水平弯头，但Type仍为通用型号字符串。',
'- 三通的DWG Width并非三个口的宽度；例如第一层C02～C04截图的主管800 mm、支路200 mm，应分别建模。',
'- 第三层C14为偏置变径：截图给出L=500 mm、B1=300 mm、B2=500 mm、H1=H2=200 mm、Z=6 m。',
'- 乙字弯和坡段截图提供了形状，精确偏移量及高差需结合相邻桥架端点，不能仅按截图比例量取。',
'- 本次输出是截图与对象的核对记录，不是连接件已完成建模的声明。','','## 全部截图分类','','|截图|建议对应模型编号|识别形状|','|---|---|---|']
for r in records:lines.append(f'|{r["截图"]}|{r["建议对应模型编号"]}|{r["形状识别"]}|')
(root/'连接件截图核对说明.md').write_text('\n'.join(lines),encoding='utf-8')
print('Total:',len(records),'Unique file hashes:',len(set(hashes)))
print('Shapes:',dict(Counter(r['形状识别'] for r in records)))
print('Suggested reassociations:',sum(r['文件名编号']!=r['建议对应模型编号'] for r in records))
