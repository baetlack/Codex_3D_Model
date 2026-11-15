import json,re,csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

root=Path(__file__).parent
objects=json.loads((root/'tray_objects.json').read_text(encoding='utf-8-sig'))
paths={}
for line in (root/'tray_paths.txt').read_text(errors='replace').splitlines():
 m=re.match(r'\("([^"]+)" \(([^)]+)\) \(([^)]+)\)\)',line)
 if m: paths[m[1]]=[[float(v) for v in m[i].split()] for i in (2,3)]
rows=[]
for o in objects:
 if o['handle'] in paths:
  o['path']=paths[o['handle']]; rows.append(o)
with (root/'tray_coordinates.csv').open('w',newline='',encoding='utf-8-sig') as f:
 w=csv.writer(f);w.writerow(['Handle','ObjectType','Layer','X1_mm','Y1_mm','Z1_mm','X2_mm','Y2_mm','Z2_mm','Width_mm','Height_mm','StartEl_mm','EndEl_mm'])
 for o in rows:
  p=o['properties'];w.writerow([o['handle'],o['type'],o['layer'],*o['path'][0],*o['path'][1],p.get('Width'),p.get('Height'),p.get('StartEl'),p.get('EndEl')])
trays=[o for o in rows if o['type']=='TDbECabletry']
print('Paths',len(rows),'trays',len(trays))
for o in trays: print(o['handle'],o['path'])
fig=plt.figure(figsize=(18,11),facecolor='#101926')
levels=[100,104,106,112,116,123]
groups=[[] for _ in levels]
for o in trays:
 x=o['path'][0][0]; idx=max(0,min(5,int((x-265000)//67280)));groups[idx].append(o)
for i,group in enumerate(groups):
 ax=fig.add_subplot(2,3,i+1,projection='3d',facecolor='#101926')
 ax.set_title(f'EL{levels[i]:.3f} plan region | {len(group)} tray objects',color='white',fontsize=11)
 if group:
  ox=min(p[0] for o in group for p in o['path']);oy=min(p[1] for o in group for p in o['path'])
  for o in group:
   a,b=o['path']; p=o['properties']; a=[(a[0]-ox)/1000,(a[1]-oy)/1000,a[2]/1000];b=[(b[0]-ox)/1000,(b[1]-oy)/1000,b[2]/1000]
   dx,dy=b[0]-a[0],b[1]-a[1];length=(dx*dx+dy*dy)**.5;ww=(p.get('Width') or 200)/2000;hh=(p.get('Height') or 200)/1000
   nx,ny=(-dy/length*ww,dx/length*ww) if length>1e-8 else (ww,0)
   verts=[[q[0]+s*nx,q[1]+s*ny,q[2]+z] for q in (a,b) for z in (0,hh) for s in (-1,1)]
   faces=[[verts[j] for j in inds] for inds in [(0,1,3,2),(4,5,7,6),(0,1,5,4),(2,3,7,6),(0,2,6,4),(1,3,7,5)]]
   color='#ffbd59' if abs(a[2]-b[2])>.01 else '#35d6ec'
   ax.add_collection3d(Poly3DCollection(faces,facecolors=color,edgecolors=color,linewidths=.4,alpha=.85))
   ax.plot(*zip(a,b),color=color,lw=1)
  ax.set_xlim(-2,48);ax.set_ylim(-2,74);ax.set_zlim(0,9);ax.set_box_aspect((44,72,16))
 ax.set_xlabel('local X (m)',color='#afc1d6');ax.set_ylabel('local Y (m)',color='#afc1d6');ax.set_zlabel('object Z (m)',color='#afc1d6');ax.tick_params(colors='#afc1d6',labelsize=7)
 ax.view_init(elev=28,azim=-55)
 for axis in (ax.xaxis,ax.yaxis,ax.zaxis): axis.pane.fill=False
fig.suptitle('Hydrolysis cable trays — DWG coordinate preview',color='white',fontsize=19)
fig.text(.5,.035,'Cyan: constant Z   Orange: changing Z | Straight tray objects only; fittings pending | Local origins per plan; Z from CAD, no floor offset added',ha='center',color='#afc1d6',fontsize=10)
fig.savefig(root/'tray_preview.png',dpi=150,facecolor=fig.get_facecolor())
print('Wrote preview and coordinates')
