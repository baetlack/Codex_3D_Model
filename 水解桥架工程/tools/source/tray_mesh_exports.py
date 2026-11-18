"""Approved 2 mm U-section mesh and OBJ/GLB exports, shared by the 2.0 rectifier.
Copied without geometric changes from the frozen 1.0 generator.
"""
import json, struct
import numpy as np
LAYERS = {}

def unit(v):return np.array(v,float)/np.linalg.norm(v)

class Mesh:
 def __init__(self):self.v=[];self.f=[]
 def tri(self,a,b,c):
  if np.linalg.norm(np.cross(np.array(b)-a,np.array(c)-a))<1e-8:return
  i=len(self.v);self.v.extend([a,b,c]);self.f.append([i,i+1,i+2])
 def quad(self,a,b,c,d):self.tri(a,b,c);self.tri(a,c,d)

def straight_mesh(a,b,w,h,up):
 d=unit(b-a);up=unit(up-d*np.dot(up,d));side=unit(np.cross(up,d));t=2
 section=[(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(w/2-t,h/2),(w/2-t,-h/2+t),(-w/2+t,-h/2+t),(-w/2+t,h/2),(-w/2,h/2)]
 rings=[[p+side*x+up*y for x,y in section] for p in (a,b)];m=Mesh()
 for j in range(8):m.quad(rings[0][j],rings[0][(j+1)%8],rings[1][(j+1)%8],rings[1][j])
 # U-shaped end rims (three rectangles), leaving cable space open.
 for ring in rings:
  for ids in [(0,1,4,5),(1,2,3,4),(0,5,6,7)]:m.quad(*[ring[j] for j in ids])
 return np.array(m.v),np.array(m.f)

def export_obj(selected,path):
 lines=['# units=m; Z-up; EL100 is local Z=0'];offset=1
 for p in selected:
  lines.append('o '+p['id']);lines+=['v '+' '.join(f'{x/1000:.7f}' for x in v) for v in p['v']]
  lines+=['f '+' '.join(str(int(i)+offset) for i in face) for face in p['f']];offset+=len(p['v'])
 path.write_text('\n'.join(lines)+'\n',encoding='ascii')

def export_glb(selected,path):
 chunks=[];views=[];accessors=[];meshes=[];nodes=[dict(name=f'L{i}_EL{LAYERS[i]["EL"]}',children=[]) for i in range(1,4)];offset=0
 for p in selected:
  v=p['v'].astype(np.float32)/1000;v=v[:,[0,2,1]];v[:,2]*=-1;faces=p['f'];normals=np.zeros_like(v)
  for f in faces:
   n=np.cross(v[f[1]]-v[f[0]],v[f[2]]-v[f[0]]);n/=np.linalg.norm(n);normals[f]=n
  start=len(accessors)
  for data,ctype,type_,count,target in [(v.astype('<f4').tobytes(),5126,'VEC3',len(v),34962),(normals.astype('<f4').tobytes(),5126,'VEC3',len(v),34962),(faces.astype('<u4').tobytes(),5125,'SCALAR',faces.size,34963)]:
   views.append(dict(buffer=0,byteOffset=offset,byteLength=len(data),target=target));a=dict(bufferView=len(views)-1,componentType=ctype,count=count,type=type_)
   if len(accessors)==start:a.update(min=v.min(0).tolist(),max=v.max(0).tolist())
   accessors.append(a);chunks.append(data);offset+=len(data)
  meshes.append(dict(name=p['id'],primitives=[dict(attributes=dict(POSITION=start,NORMAL=start+1),indices=start+2,material=p['layer']-1)]))
  nodes[p['layer']-1]['children'].append(len(nodes));nodes.append(dict(name=p['id'],mesh=len(meshes)-1,extras=dict(id=p['id'],category=p['category'],source_handle=p['handle'])))
 def color(hex_):return [int(hex_[i:i+2],16)/255 for i in (1,3,5)]+[1]
 g=dict(asset=dict(version='2.0',generator='HydrolysisTrayAssembly 2.0'),scene=0,scenes=[dict(nodes=[0,1,2])],nodes=nodes,meshes=meshes,materials=[dict(name=f'L{i}',doubleSided=True,pbrMetallicRoughness=dict(baseColorFactor=color(LAYERS[i]['color']),metallicFactor=.4,roughnessFactor=.45)) for i in range(1,4)],buffers=[dict(byteLength=offset)],bufferViews=views,accessors=accessors)
 g['asset']['extras']=dict(geographic_axes=dict(east='+X',north='-Z',up='+Y'),elevation_origin_EL=100,assembly_revision='2.0')
 j=json.dumps(g,separators=(',',':')).encode();j+=b' '*((-len(j))%4);b=b''.join(chunks);b+=b'\0'*((-len(b))%4)
 path.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b)
