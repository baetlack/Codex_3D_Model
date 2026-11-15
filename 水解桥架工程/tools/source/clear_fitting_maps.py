"""One fitting per panel, preserving the existing checklist IDs."""
import csv,json,re,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
root=Path(__file__).parent
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
rows=list(csv.DictReader((root/'fitting_checklist.csv').open(encoding='utf-8-sig')))
objs={o['handle']:o for o in json.loads((root/'tray_objects.json').read_text(encoding='utf-8-sig'))}
paths={}
for s in (root/'tray_paths.txt').read_text(errors='replace').splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)',s)
 if m:paths[m[1]]=[[float(v) for v in m[i].split()] for i in (2,3)]
out=root/'连接件定位详图';out.mkdir(exist_ok=True)
links=[]
for layer in range(1,4):
 group=[r for r in rows if int(r['层序'])==layer]
 for page in range(math.ceil(len(group)/6)):
  batch=group[page*6:page*6+6]
  fig,axes=plt.subplots(2,3,figsize=(18,13),facecolor='white')
  fig.subplots_adjust(top=.87,bottom=.07,hspace=.65,wspace=.28)
  fig.suptitle(f'第{layer}层 · 连接件逐个定位（第{page+1}页）',fontsize=23,y=.98)
  fig.text(.5,.935,'每格只定位一个编号：红色十字为目标，灰点为附近其他配件；彩线按对象 Z 着色。',ha='center',fontsize=13)
  fig.text(.5,.91,'坐标单位 m，采用原 CAD 坐标。Z 为对象原始值；红色框仅为配件平面包围范围，不代表实际形状。',ha='center',fontsize=11,color='#555555')
  for ax,r in zip(axes.flat,batch):
   ident=r['编号'];o=objs[r['DWG句柄']];x=float(r['CAD中心X_mm'])/1000;y=float(r['CAD中心Y_mm'])/1000;z=float(r['CAD中心Z_mm'])/1000
   a,b=o['bounds'];radius=max(1.8,(b[0]-a[0])/1000+1,(b[1]-a[1])/1000+1)
   radius=min(radius,6)
   for h,ends in paths.items():
    if objs.get(h,{}).get('type')!='TDbECabletry':continue
    p,q=ends
    if max(p[0],q[0])/1000<x-radius or min(p[0],q[0])/1000>x+radius or max(p[1],q[1])/1000<y-radius or min(p[1],q[1])/1000>y+radius:continue
    color=plt.cm.viridis(min(1,max(0,(p[2]+q[2])/2/6500)))
    ax.plot([p[0]/1000,q[0]/1000],[p[1]/1000,q[1]/1000],color=color,lw=3,solid_capstyle='round')
    if abs(p[0]-q[0])+abs(p[1]-q[1])<1:
     ax.scatter(p[0]/1000,p[1]/1000,marker='s',s=65,facecolors='none',edgecolors=color,linewidths=2)
   coloc=[]
   for other in group:
    if other['编号']==ident:continue
    xx=float(other['CAD中心X_mm'])/1000; yy=float(other['CAD中心Y_mm'])/1000
    if abs(xx-x)<radius and abs(yy-y)<radius:
     ax.scatter(xx,yy,s=25,color='#aaaaaa',zorder=4)
     if abs(xx-x)<.05 and abs(yy-y)<.05:coloc.append(other['编号'])
   ax.add_patch(Rectangle((a[0]/1000,a[1]/1000),max(.04,(b[0]-a[0])/1000),max(.04,(b[1]-a[1])/1000),fill=False,edgecolor='#d62935',lw=1.6,linestyle='--'))
   ax.scatter(x,y,s=190,marker='+',color='#d62935',linewidths=2.6,zorder=8)
   ax.set_xlim(x-radius,x+radius);ax.set_ylim(y-radius,y+radius);ax.set_aspect('equal');ax.grid(color='#dddddd',lw=.6)
   ax.ticklabel_format(useOffset=False,style='plain');ax.tick_params(labelsize=9)
   ax.set_xlabel('CAD X (m)',fontsize=10);ax.set_ylabel('CAD Y (m)',fontsize=10)
   ax.set_title(f'{ident}  |  句柄 {r["DWG句柄"]}\n{r["宽mm"]}×{r["高mm"]} mm  |  Z={z:.3f} m',fontsize=13,pad=10)
   if coloc:ax.text(.02,.02,'同XY位置：'+', '.join(coloc),transform=ax.transAxes,fontsize=9,color='#c02020',bbox=dict(facecolor='white',alpha=.9,edgecolor='none'))
  for ax in list(axes.flat)[len(batch):]:ax.axis('off')
  fig.text(.5,.018,'截图时请使用本页编号；保留目标连接件及相邻直段，升降连接件请给三维视角。',ha='center',fontsize=12)
  name=f'L{layer}_detail_{page+1:02d}.png';fig.savefig(out/name,dpi=150);plt.close(fig)
  links.append((layer,','.join(r['编号'] for r in batch),name))
lines=['# 连接件清晰定位图','','原编号不变，每个连接件独立一格。红十字对应目标配件，避免密集编号遮挡。','']
for n,ids,name in links:lines.append(f'- 第{n}层 {ids}：[打开详图]({name})')
(out/'索引.md').write_text('\n'.join(lines),encoding='utf-8')
print('\n'.join(f'{n}: {ids}: {name}' for n,ids,name in links))
