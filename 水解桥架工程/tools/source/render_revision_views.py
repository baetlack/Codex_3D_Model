from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection,LineCollection
root=Path(__file__).parent/'连接件模型库'
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans'];plt.rcParams['axes.unicode_minus']=False
catalog={m['id']:m for m in json.loads((root/'catalog.json').read_text(encoding='utf-8'))['models']}
ids=['L1-C07','L2-C18','L3-C02','L3-C04','L3-C10']
fig,axes=plt.subplots(len(ids),3,figsize=(16,17));fig.subplots_adjust(hspace=.5,wspace=.28,top=.93)
for row,ident in enumerate(ids):
 m=catalog[ident];v=[];f=[]
 for line in (root/m['files']['obj']).read_text().splitlines():
  if line.startswith('v '):v.append([float(x)*1000 for x in line.split()[1:]])
  if line.startswith('f '):f.append([int(x)-1 for x in line.split()[1:]])
 v=np.array(v);f=np.array(f);edges={}
 for face in f:
  pts=v[face];n=np.cross(pts[1]-pts[0],pts[2]-pts[0]);n/=np.linalg.norm(n)
  for i in range(3):
   a,b=pts[i],pts[(i+1)%3];key=tuple(sorted([tuple(np.round(a,3)),tuple(np.round(b,3))]))
   edges.setdefault(key,[]).append(n)
 # Suppress the mesh triangulation diagonals within flat plates.
 creases=[]
 for key,normals in edges.items():
  if len(normals)==1 or any(abs(np.dot(normals[0],n))<.999 for n in normals[1:]):creases.append(np.array(key))
 for col,(plane,title) in enumerate([((0,1),'俯视 XY'),((0,2),'侧视 XZ'),((1,2),'正视 YZ')]):
  ax=axes[row,col];ax.add_collection(PolyCollection(v[f][:,:,plane],facecolor='#dcebf0',edgecolor='none'))
  ax.add_collection(LineCollection([e[:,plane] for e in creases],colors='#34596a',linewidths=.6))
  projected=v[:,plane];lo=projected.min(0);hi=projected.max(0);pad=max(hi-lo)*.12
  ax.set_xlim(lo[0]-pad,hi[0]+pad);ax.set_ylim(lo[1]-pad,hi[1]+pad);ax.set_aspect('equal');ax.grid(alpha=.15)
  ax.set_title(f'{ident} · {title}',fontsize=12);ax.tick_params(labelsize=8);ax.set_xlabel('mm',fontsize=8)
  ax.text(.02,.98,f'包络 {hi[0]-lo[0]:g} × {hi[1]-lo[1]:g} mm',transform=ax.transAxes,va='top',fontsize=8,bbox=dict(facecolor='white',alpha=.85,edgecolor='none'))
fig.suptitle('v1.2 修订连接件 · 三视图核对',fontsize=22)
fig.savefig(root/'previews'/'修订模型三视图.png',dpi=150,bbox_inches='tight');plt.close(fig)
print('Rendered revision orthographic views')
