import json,csv,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent
objs=json.loads((root/'tray_objects.json').read_text(encoding='utf-8-sig'))
fits=[o for o in objs if o['type']=='TDbEFitting']
paths={}
for line in (root/'tray_paths.txt').read_text(errors='replace').splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)\)',line)
 if m: paths[m[1]]=[[float(v) for v in m[i].split()] for i in (2,3)]
def layer(x):return 1 if x<390000 else 2 if x<500000 else 3
records=[]
fig,axes=plt.subplots(1,3,figsize=(17,12),facecolor='#101926')
for n,ax in enumerate(axes,1):
 group=[o for o in fits if layer(o['bounds'][0][0])==n]
 group.sort(key=lambda o:(o['bounds'][0][1],o['bounds'][0][0],o['bounds'][0][2]))
 trays=[o for o in objs if o['type']=='TDbECabletry' and o['handle'] in paths and layer(paths[o['handle']][0][0])==n]
 ox=min(p[0] for o in trays for p in paths[o['handle']]);oy=min(p[1] for o in trays for p in paths[o['handle']])
 ax.set_facecolor('#101926')
 for o in trays:
  a,b=paths[o['handle']];ax.plot([(a[0]-ox)/1000,(b[0]-ox)/1000],[(a[1]-oy)/1000,(b[1]-oy)/1000],color='#43cddd',lw=1)
 for i,o in enumerate(group,1):
  ident=f'L{n}-C{i:02d}';a,b=o['bounds'];p=o['properties'];center=[(a[k]+b[k])/2 for k in range(3)]
  near=[]
  for t in trays:
   dist=min(sum((q[k]-center[k])**2 for k in range(3))**.5 for q in paths[t['handle']])
   if dist<2200:near.append((dist,t['handle']))
  near.sort()
  row=[ident,o['handle'],n,p.get('Type'),p.get('Width'),p.get('Height'),*[round(v,2) for v in center],','.join(h for _,h in near[:4]),'待截图确认']
  records.append(row)
  x,y=(center[0]-ox)/1000,(center[1]-oy)/1000
  ax.scatter(x,y,s=16,color='#ffbd59')
  dx=12 if i%2 else -45;dy=(i%4-1.5)*12
  ax.annotate(ident,(x,y),xytext=(dx,dy),textcoords='offset points',fontsize=7,color='#ffce82',arrowprops=dict(arrowstyle='-',color='#b58c54',lw=.5))
 ax.set_title(f'Layer {n} | {len(group)} missing fittings',color='white')
 ax.set_xlabel('local X (m)',color='white');ax.set_ylabel('local Y (m)',color='white');ax.tick_params(colors='white');ax.grid(alpha=.15);ax.set_aspect('equal');ax.margins(.2)
fig.suptitle('Fitting checklist — IDs refer to original DWG handles',color='white',fontsize=17)
fig.tight_layout();fig.savefig(root/'fitting_locations.png',dpi=160,facecolor=fig.get_facecolor())
headers=['编号','DWG句柄','层序','原始Type','宽mm','高mm','CAD中心X_mm','CAD中心Y_mm','CAD中心Z_mm','附近桥架句柄_仅供定位','状态']
with (root/'fitting_checklist.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.writer(f);w.writerow(headers);w.writerows(records)
lines=['# 三层桥架连接件补齐清单','','按CAD平面从左到右暂记第1、2、3层。共47个原始配件，均待补形。坐标为原CAD坐标，Z基准待核实。附近桥架由端点距离筛选，不代表已确认连接。','','截图请标编号，包含配件及相邻直段；变标高件请提供能看清升降方向的三维视角。','']
for n in range(1,4):
 lines += [f'## 第{n}层','','|编号|DWG句柄|原始Type|宽×高 mm|CAD中心 XYZ mm|','|---|---|---|---|---|']
 for r in records:
  if r[2]==n:lines.append(f'|{r[0]}|{r[1]}|{r[3]}|{r[4]}×{r[5]}|{r[6]}, {r[7]}, {r[8]}|')
 lines.append('')
(root/'连接件补齐清单.md').write_text('\n'.join(lines),encoding='utf-8')
for n in range(1,4): print(n,sum(r[2]==n for r in records))
