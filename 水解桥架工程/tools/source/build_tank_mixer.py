"""Create the user-requested tank and simplified top-entry agitator, mm, Z-up."""
from pathlib import Path
from functools import lru_cache
import json, math, struct

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'models' / '设备'
MIXER_SOURCE = OUT / '槽罐搅拌器_标注侧视' / 'model_data.js'
MIXER_HEIGHTS = {'C41B02': 2185, 'C41B03': 1350, 'D41B01': 1430, 'D41B02': 3076,
                 'F41B01': 2310, 'F41B02': 1880, 'F41B05': 1880, 'F41B06': 1880}
parts=[]

def add(name, color, verts, faces): parts.append((name,color,verts,faces))
def cyl(name, z0, z1, r, color, n=64, r2=None):
    r2=r if r2 is None else r2
    v=[]
    for z,rr in ((z0,r),(z1,r2)):
        v += [(rr*math.cos(2*math.pi*i/n),rr*math.sin(2*math.pi*i/n),z) for i in range(n)]
    f=[]
    for i in range(n): j=(i+1)%n; f.append((i,j,n+j,n+i))
    f += [tuple(reversed(range(n))),tuple(range(n,2*n))]
    add(name,color,v,f)
def box(name,center,size,color):
    x,y,z=center; a,b,c=(s/2 for s in size)
    v=[(x+sx*a,y+sy*b,z+sz*c) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    add(name,color,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)])
