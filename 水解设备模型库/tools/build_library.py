from __future__ import annotations

import json
import math
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / '水解桥架工程' / 'tools' / 'source'))
from build_tank_mixer import MIXER_HEIGHTS, mixer_at, mixer_reference

SOURCE = Path(__file__).resolve().parents[2] / "水解设备布置模型" / "设备数据.json"
SCREEN_SOURCE = Path(__file__).resolve().parents[2] / "设备"
MATERIALS = {
    "shell": "TankCyan",
    "tank_white": "TankWhite",
    "mixer_gray": "MixerLightGray",
    "foundation": "FoundationRed",
    "preheater_shell": "PreheaterWhite",
    "preheater_base": "BaseLightGray",
    "steel": "SupportWhite",
    "drive": "DriveWhite",
    "machine": "MachineGrey",
    "annotated_motor": "AnnotatedMotor",
    "annotated_drive": "AnnotatedDrive",
    "annotated_shaft": "AnnotatedShaft",
    "annotated_frame": "AnnotatedFrame",
}
MIXER_MATERIALS = {'01': 'annotated_motor', '02': 'annotated_drive',
                   '03': 'annotated_shaft', '06': 'annotated_frame'}
MTL = """newmtl TankCyan\nKa 0.03 0.38 0.43\nKd 0.05 0.78 0.84\nKs 0.16 0.16 0.16\nNs 24\n\nnewmtl FoundationRed\nKa 0.25 0.05 0.06\nKd 0.62 0.18 0.20\nKs 0.08 0.08 0.08\nNs 12\n\nnewmtl SupportWhite\nKa 0.42 0.44 0.45\nKd 0.86 0.88 0.89\nKs 0.20 0.20 0.20\nNs 32\n\nnewmtl DriveWhite\nKa 0.42 0.44 0.45\nKd 0.92 0.93 0.91\nKs 0.25 0.25 0.25\nNs 36\n\nnewmtl MachineGrey\nKa 0.18 0.20 0.21\nKd 0.45 0.52 0.55\nKs 0.16 0.16 0.16\nNs 20\n"""
MTL += """\nnewmtl PreheaterWhite\nKa 0.60 0.61 0.62\nKd 0.90 0.91 0.92\nKs 0.20 0.20 0.20\nNs 28\n\nnewmtl BaseLightGray\nKa 0.45 0.46 0.47\nKd 0.72 0.74 0.76\nKs 0.12 0.12 0.12\nNs 16\n"""
MTL += """\nnewmtl TankWhite\nKa 0.72 0.73 0.74\nKd 0.92 0.93 0.94\nKs 0.08 0.08 0.08\nNs 8\nd 1.0\n"""
MTL += """\nnewmtl MixerLightGray\nKa 0.52 0.54 0.56\nKd 0.78 0.80 0.82\nKs 0.14 0.14 0.14\nNs 18\nd 1.0\n"""
for group, color in {'01': '#387f7c', '02': '#597a98', '03': '#d6a45a', '06': '#6d8497'}.items():
    rgb = ' '.join(f'{int(color[i:i+2], 16)/255:.4f}' for i in (1, 3, 5))
    MTL += f'\nnewmtl {MATERIALS[MIXER_MATERIALS[group]]}\nKd {rgb}\n'


