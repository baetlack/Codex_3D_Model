"""Analytic fixtures distinguish overlap candidates, surface hits and containment."""
import numpy as np
from check_assembly import sat,inside,tri,object_mesh,surface,column_penetration
from build_assembly import box

def test():
 a=np.array([[0,0,0],[3,0,0],[0,3,0]],float)
 assert sat(a,np.array([[1,1,-1],[1,1,1],[2,1,0]],float))
 # Bounding boxes overlap but these coplanar triangles are disjoint.
 assert not sat(a,np.array([[3,3,0],[3,1,0],[1,3,0]],float))
 assert not sat(a,a+[0,0,1])
 assert sat(a,a+[.25,.25,0])
 t=tri([box('test',0,0,0,10,10,10)])
 assert inside(np.array([5,5,5]),t)
 assert not inside(np.array([15,5,5]),t)
 outer=object_mesh('outer','test',t);inner=object_mesh('inner','test',tri([box('inner',2,2,2,2,2,2)]))
 assert surface(outer,inner) is None
 assert inside(inner['t'][0,0],t)
 touching=object_mesh('touch','bridge',np.array([[[0,20,2],[20,0,2],[10,10,8]]],float))
 assert surface(touching,outer) is not None
 assert column_penetration(touching,outer) is None  # corner contact despite 10x10x6 AABB overlap
 entering=object_mesh('entry','bridge',touching['t']-np.array([.5,.5,0]))
 assert column_penetration(entering,outer) is not None
 face=object_mesh('face','bridge',np.array([[[10,2,2],[10,8,2],[10,5,8]]],float))
 assert column_penetration(face,outer) is None
 assert column_penetration(inner,outer) is not None
 print('柱面/棱角接触不误报、真实穿入、闭体包含校验通过')
 print('三角形穿越、包围盒假阳性、共面、分离和闭体包含校验通过')
if __name__=='__main__':test()
