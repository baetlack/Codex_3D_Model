"""Independent analytic fixtures for depth versus displacement and nonlocal geometry."""
import numpy as np
import check_assembly as ck
from audit_bridge_columns import polygons,max_depth,translations,bucket

def box(low,high):
 vertices=[[x,y,z] for x in [low[0],high[0]] for y in [low[1],high[1]] for z in [low[2],high[2]]]
 faces=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]
 return ck.object_mesh('fixture-column','structure',ck.tri([{'vertices':vertices,'faces':faces}]))
def plane(x0,x1,y0,y1,z=1000):return np.array([[[x0,y0,z],[x1,y0,z],[x1,y1,z]],[[x0,y0,z],[x1,y1,z],[x0,y1,z]]],float)
def run():
 c=box([0,0,0],[750,750,10000]);b=ck.object_mesh('strip','bridge',plane(-100,850,700,900));p=polygons(b,c)
 depth,_=max_depth(p,c['low'],c['high']);assert abs(depth-50)<1e-5
 assert abs(translations(b,c)['Y+']-50)<1e-5
 # A triangular corner wedge: the deepest point is not its centroid; and moving
 # 100mm does not clear the whole wedge, although max nearest-face depth is 100mm.
 c=box([0,0,0],[1000,1000,10000]);b=ck.object_mesh('wedge','bridge',np.array([[[0,0,1000],[200,0,1000],[0,200,1000]]],float))
 depth,_=max_depth(polygons(b,c),c['low'],c['high']);assert abs(depth-100)<1e-5
 assert ck.column_penetration(b,c)['interior_sample_depth_mm']<depth-1
 assert abs(translations(b,c)['X-']-200)<1e-5
 assert abs(translations(b,c)['Y-']-200)<1e-5
 # A distant disconnected surface does not require clearing the combined AABB.
 c=box([0,0,0],[100,100,10000]);b=ck.object_mesh('disconnected','bridge',np.vstack([plane(-10,10,10,90),plane(-300,-200,10,90)]))
 assert abs(translations(b,c)['X+']-110)<1e-5
 # But a second surface entering the column before the first has exited must be
 # included. Clipped extents alone would incorrectly return 110 instead of 250.
 b=ck.object_mesh('entering-second-surface','bridge',np.vstack([plane(-10,10,10,90),plane(-150,-50,10,90)]))
 assert abs(translations(b,c)['X+']-250)<1e-5
 contact=ck.object_mesh('contact','bridge',plane(-100,0,10,90));assert ck.column_penetration(contact,c) is None
 assert [bucket(x) for x in [10,30,60,100,101]]==['0.1–10 mm','>10–30 mm','>30–60 mm','>60–100 mm','>100 mm']
 print('平行侧面深度、斜角最大值/采样点差异、深度与退出距离区别、整件几何区间合并、接触与分档边界通过')
if __name__=='__main__':run()