class Mesh:
    def __init__(self):
        self.tris = []
        self.mixer = None

    def tri(self, p, mat="shell"):
        self.tris.append((p, mat))

    def quad(self, p, mat="shell"):
        self.tri([p[0], p[1], p[2]], mat)
        self.tri([p[0], p[2], p[3]], mat)

    def box(self, cx, cy, z, sx, sy, sz, mat="steel", closed=True):
        x, y = sx / 2, sy / 2
        v = [[cx-x,cy-y,z],[cx+x,cy-y,z],[cx+x,cy+y,z],[cx-x,cy+y,z],
             [cx-x,cy-y,z+sz],[cx+x,cy-y,z+sz],[cx+x,cy+y,z+sz],[cx-x,cy+y,z+sz]]
        for f in ((0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)):
            self.quad([v[i] for i in f], mat)
        if closed:
            self.quad([v[i] for i in (4,5,6,7)], mat)
            self.quad([v[i] for i in (0,3,2,1)], mat)

    def cylinder(self, cx, cy, z, radius, height, profile=None, mat="shell", n=32):
        profile = profile or ((0,1),(0.02,1),(0.98,1),(1,1))
        rings = []
        for f, rscale in profile:
            rings.append([[cx+math.cos(2*math.pi*i/n)*radius*rscale,
                           cy+math.sin(2*math.pi*i/n)*radius*rscale,
                           z+height*f] for i in range(n)])
        for k in range(len(rings)-1):
            for i in range(n):
                j=(i+1)%n
                self.tri([rings[k][i],rings[k][j],rings[k+1][j]],mat)
                self.tri([rings[k][i],rings[k+1][j],rings[k+1][i]],mat)
        for i in range(n):
            self.tri([[cx,cy,z+height],rings[-1][i],rings[-1][(i+1)%n]],mat)
            self.tri([[cx,cy,z],rings[0][(i+1)%n],rings[0][i]],mat)

    def beam_between(self, a, b, width=55, depth=None, mat="steel"):
        """Closed rectangular brace between two 3D endpoints."""
        depth = depth or width
        v=[b[i]-a[i] for i in range(3)]
        length=math.sqrt(sum(c*c for c in v))
        u=[c/length for c in v]
        ref=[0,1,0] if abs(u[2])>.92 else [0,0,1]
        side=[u[1]*ref[2]-u[2]*ref[1],u[2]*ref[0]-u[0]*ref[2],u[0]*ref[1]-u[1]*ref[0]]
        sn=math.sqrt(sum(c*c for c in side)); side=[c/sn*width/2 for c in side]
        normal=[u[1]*side[2]-u[2]*side[1],u[2]*side[0]-u[0]*side[2],u[0]*side[1]-u[1]*side[0]]
        normal=[c*(depth/width) for c in normal]
        def corner(p,ss,nn): return [p[i]+ss*side[i]+nn*normal[i] for i in range(3)]
        va=[corner(a,-1,-1),corner(a,1,-1),corner(a,1,1),corner(a,-1,1)]
        vb=[corner(b,-1,-1),corner(b,1,-1),corner(b,1,1),corner(b,-1,1)]
        for i in range(4): self.quad([va[i],va[(i+1)%4],vb[(i+1)%4],vb[i]],mat)
        self.quad(va[::-1],mat); self.quad(vb,mat)

    def agitator(self, mount_z, height):
        self.mixer = {'mount_z_mm': mount_z, 'height_mm': height}

    def foundation(self, d, depth=None, thickness=250, piers=0, pier_h=0):
        depth = depth or d
        self.box(0,0,-thickness,d,depth,thickness,"foundation")
        if piers:
            for i in range(piers):
                a=2*math.pi*i/piers
                self.box(math.cos(a)*d*.34,math.sin(a)*depth*.34,-thickness-pier_h,
                         650,650,pier_h,"foundation")

    def ibeam(self, length, cy, base_z=-200, depth=100, height=200, flange=12, web=8):
        # I-section extruded along local X. Cross-section is 100 x 200 mm.
        y=depth/2; t=web/2; z=base_z; h=height; f=flange
        profile=[(-y,z),(y,z),(y,z+f),(t,z+f),(t,z+h-f),(y,z+h-f),
                 (y,z+h),(-y,z+h),(-y,z+h-f),(-t,z+h-f),(-t,z+f),(-y,z+f)]
        x0,x1=-length/2,length/2
        a=[[x0,cy+py,pz] for py,pz in profile]
        b=[[x1,cy+py,pz] for py,pz in profile]
        for i in range(len(profile)):
            j=(i+1)%len(profile)
            self.quad([a[i],a[j],b[j],b[i]],"steel")
        for i in range(1,len(profile)-1):
            self.tri([a[0],a[i],a[i+1]],"steel")
            self.tri([b[0],b[i+1],b[i]],"steel")

    def tank(self, item):
        tag=item["id"]; d=float(item.get("body_diameter_mm") or item["w"]); h=float(item.get("body_height_mm") or item["h"])
        tower=tag.startswith("L41B02")
        cone=tag.startswith(("L41B03","D41B01"))
        profile=([(0,.48),(.025,.5),(.82,.5),(.92,.34),(1,.10)] if tower else
                 [(0,.08),(.17,.5),(.88,.5),(.97,.44),(1,.38)] if cone else
                 [(0,1),(.02,1),(.98,1),(1,1)])
        self.cylinder(0,0,0,d/2,h,profile,"tank_white",64)
        if tag[:6] in MIXER_HEIGHTS:
            self.agitator(h, MIXER_HEIGHTS[tag[:6]])
        return d,h

    def build(self,item):
        tag=item["id"]; shape=item["shape"]; w=float(item["w"]); h=float(item["h"]); depth=float(item.get("depth") or w*.72)
        if shape=="preheater":
            self.cylinder(0,0,0,w/2,h,((0,1),(.02,1),(.98,1),(1,1)),"tank_white",64)
            self.agitator(h, MIXER_HEIGHTS[tag[:6]])
            return {"footprint_mm":[w,w],"body_diameter_mm":w,"body_height_mm":h,"body_z_mm":0,
                    **self.mixer_metadata(tag)}
        if shape in ("cylinder","tower","demister","filter"):
            d,h=self.tank(item)
            return {"footprint_mm":[d,d],"body_diameter_mm":d,"body_height_mm":h,"body_z_mm":0,
                    **self.mixer_metadata(tag)}
        if shape=="coolerPair":
            for cx in (-1200,1200):
                self.cylinder(cx,0,0,850,h,((0,.72),(.05,1),(.9,1),(.97,.82),(1,.78)),"shell",32)
            return {"footprint_mm":[w,depth],"body_height_mm":h,"units_per_model":2,"foundation_removed":True}
        if shape=="coolerUnit":
            # One individual cooler; omit the four schematic support rods and red foundation.
            self.cylinder(0,0,0,w/2,h,((0,.72),(.05,1),(.90,1),(.97,.82),(1,.78)),"shell",32)
            return {"footprint_mm":[w,w],"body_height_mm":h,"paired_platform_reference_mm":[4800,2725],"platform_center_spacing_mm":2400,"foundation_removed":True,"support_removed":True}
        if shape=="pit":
            self.box(0,0,-120,w*.9,depth*.9,120,"shell")
            return {"footprint_mm":[w,depth],"body_height_mm":h,"below_grade_mm":h,"foundation_removed":True}
        if shape=="hoist":
            self.box(0,0,h*.48,w*1.7,depth*.42,100,"machine")
            self.box(0,0,h*.2,w*.75,depth*.65,h*.38,"machine")
            self.cylinder(0,0,0,75,h*.22,((0,1),(1,1)),"machine",12)
            return {"footprint_mm":[w*1.7,depth],"body_height_mm":h,"note":"hoist lift is not physical height"}
        if shape=="pump" or tag.startswith("P41"):
            # Keep the pump casing as the equipment body; omit its simplified motor block/base.
            self.cylinder(-w*.18,0,0,w*.20,h*.62,((0,1),(.75,1),(1,.72)),"machine",20)
            return {"footprint_mm":[w*.4,depth*.55],"body_height_mm":h*.62,"dimension_status":"estimated pump casing only; motor/base omitted"}
        if tag.startswith("F41B04"):
            return self.tank(item)
        self.box(0,0,0,w,depth,h,"machine")
        return {"footprint_mm":[w,depth],"body_height_mm":h,"dimension_status":"schematic estimate"}

    def mixer_metadata(self, tag):
        if not self.mixer:
            return {}
        height_basis = '确认高度' if tag[:6] in ('C41B02', 'D41B02') else '按类型侧视比例估取'
        return {'mixer_total_height_mm': self.mixer['height_mm'], 'mixer_height_basis': height_basis,
                'mixer_geometry_source': '槽罐搅拌器_标注侧视 v0.3（01、02、03、06）'}


