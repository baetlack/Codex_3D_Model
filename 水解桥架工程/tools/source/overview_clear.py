import csv,json,re
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans']
plt.rcParams['axes.unicode_minus']=False
rows=list(csv.DictReader((root/'fitting_checklist.csv').open(encoding='utf-8-sig')))
objects=json.loads((root/'tray_objects.json').read_text(encoding='utf-8-sig'))
types={o['handle']:o['type'] for o in objects}
paths={}
for line in (root/'tray_paths.txt').read_text(errors='replace').splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)',line)
 if m:paths[m[1]]=[[float(v) for v in m[i].split()] for i in (2,3)]
def layer(x):return 1 if x<390000 else 2 if x<500000 else 3
fig,axes=plt.subplots(1,3,figsize=(24,13),facecolor='#101926')
fig.subplots_adjust(left=.035,right=.98,bottom=.07,top=.88,wspace=.12)
for n,ax in enumerate(axes,1):
 ax.set_facecolor('#101926')
 group=[r for r in rows if int(r['层序'])==n]
 trays=[ends for h,ends in paths.items() if types.get(h)=='TDbECabletry' and layer(ends[0][0])==n]
 ox=min(p[0] for ends in trays for p in ends);oy=min(p[1] for ends in trays for p in ends)
 for a,b in trays:ax.plot([(a[0]-ox)/1000,(b[0]-ox)/1000],[(a[1]-oy)/1000,(b[1]-oy)/1000],color='#43d8ea',lw=1.7,zorder=2)
 pts=[]
 for r in group:
  x=(float(r['CAD中心X_mm'])-ox)/1000;y=(float(r['CAD中心Y_mm'])-oy)/1000
  pts.append((x,y,r['编号']))
 # Separate lower manifold labels from remote branch labels. A short local leg
 # leads to a dedicated, evenly spaced label row below the full plan.
 low=sorted([p for p in pts if p[1]<12],key=lambda p:(p[0],p[1],p[2]))
 high=sorted([p for p in pts if p[1]>=12],key=lambda p:(p[1],p[0],p[2]))
 for j,(x,y,ident) in enumerate(low):
  tx=-5+48*j/max(1,len(low)-1)
  ty=-4-(j%3)*3.1
  ax.annotate(ident,xy=(x,y),xytext=(tx,ty),ha='center',va='top',fontsize=10,color='#ffd68d',rotation=55,
    bbox=dict(boxstyle='round,pad=.2',facecolor='#101926',edgecolor='none'),
    arrowprops=dict(arrowstyle='-',lw=.65,color='#a98c5c',connectionstyle='arc3,rad=0'),zorder=4)
 # Remote labels use two side columns; maintain vertical spacing within each.
 sides={0:[],1:[]}
 for p in high:sides[int(p[0]>20)].append(p)
 for side,items in sides.items():
  ys=[]
  for x,y,ident in items:ys.append(max(y,ys[-1]+3.2 if ys else y))
  for (x,y,ident),ty in zip(items,ys):
   tx=47 if side else -7
   ax.annotate(ident,(x,y),(tx,ty),ha='left' if side else 'right',va='center',fontsize=10,color='#ffd68d',
    bbox=dict(boxstyle='round,pad=.2',facecolor='#101926',edgecolor='none'),
    arrowprops=dict(arrowstyle='-',lw=.8,color='#b79a68'),zorder=4)
 for x,y,ident in pts:ax.scatter(x,y,s=26,color='#ffc75f',edgecolor='#101926',linewidth=.35,zorder=5)
 ax.set_xlim(-16,57);ax.set_ylim(-17,78);ax.set_aspect('equal');ax.grid(alpha=.12,color='white')
 ax.set_xticks([0,10,20,30,40]);ax.set_yticks([0,10,20,30,40,50,60,70]);ax.tick_params(colors='#bac9dc',labelsize=10)
 ax.set_xlabel('局部 X（m）',color='#bac9dc',fontsize=11);ax.set_ylabel('局部 Y（m）',color='#bac9dc',fontsize=11)
 ax.set_title(f'第 {n} 层 · {len(group)} 个连接件',color='white',fontsize=19,pad=18)
 for spine in ax.spines.values():spine.set_edgecolor('#45536a')
fig.suptitle('三层桥架 · 连接件整体定位图',color='white',fontsize=27,y=.97)
fig.text(.5,.92,'青色：桥架完整路径     黄色：待补连接件     编号沿用原清单',ha='center',color='#bac9dc',fontsize=14)
fig.savefig(root/'fitting_overview_clear.png',dpi=180,facecolor=fig.get_facecolor())
fig.savefig(root/'fitting_overview_clear.svg',facecolor=fig.get_facecolor())
print('Generated overview')
