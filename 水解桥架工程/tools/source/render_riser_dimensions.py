from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent/'三层桥架模型'
data=json.loads((root/'assembly.json').read_text(encoding='utf-8'));part=next(p for p in data['parts'] if p['id']=='L3-X01');p=part['parameters'];q=np.array(p['path_centerline_mm']);horizontal=q[-1,:2]-q[0,:2];direction=horizontal/np.linalg.norm(horizontal)
v=[];faces=[]
for line in (root/'models'/'L3-X01_45度乙字弯.obj').read_text().splitlines():
 if line.startswith('v '):v.append([float(n)*1000 for n in line.split()[1:]])
 elif line.startswith('f '):faces.append([int(n)-1 for n in line.split()[1:]])
v=np.array(v);x=(v[:,:2]-q[0,:2])@direction;z=v[:,2]-q[0,2]
plt.rcParams['font.sans-serif']=['Microsoft YaHei','DejaVu Sans'];plt.rcParams['axes.unicode_minus']=False
from matplotlib.collections import PolyCollection
fig,ax=plt.subplots(figsize=(10,10));ax.add_collection(PolyCollection(np.stack([x,z],axis=1)[np.array(faces)],facecolor='#d3e6ed',edgecolor='none'))
px=(q[:,:2]-q[0,:2])@direction;pz=q[:,2]-q[0,2];ax.plot(px,pz,'o-',color='#138ba4',lw=2,label='路径中心线')
run=p['horizontal_offset_mm'];total=p['total_rise_mm'];stub=p['straight_end_mm']
def dimension(a,b,text,offset=(0,0)):
 ax.annotate('',xy=b,xytext=a,arrowprops=dict(arrowstyle='<->',color='#535b65',lw=1))
 mid=(np.array(a)+b)/2+offset;ax.text(*mid,text,ha='center',va='center',fontsize=11,bbox=dict(facecolor='white',edgecolor='none',pad=2))
dimension((0,-210),(run,-210),f'水平偏移 {run:.2f} mm')
dimension((run+390,0),(run+390,total),f'总高差\n{total:.2f} mm',offset=(55,0))
dimension((-350,0),(-350,stub),'150 mm',offset=(-50,0))
dimension((run+210,total-stub),(run+210,total),'150 mm',offset=(50,0))
ax.text(run/2-100,total/2+130,'中段 45°\n斜段升高 = 水平偏移',fontsize=12,color='#246171',ha='center')
ax.text(0,-70,'A · 接37C11',ha='center',fontsize=11);ax.text(run,total+70,'B · 接37C12',ha='center',fontsize=11)
ax.set_xlim(-550,run+700);ax.set_ylim(-350,total+220);ax.set_aspect('equal');ax.grid(alpha=.13);ax.set_xlabel('沿水平偏移方向（mm）');ax.set_ylabel('相对A口升高（mm）')
ax.set_title('L3-X01 · 500×200 mm 立管乙字弯\nA口 EL115.42897 → B口 EL116.70000',fontsize=16,pad=18);ax.legend(loc='upper left');fig.tight_layout();fig.savefig(root/'previews'/'立管乙字弯尺寸.png',dpi=150);plt.close(fig)
print('Riser dimension drawing generated')