def source_xy(item):
    if item.get("x") is None or item.get("y") is None:
        return None,None,None
    centers={"EL100":662934,"EL106":725974,"EL112":797581,"EL123":862865}
    windows={"EL100":(630000,695000),"EL106":(695000,761000),"EL112":(761000,830000),"EL123":(830000,920000)}
    for level,center in centers.items():
        x=item["x"]+center
        if windows[level][0] <= x < windows[level][1]:
            return round(x,2),round(item["y"]+300000,2),level
    return None,None,None


def write_obj(path, mesh):
    verts=[]; faces=[]
    for tri,mat in mesh.tris:
        start=len(verts)+1
        verts.extend([[p[0]/1000,p[1]/1000,p[2]/1000] for p in tri])
        faces.append((start,start+1,start+2,mat))
    lines=["mtllib materials.mtl","o Equipment"]
    for v in verts: lines.append(f"v {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}")
    last=None
    for a,b,c,mat in faces:
        if mat!=last: lines.append(f"usemtl {MATERIALS[mat]}");last=mat
        lines.append(f"f {a} {b} {c}")
    vertex_count, face_count = len(verts), len(faces)
    if mesh.mixer:
        mount = mesh.mixer['mount_z_mm']
        for name, _, points, polygons in mixer_at(mount, mount+mesh.mixer['height_mm']):
            lines.extend([f'o {name}', f'usemtl {MATERIALS[MIXER_MATERIALS[name[:2]]]}'])
            lines.extend(f'v {x/1000:.6f} {y/1000:.6f} {z/1000:.6f}' for x,y,z in points)
            lines.extend('f '+' '.join(str(vertex_count+i+1) for i in face) for face in polygons)
            vertex_count += len(points)
            face_count += len(polygons)
    path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    return vertex_count,face_count


