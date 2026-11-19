"""Auditable plan/section comparison artifacts; current mesh versus source and revision 01."""
from pathlib import Path
import sys,json,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
R=Path(__file__).resolve().parents[2];OUT=R/'水解设备模型库/版本/2.0/C41B02'
sys.path.insert(0,str(R/'水解总装工程/tools'));from check_assembly import script

def render():
 trace=json.loads((OUT/'顶侧结构图面量测.json').read_text());old=json.loads((OUT/'历史/2.0-C41B02-01/设备/参数.json').read_text());current=json.loads((OUT/'设备/参数.json').read_text());oldp={p['id']:p for p in old['ports']};newp={p['id']:p for p in current['ports']}
 fig,axes=plt.subplots(1,2,figsize=(15,7),sharex=True,sharey=True);errors=[]
 for ax,parts,color,title in [(axes[0],oldp,'#cb594a','Revision 01 - before'),(axes[1],newp,'#1688a6','Revision 02 - corrected')]:
  ax.add_patch(Circle((0,0),2862,fill=False,color='#999',lw=.9));ax.add_patch(Circle((0,0),2100,fill=False,color='#ddd',ls='--'))
  for ident,q in trace['circles'].items():
   if ident not in parts:continue
   p=parts[ident];xy=p['center_mm'][:2];ref=q['center_xy_mm'];ax.plot(*ref,'+',color='#444',ms=7)
   r=(1075 if ident.startswith('k') else {'c':265,'d':320,'e':185,'f':200,'n':340,'a/p':375}.get(ident,150))/2
   ax.add_patch(Circle(ref,r,fill=False,color='#aaa',lw=1.4))
   modelr=(p.get('cover_OD_mm',1000) if ident.startswith('k') else p.get('flange_OD_mm',{'c':280,'d':330,'e':195,'f':210,'n':330}.get(ident,150)))/2
   ax.add_patch(Circle(xy,modelr,fill=False,color=color,lw=1.3,ls='--' if parts is oldp else '-'))
   ax.text(xy[0]+80,xy[1]+80,ident,color=color,fontsize=9)
  ref=trace['circles']['a/p']['center_xy_mm'];xy=parts['p']['center_mm'][:2];ax.plot(*ref,'+',color='#444');ax.add_patch(Circle(ref,187.5,fill=False,color='#aaa'));ax.add_patch(Circle(xy,133 if parts is oldp else 187.5,fill=False,color=color));ax.text(xy[0]+70,xy[1]+80,'a/p',color=color)
  for ident in ['a','c','d','e','f','n']:
   ref=trace['circles']['a/p' if ident=='a' else ident]['center_xy_mm'];xy=np.array(parts[ident]['center_mm'][:2]);err=float(np.linalg.norm(xy-ref))
   if parts is oldp:errors.append({'port':ident,'old_center_error_mm':round(err,3),'old_xy_mm':xy.tolist(),'source_xy_mm':ref,'new_xy_mm':newp[ident]['center_mm'][:2]})
  ax.set(xlim=(-3200,3200),ylim=(-3200,3200),aspect='equal',title=title,xlabel='Local X / mm');ax.grid(alpha=.15)
 axes[0].set_ylabel('Local Y / mm');fig.suptitle('C41B02 roof plan | grey: source outline | colored: model\nPage calibrated from dimensioned rim OD5724; not site installation accuracy',fontsize=12);fig.tight_layout();fig.savefig(OUT/'图面校核_俯视新旧.png',dpi=150);plt.close(fig)
 fig,axes=plt.subplots(1,3,figsize=(16,5))
 for ax,title,oldstate in [(axes[0],'b/j - old radial 300',True),(axes[1],'b/j - corrected tangent 250',False)]:
  rad=np.array([math.cos(math.pi/8),math.sin(math.pi/8)]);t=np.array([-rad[1],rad[0]]);center=rad*2100
  ax.add_patch(Circle((0,0),537.5,fill=False,color='#888'));ax.add_patch(Circle((0,0),230,fill=False,color='#888'))
  for name,sign in [('b',1),('j',-1)]:
   xy=(-sign*rad*150) if oldstate else sign*t*125
   ax.add_patch(Circle(xy,75,fill=False,color='#c95b49' if oldstate else '#1688a6',lw=2));ax.text(xy[0],xy[1],name,ha='center',va='center')
  ax.plot([-400*rad[0],400*rad[0]],[-400*rad[1],400*rad[1]],'--',color='#ccc');ax.set(xlim=(-600,600),ylim=(-600,600),aspect='equal',title=title);ax.grid(alpha=.15)
 ax=axes[2]
 ax.add_patch(Rectangle((0,0),200,377,fill=False,color='#1688a6',lw=2));ax.add_patch(Rectangle((184,-64),16,505,fill=False,color='#1688a6',lw=2));ax.add_patch(Rectangle((200,-51),3,479,fill=False,color='#777'));ax.add_patch(Rectangle((203,-64),10,505,fill=False,color='#1688a6',lw=2));ax.add_patch(Rectangle((213,52),200,273,fill=False,color='#1688a6',lw=2));ax.add_patch(Rectangle((397,-9),16,395,fill=False,color='#1688a6',lw=2));ax.axvline(0,color='#444');ax.set(xlim=(-45,450),ylim=(-100,460),aspect='equal',title='g section - sleeve / joint / straight short piece',xlabel='Projection from shell / mm');ax.text(100,-75,'200',ha='center');ax.text(206,-75,'13',ha='center');ax.text(313,-75,'200',ha='center');ax.grid(alpha=.15)
 fig.tight_layout();fig.savefig(OUT/'图面校核_双管与侧口.png',dpi=150);plt.close(fig)
 (OUT/'孔位偏差对比.json').write_text(json.dumps({'reference':'顶侧结构图面量测.json','units':'mm','maximum_old_model_offset_mm':max(p['old_center_error_mm'] for p in errors),'ports':errors,'limit':'该偏差仅比较模型与本张图面；不是设备安装或施工偏差。'},ensure_ascii=False,indent=2)+'\n')
 print('Rendered plan and local structure comparisons.')
if __name__=='__main__':render()
