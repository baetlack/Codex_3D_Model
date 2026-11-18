"""Plan projections of actual model triangles, not illustrative collision boxes."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle
from matplotlib.font_manager import FontProperties
from audit_bridge_columns import load,polygons,OUT
font_file=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
FONT=FontProperties(fname=str(font_file)) if font_file.exists() else FontProperties(family=['Microsoft YaHei','SimHei','DejaVu Sans'])
plt.rcParams['axes.unicode_minus']=False

def run():
 report=json.loads((OUT/'data/桥架立柱穿入深度统计.json').read_text());rows={(r['bridge'],r['column']):r for r in report['penetrations']}
 bridges,columns=load();bridges={p['id']:p for p in bridges};columns={p['id']:p for p in columns}
 cases=[('L2-S-37C69','COL-040'),('L2-S-37BFF','COL-019'),('L3-S-37C70','COL-031'),('L3-C16','COL-063')]
 fig,axes=plt.subplots(2,2,figsize=(14,12));fig.patch.set_facecolor('white')
 for ax,key in zip(axes.flat,cases):
  r=rows.get(key)
  if r is None:
   ax.text(.5,.5,'当前未检出该配对穿入',transform=ax.transAxes,ha='center',fontproperties=FONT);ax.set_title(' / '.join(key));ax.axis('off');continue
  b,c=bridges[key[0]],columns[key[1]];lo,hi=c['low'][:2],c['high'][:2];polys=polygons(b,c)
  # Relative plan coordinates in mm keep labels readable while preserving scale.
  center=(lo+hi)/2;low=lo-center;high=hi-center
  ax.add_patch(Rectangle(low,*(high-low),facecolor='#dce4e8',edgecolor='#5c7380',lw=1.5,zorder=1))
  ax.add_collection(PolyCollection([t[:,:2]-center for t in b['t']],facecolors='#4794b5',edgecolors='#2d7499',linewidths=.35,alpha=.4,zorder=2))
  ax.add_collection(PolyCollection([np.array(p)[:,:2]-center for p in polys],facecolors='#dc654a',edgecolors='#c3442d',linewidths=.5,alpha=.72,zorder=3))
  witness=np.array(r['depth_witness_mm'])[:2]-center
  margins=np.r_[witness-low,high-witness];i=int(np.argmin(margins));face=witness.copy();face[i%2]=(low if i<2 else high)[i%2]
  ax.scatter(*witness,marker='*',s=120,color='#972f23',edgecolor='white',lw=.7,zorder=5)
  ax.annotate('',xy=witness,xytext=face,arrowprops={'arrowstyle':'<->','color':'#a42e1e','lw':1.6},zorder=6)
  ax.set_xlim(-800,800);ax.set_ylim(-800,800)
  ax.set_aspect('equal');ax.grid(alpha=.2);ax.set_xlabel('东向 X，相对柱轴 / mm',fontproperties=FONT);ax.set_ylabel('北向 Y，相对柱轴 / mm',fontproperties=FONT)
  ax.set_title(f"{key[0]} / {key[1]}\n最大实际内侵 {r['max_depth_mm']:.3f} mm；单轴退出 {r['direction']} {r['separation_mm']:.3f} mm",fontproperties=FONT,fontsize=11,pad=12)
 fig.suptitle('桥架与立柱：四种实际重叠情况',fontproperties=FONT,fontsize=18,y=.99)
 fig.text(.5,.025,'灰色：柱截面   蓝色：实际桥架面投影   红色：实际相交面投影   ★：最大内侵点\n各子图按相同比例绘制；退出距离为单对构件的几何下限，不是整装修补位移。',ha='center',fontproperties=FONT,fontsize=11)
 fig.tight_layout(rect=[.02,.075,.98,.965]);fig.savefig(OUT/'previews/桥架立柱重叠典型案例.png',dpi=170);plt.close(fig)
 print('实际三角面俯视图已生成')
if __name__=='__main__':run()