def write_layout_mixer():
    """Store one compact preview mesh for the multi-device layout viewer."""
    preview = []
    for part in mixer_reference():
        if part['name'].startswith('01_Fin_'):
            continue
        buckets, indices = {}, []
        for point in part['vertices']:
            key = tuple(round(value/90) for value in point)
            if key not in buckets:
                buckets[key] = [len(buckets), [0, 0, 0], 0]
            entry = buckets[key]
            for axis, value in enumerate(point):
                entry[1][axis] += value
            entry[2] += 1
            indices.append(entry[0])
        points = [[round(value/count, 1) for value in total] for _, total, count in buckets.values()]
        faces, seen = [], set()
        for face in part['faces']:
            for corner in range(1, len(face)-1):
                tri = tuple(indices[i] for i in (face[0], face[corner], face[corner+1]))
                key = tuple(sorted(tri))
                if len(set(tri)) == 3 and key not in seen:
                    faces.append(tri)
                    seen.add(key)
        if faces:
            preview.append({'vertices': points, 'faces': faces, 'color': part['color']})
    output = SOURCE.with_name('mixer_preview.js')
    output.write_text('window.LAYOUT_MIXER='+json.dumps(preview, separators=(',', ':'))+
                      ';\nwindow.LAYOUT_MIXER_HEIGHTS='+json.dumps(MIXER_HEIGHTS)+';\n', encoding='utf-8')