def ring(name,z0,z1,ro,ri,color,n=64):
    v=[]
    for z,r in ((z0,ro),(z1,ro),(z0,ri),(z1,ri)):
        v += [(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for i in range(n)]
    f=[]
    for i in range(n):
        j=(i+1)%n
        f += [(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),(n+i,n+j,3*n+j,3*n+i),(j,i,2*n+i,2*n+j)]
    add(name,color,v,f)
def hollow_frustum(name,z0,z1,r0,r1,thickness,color,n=96):
    v=[]
    for z,r in ((z0,r0),(z1,r1),(z0,r0-thickness),(z1,r1-thickness)):
        v.extend([(r*math.cos(2*math.pi*i/n),r*math.sin(2*math.pi*i/n),z) for i in range(n)])
    f=[]
    for i in range(n):
        j=(i+1)%n
        f.extend([(i,j,n+j,n+i),(2*n+j,2*n+i,3*n+i,3*n+j),(n+i,n+j,3*n+j,3*n+i),(j,i,2*n+i,2*n+j)])
    add(name,color,v,f)
def brace(name,x0,z0,x1,z1,width,depth,color):
    # Rectangular beam in the front X/Z plane, extruded across Y.
    dx,dz=x1-x0,z1-z0; length=math.hypot(dx,dz); nx,nz=-dz/length*width/2,dx/length*width/2
    v=[]
    for y in (-depth/2,depth/2):
        v.extend([(x0+nx,y,z0+nz),(x0-nx,y,z0-nz),(x1-nx,y,z1-nz),(x1+nx,y,z1+nz)])
    add(name,color,v,[(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])

def build_preheater():
    parts.clear()
    # Tank: nominal OD 5500, straight shell height 5000, bottom at Z=0.
    cyl('Tank_shell_OD5500_H5000',0,5000,2750,'#9aa8ad',96,2750)
    cyl('Tank_flat_bottom',0,24,2750,'#7e8c91',96)
    ring('Lid_edge_rim',4970,5030,2790,2670,'#c5d0d3',96)
    cyl('Tank_cover_lid',5000,5055,2750,'#9eaaad',96)
    ring('Lid_mixer_mount_flange',5035,5080,540,370,'#68777c',64)
    # simple feet and foundation pads
    for i in range(12):
        a=2*math.pi*i/12; x,y=2685*math.cos(a),2685*math.sin(a)
        box(f'Leg_{i+1:02}',(x,y,-65),(180,180,130),'#68777c')
        box(f'Pad_{i+1:02}',(x,y,-155),(280,280,50),'#929b9e')
    # Hollow, rotationally symmetric conical support shell; no internal ladder or crossbars.
    hollow_frustum('Hollow_conical_mixer_support',5080,6380,410,245,12,'#68777c',96)
    # Rotationally symmetric solid drive stack, following the provided side silhouette.
    cyl('Drive_lower_mount',6380,6435,390,'#52636a',96,390)
    cyl('Drive_neck',6435,6515,250,'#78898f',96,220)
    cyl('Drive_base_flange',6515,6580,500,'#52636a',96,500)
    cyl('Drive_spacer',6580,6650,300,'#78898f',96,300)
    cyl('Motor_lower_bell',6650,6735,310,'#52636a',96,285)
    cyl('Motor_body',6735,7100,285,'#6f8086',96,285)
    # Longitudinal radial cooling ribs; their repeated circular layout preserves the same silhouette at every azimuth.
    for i in range(24):
        a=2*math.pi*i/24
        cyl('Motor_cooling_fin',6765,7065,13,'#a8b5b8',12,13)
        # move fin mesh from the axis to its equally spaced position around the motor casing
        name,color,verts,faces=parts[-1]
        parts[-1]=(name,color,[(x+282*math.cos(a),y+282*math.sin(a),z) for x,y,z in verts],faces)
    cyl('Motor_top_cap',7100,7155,285,'#52636a',96,270)
    cyl('Motor_rounded_crown',7155,7185,270,'#6f8086',96,220)
    # shaft inside tank, plus two simplified pitched-blade impeller levels
    cyl('Agitator_shaft',100,6380,42,'#c0c9cc',32)
    # Two small, simplified impellers on the submerged shaft; retained as separate parts.
    for z,rad in ((1450,1050),(3150,820)):
        for i in range(4):
            a=math.pi*i/2
            box(f'Impeller_{z}_{i+1}',(rad*.36*math.cos(a),rad*.36*math.sin(a),z),(rad*.72,70,58),'#89989d')
        cyl('Impeller_hub',z-55,z+55,85,'#65757b',32)

def corner_normals(vertices, faces):
    """Smooth shallow joins while keeping caps and machined edges sharp."""
    def unit(v):
        length = math.hypot(*v)
        return tuple(x/length for x in v) if length else (0, 0, 1)

    neighbors = [[] for _ in vertices]
    face_normals = []
    for face in faces:
        a, b, c = (vertices[i] for i in face[:3])
        u, v = [y-x for x, y in zip(a, b)], [y-x for x, y in zip(a, c)]
        normal = unit((u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]))
        face_normals.append(normal)
        for index in face:
            neighbors[index].append(normal)
    result = []
    for face, normal in zip(faces, face_normals):
        corners = []
        for index in face:
            similar = [n for n in neighbors[index] if sum(x*y for x, y in zip(n, normal)) >= .80]
            corners.append(unit(tuple(sum(n[k] for n in similar) for k in range(3))))
        result.append(corners)
    return result


def export_model(out, stem, color_materials=False, smooth=False):
    out.mkdir(parents=True, exist_ok=True)
    colors = sorted({part[1] for part in parts})
    color_indices = {color: i for i, color in enumerate(colors)}
    def rgb(color):
        return [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
    normals = [corner_normals(verts, faces) for _, _, verts, faces in parts] if smooth else [None]*len(parts)
    # OBJ (meters, Z-up) with named object groups and colors.
    obj=['# Tank and mixer generated from side elevation; source dimensions in mm; OBJ in meters, Z-up.',f'mtllib {stem}.mtl']
    normal_base = 1
    for (name,color,verts,faces), corners in zip(parts, normals):
        obj += [f'o {name}',f'usemtl {color[1:]}']
        obj += [f'v {x/1000:.6f} {y/1000:.6f} {z/1000:.6f}' for x,y,z in verts]
        base=sum(1 for line in obj if line.startswith('v '))-len(verts)+1
        if corners is None:
            obj += ['f '+' '.join(str(base+i) for i in face) for face in faces]
        else:
            obj += [f'vn {x:.6f} {y:.6f} {z:.6f}' for face in corners for x, y, z in face]
            for face in faces:
                obj.append('f '+' '.join(f'{base+index}//{normal_base+i}' for i, index in enumerate(face)))
                normal_base += len(face)
    (out/f'{stem}.obj').write_text('\n'.join(obj)+'\n',encoding='utf-8')
    (out/f'{stem}.mtl').write_text('\n'.join(
        f'newmtl {c[1:]}\nKd ' + (' '.join(f'{v:.4f}' for v in rgb(c)) if color_materials else '0.55 0.62 0.65')
        for c in colors)+'\n', encoding='utf-8')

    # Minimal valid glTF 2.0 binary; each physical part remains a separately named node.
    blob=bytearray(); views=[]; access=[]; meshes=[]; nodes=[]
    def align4(): blob.extend(b'\0'*((-len(blob))%4))
    for (name,color,verts,faces), corners in zip(parts, normals):
        if corners is not None:
            flat_vertices, flat_faces = [], []
            for face in faces:
                start = len(flat_vertices)
                flat_vertices.extend(verts[i] for i in face)
                flat_faces.append(tuple(range(start, start+len(face))))
            verts, faces = flat_vertices, flat_faces
        pos=[q for v in verts for q in (v[0]/1000,v[2]/1000,-v[1]/1000)] # GLB meters, Y-up; east +X, north -Z
        idx=[q for face in faces for k in range(1,len(face)-1) for q in (face[0],face[k],face[k+1])]
        align4(); off=len(blob); raw=struct.pack('<%sf'%len(pos),*pos); blob.extend(raw); views.append({'buffer':0,'byteOffset':off,'byteLength':len(raw),'target':34962}); vi=len(views)-1
        mins=[min(pos[i::3]) for i in range(3)]; maxs=[max(pos[i::3]) for i in range(3)]
        access.append({'bufferView':vi,'componentType':5126,'count':len(verts),'type':'VEC3','min':mins,'max':maxs}); ai=len(access)-1
        align4(); off=len(blob); raw=struct.pack('<%sH'%len(idx),*idx); blob.extend(raw); views.append({'buffer':0,'byteOffset':off,'byteLength':len(raw),'target':34963}); ii=len(views)-1
        access.append({'bufferView':ii,'componentType':5123,'count':len(idx),'type':'SCALAR'}); bi=len(access)-1
        primitive = {'attributes': {'POSITION': ai}, 'indices': bi, 'mode': 4}
        if corners is not None:
            directions = [q for face in corners for x, y, z in face for q in (x, z, -y)]
            align4()
            off = len(blob)
            raw = struct.pack(f'<{len(directions)}f', *directions)
            blob.extend(raw)
            views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(raw), 'target': 34962})
            access.append({'bufferView': len(views)-1, 'componentType': 5126, 'count': len(verts), 'type': 'VEC3'})
            primitive['attributes']['NORMAL'] = len(access)-1
        if color_materials:
            primitive['material'] = color_indices[color]
        meshes.append({'name':name,'primitives':[primitive]}); nodes.append({'name':name,'mesh':len(meshes)-1})
    doc={'asset':{'version':'2.0','generator':'build_tank_mixer.py'},'scene':0,'scenes':[{'nodes':list(range(len(nodes)))}],'nodes':nodes,'meshes':meshes,'accessors':access,'bufferViews':views,'buffers':[{'byteLength':len(blob)}]}
    if color_materials:
        doc['materials'] = [{'pbrMetallicRoughness': {'baseColorFactor': [*rgb(c), 1], 'metallicFactor': 0, 'roughnessFactor': .64},
                             'doubleSided': True} for c in colors]
    json_chunk=json.dumps(doc,separators=(',',':')).encode(); json_chunk+=b' '*((-len(json_chunk))%4); align4(); bin_chunk=bytes(blob)
    total=12+8+len(json_chunk)+8+len(bin_chunk)
    glb=struct.pack('<4sII',b'glTF',2,total)+struct.pack('<I4s',len(json_chunk),b'JSON')+json_chunk+struct.pack('<I4s',len(bin_chunk),b'BIN\0')+bin_chunk
    (out/f'{stem}.glb').write_bytes(glb)
    view_parts = []
    for (name, color, verts, faces), corners in zip(parts, normals):
        item = {'name': name, 'color': color, 'vertices': verts, 'faces': faces}
        if corners is not None:
            item['normals'] = [[[round(v, 6) for v in n] for n in face] for face in corners]
        view_parts.append(item)
    (out/'model_data.js').write_text(
        'window.MODEL_PARTS='+json.dumps(view_parts, separators=(',',':'))+';\n', encoding='utf-8')