def main(mixers_only=False):
    source=json.loads(SOURCE.read_text(encoding="utf-8"))
    source_items=[x for level in source["levels"] for x in level["items"]]
    items=[]
    for item in source_items:
        if item["shape"]=="coolerPair":
            suffix=item["id"][6:]
            pair_members=list(suffix)
            for offset,letter in zip((-1200,1200),pair_members):
                one={**item,"id":"C41B04"+letter,"w":1700,"depth":1700,"h":3600,"shape":"coolerUnit",
                     "x":item["x"]+offset,"z":4500,"pos_el":104.5,"level":"EL106",
                     "quantity_role":"individual unit expanded from paired CAD callout",
                     "foundation":{"material":"RC","width":1950,"depth":1950,"height":180},
                     "position_basis":"CAD成对位号点；按俯视图2400mm中心距分解到单台"}
                items.append(one)
        elif item["id"]=="P41B09AB":
            for offset,letter in zip((-600,600),("A","B")):
                items.append({**item,"id":"P41B09"+letter,"x":item["x"]+offset,
                              "quantity_role":"individual unit expanded from A/B callout",
                              "position_basis":"A/B共用CAD位号点；单泵坐标由并列关系估分"})
        else:
            items.append(item)
    if not any(x["id"]=="P41A08" for x in items):
        items.append({"id":"P41A08","group":"P41A08","name":"偏钛酸转运泵",
                      "spec":"流量Q=120m3/h，扬程H=20m","qty":"1","x":None,"y":None,
                      "z":0,"level":"未定位","pos_el":None,"w":1200,"h":700,"depth":850,
                      "shape":"pump","position_basis":"台账有设备；本布置图内未找到可确认的对应位号位置",
                      "height_basis":"泵外形按同系列P41B08示意，未取得总图尺寸"})
    for name in ("obj","parameters","screenshots"):
        (ROOT/name).mkdir(parents=True,exist_ok=True)
    (ROOT/"materials.mtl").write_text(MTL,encoding="utf-8")
    catalog_path, viewer_path = ROOT/'catalog.json', ROOT/'viewer_data.js'
    if mixers_only:
        old_catalog = json.loads(catalog_path.read_text(encoding='utf-8-sig'))['models']
        old_viewer = json.JSONDecoder().raw_decode(viewer_path.read_text(encoding='utf-8-sig').split('=',1)[1])[0]
    catalog=[]; viewer=[]
    for item in items:
        if mixers_only and item['id'][:6] not in MIXER_HEIGHTS:
            continue
        if item["id"].startswith("C41B02"):
            item={**item,
                  "ledger_spec":item.get("spec"),
                  "model_spec":"Ø5900 × 4700 mm（用户指定）",
                  "drawing_pos_el":item.get("pos_el"),
                  "pos_el":100.3,"level":"EL100","z":0,
                  "w":5900,"h":4700,"depth":5900,"shape":"preheater",
                  "position_basis":"槽体底面按用户指定EL100.300；平面位置保留布置图位号点"}
        if item["shape"] in ("cylinder","preheater","tower","demister","filter"):
            has_mixer=item["id"][:6] in MIXER_HEIGHTS
            item={**item,"source_foundation":item.get("foundation"),"source_support":item.get("support"),
                  "foundation":None,"support":None,
                  "model_scope":"槽罐本体与顶部搅拌；不含基础及底部支撑" if has_mixer else "设备本体；不含基础及底部支撑"}
        if item.get("foundation") is not None:
            item={**item,"source_foundation":item.get("source_foundation",item["foundation"]),"foundation":None}
        if item["shape"] in ("coolerUnit","coolerPair"):
            item={**item,"source_support":item.get("support"),"support":None,
                  "model_scope":"冷却器本体；不含基础及底部支撑"}
        mesh=Mesh(); geom=mesh.build(item)
        ident=item["id"]
        x,y,plan_sheet=source_xy(item)
        model={**item,**geom,"cad_position_mm":[x,y],"plan_sheet":plan_sheet,
               "coordinate_reference":("no confirmed placement coordinate in supplied layout" if x is None else "DXF model-space point at equipment tag insertion; approximate equipment center"),
               "coordinate_system":"local model: X east, Y north, Z up; OBJ meters, Z-up",
               "large_equipment":(item["w"]>=2800 or item["h"]>=3000 or item["shape"]=="coolerUnit")}
        obj=ROOT/"obj"/(ident+".obj")
        nv,nf=write_obj(obj,mesh)
        (ROOT/"parameters"/(ident+".json")).write_text(json.dumps(model,ensure_ascii=False,indent=2),encoding="utf-8")
        catalog.append({k:model[k] for k in ("id","group","name","spec","model_spec","ledger_spec","drawing_pos_el","qty","level","pos_el","cad_position_mm","plan_sheet","w","h","shape","large_equipment","position_basis","height_basis") if k in model})
        # Flatten triangles for the offline viewer; OBJ remains the independent source mesh.
        viewer.append({"id":ident,"group":item["group"],"name":item["name"],"level":item["level"],"w":item["w"],"h":item["h"],"shape":item["shape"],"spec":item["spec"],"model_spec":item.get("model_spec"),"ledger_spec":item.get("ledger_spec"),"drawing_pos_el":item.get("drawing_pos_el"),"body_z_mm":geom.get("body_z_mm",0),"mixer_total_height_mm":geom.get("mixer_total_height_mm"),"mixer_height_basis":geom.get("mixer_height_basis"),"pos_el":item.get("pos_el"),"cad":[x,y],"foundation":geom.get("foundation",item.get("foundation")),"support":geom.get("support",item.get("support")),"model_scope":item.get("model_scope"),"large":model["large_equipment"],"position_basis":item.get("position_basis",""),"tris":[{"v":[[p[0]/1000,p[1]/1000,p[2]/1000] for p in tri],"m":mat} for tri,mat in mesh.tris]})
        if mesh.mixer:
            viewer[-1]['mixer'] = mesh.mixer
        if mixers_only:
            continue
        # Preserve screenshot sources as copies; originals remain untouched.
        shot_map={
            "C41B01":("热水预热槽-俯视图.png","热水预热槽-侧视图.png"),
            "C41B02":("钛液预热槽-俯视图.png","钛液预热槽-侧视图.png"),
            "C41B03":("稀碱预热槽-俯视图.png","稀碱预热槽-侧视图.png"),
            "C41B04":("偏钛酸冷却器-俯视图.png","偏钛酸冷却器-侧视图.png"),
            "D41B01":("晶种制备槽-俯视图.png","晶种制备槽-侧视图.png"),
            "D41B02":("水解槽-俯视图.png","水解槽-侧视图.png"),
            "F41B01":("偏钛酸缓冲槽-俯视图.png","偏钛酸缓冲槽-侧视图.png"),
            "F41B02":("钛液事故槽、稀碱配置槽、稀碱储槽-俯视图.png","钛液事故槽、稀碱配置槽、稀碱储槽-侧视图.png"),
            "F41B05":("钛液事故槽、稀碱配置槽、稀碱储槽-俯视图.png","钛液事故槽、稀碱配置槽、稀碱储槽-侧视图.png"),
            "F41B06":("钛液事故槽、稀碱配置槽、稀碱储槽-俯视图.png","钛液事故槽、稀碱配置槽、稀碱储槽-侧视图.png"),
            "F41B04":("尾气洗涤塔、烟囱、除雾器-俯视图.png","尾气洗涤塔、烟囱、除雾器-侧视图.png"),
            "L41B02":("尾气洗涤塔、烟囱、除雾器-俯视图.png","尾气洗涤塔、烟囱、除雾器-侧视图.png"),
            "L41B03":("尾气洗涤塔、烟囱、除雾器-俯视图.png","尾气洗涤塔、烟囱、除雾器-侧视图.png"),
            "V41B":(None,"电动葫芦-侧视图.png")}
        prefix=next((p for p in shot_map if ident.startswith(p)),None)
        if prefix:
            for view,filename in zip(("俯视图","侧视图"),shot_map[prefix]):
                if filename:
                    src=SCREEN_SOURCE/filename
                    if src.exists(): shutil.copy2(src,ROOT/"screenshots"/(ident+"-"+view+".png"))
    generated = len(catalog)
    if mixers_only:
        def merge(existing, updated):
            by_id = {item['id']: item for item in updated}
            return [by_id.get(item['id'], item) for item in existing]
        catalog, viewer = merge(old_catalog, catalog), merge(old_viewer, viewer)
    catalog_path.write_text(json.dumps({"version":"0.2","units":"mm","count":len(catalog),"source":source["source_ledger"],"models":catalog},ensure_ascii=False,indent=2),encoding="utf-8")
    reference = [{'vertices': p['vertices'], 'faces': p['faces'], 'm': MIXER_MATERIALS[p['name'][:2]]}
                 for p in mixer_reference()]
    viewer_path.write_text("window.MODELS="+json.dumps(viewer,ensure_ascii=False,separators=(",",":"))+
                           ";\nwindow.ANNOTATED_MIXER="+json.dumps(reference,separators=(",",":"))+";",encoding="utf-8")
    write_layout_mixer()
    print(f"generated {generated} individual OBJ/JSON models")


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--mixers-only', action='store_true')
    main(parser.parse_args().mixers_only)