@lru_cache(maxsize=1)
def mixer_reference():
    prefix = 'window.MODEL_PARTS='
    mesh = MIXER_SOURCE.read_text(encoding='utf-8-sig').strip()
    if not mesh.startswith(prefix) or not mesh.endswith(';'):
        raise ValueError(f'Unexpected agitator mesh wrapper: {MIXER_SOURCE}')
    return tuple(part for part in json.loads(mesh[len(prefix):-1])
                 if part['name'].startswith(('01_', '02_', '03_', '06_')))


def mixer_at(mount_z, motor_top):
    """Place the confirmed top assembly, including its symmetric intermediate shaft."""
    reference_parts = mixer_reference()
    source_top = max(z for part in reference_parts if part['name'].startswith('01_')
                     for _, _, z in part['vertices'])
    scale = (motor_top - mount_z) / source_top
    if scale <= 0:
        raise ValueError('The motor top must be above the mixer mounting plane')
    return [(part['name'], part['color'],
             [(scale*x, scale*y, mount_z+scale*z) for x, y, z in part['vertices']],
             part['faces']) for part in reference_parts]


def polish_preheater_archive():
    mount_z = max(z for name, _, verts, _ in parts if name == 'Tank_cover_lid' for _, _, z in verts)
    assembly = mixer_at(mount_z, 7185)
    intermediate = next(verts for name, _, verts, _ in assembly if name == '03_Intermediate_shaft')
    lower_joint_z = min(z for _, _, z in intermediate)
    impeller_top = max(z for name, _, verts, _ in parts if name.startswith('Impeller_')
                       for _, _, z in verts)
    parts[:] = [part for part in parts if not part[0].startswith(('Drive_', 'Motor_', 'Hollow_'))
                and part[0] != 'Lid_mixer_mount_flange']

    # Keep the original lower shaft diameter and impeller placement. Shorten only
    # the portion of straight shaft that the installed intermediate shaft replaces.
    for index, (name, color, verts, faces) in enumerate(parts):
        if name == 'Agitator_shaft':
            if not impeller_top < lower_joint_z < max(z for _, _, z in verts):
                raise ValueError('Intermediate shaft joint is outside the original upper shaft span')
            parts[index] = (name, color, [(x, y, min(z, lower_joint_z)) for x, y, z in verts], faces)
            break

    parts.extend(assembly)

    palette = (
        (('Tank_shell', 'Tank_flat'), '#a5b9c3'),
        (('Tank_cover',), '#b7c8d0'),
        (('Lid_edge',), '#c9d9df'),
        (('Leg_',), '#667c89'),
        (('Pad_',), '#848989'),
    )
    for index, (name, color, verts, faces) in enumerate(parts):
        finish = next((finish for prefixes, finish in palette if name.startswith(prefixes)), color)
        parts[index] = (name, finish, verts, faces)
    stem = 'C41B02_钛液预热槽'
    archive = ROOT.parent / '水解设备模型库' / '设备档案' / stem
    export_model(archive, stem, color_materials=True, smooth=True)

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--polish-archive', action='store_true', help='Rebuild the presentation finish of C41B02')
    args = parser.parse_args()
    build_preheater()
    if args.polish_archive:
        polish_preheater_archive()
    else:
        export_model(OUT, 'C4_BH2C_tank_mixer')
    print(f'Wrote {len(parts)} named parts; tank OD 5500 x H5000, mixer above tank 2185; overall height 7185 mm.')
