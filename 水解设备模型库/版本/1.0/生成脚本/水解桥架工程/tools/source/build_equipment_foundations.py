
"""Generate stand-alone foundations from the checked DXF dimension schedule."""
import json
from hashlib import sha256
from math import acos, ceil, cos, pi, sin, sqrt
from pathlib import Path
import re
import sys

from build_tank_mixer import add, box, brace, cyl, export_model, parts

PROJECT = Path(__file__).resolve().parents[2]
RAW = PROJECT / 'data/原始资料/设备基础'
OUT = PROJECT / 'models/设备/设备基础_20261106'
LIBRARY = PROJECT.parent / '水解设备模型库'
sys.path.insert(0,str(LIBRARY/'tools'))
from build_sheet_models import ARCHIVE_PORT_HANDLES, archive_ports, axial
DXF = RAW / '水解设备基础图.dxf'
TOWER_DXF = RAW / '水解设备基础图_增补烟囱及洗涤塔钢塔架_20261106.dxf'
CONCRETE, GROUT, BLINDING = '#9e9690', '#beb7ae', '#807a74'
STEEL, PLATE = '#697d86', '#87979b'


def block(name, x0, x1, y0, y1, z0, z1, color=CONCRETE):
    box(name, ((x0+x1)/2, (y0+y1)/2, (z0+z1)/2), (x1-x0, y1-y0, z1-z0), color)


def translate_last(x, y):
    name, color, vertices, faces = parts[-1]
    parts[-1] = name, color, [(a+x,b+y,z) for a,b,z in vertices], faces


def round_base(diameter, height, blinding=0, pitch=0):
    cyl('基础_混凝土', -height, -50, diameter/2, CONCRETE, 96)
    cyl('基础_二次浇筑层', -50, 0, diameter/2, GROUT, 96)
    if blinding:
        cyl('基础_混凝土垫层', -height-blinding, -height, diameter/2+100, BLINDING, 96)
    if pitch:
        for i in range(12):
            angle=i*pi/6
            cyl(f'地脚螺栓_M24_{i+1:02}', 0, 200, 12, STEEL, 16)
            translate_last(pitch/2*cos(angle),pitch/2*sin(angle))


def circular_strip(name, radius, left, right, z0, z1, color):
    start, end = acos(right/radius), acos(left/radius)
    steps = ceil((end-start)/(pi/48))
    top = [(radius*cos(t), radius*sin(t)) for t in
           (start+(end-start)*i/steps for i in range(steps+1))]
    loop = top + [(x,-y) for x,y in reversed(top) if abs(y)>1e-8]
    n = len(loop)
    vertices = [(x,y,z) for z in (z0,z1) for x,y in loop]
    faces = [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    faces += [tuple(reversed(range(n))), tuple(range(n,2*n))]
    add(name,color,vertices,faces)


def hydrolysis():
    cyl('基础_C40承台', -2500, -2000, 3350, CONCRETE, 96)
    cyl('基础_混凝土垫层', -2600, -2500, 3450, BLINDING, 96)
    left=-3050
    for i,width in enumerate((800,300,300,300,300,300,800),1):
        right=left+width
        circular_strip(f'基础_混凝土肋{i}',3050,left,right,-2000,-50,CONCRETE)
        circular_strip(f'基础_二次浇筑层{i}',3050,left,right,-50,0,GROUT)
        left=right+500


def pump_base(length, width, height, bolt_x, bolt_y, grout):
    xs=(250-length/2,250+bolt_x-length/2)
    ys=(-bolt_y/2,bolt_y/2)
    x_edges=[-length/2,*[x+d for x in xs for d in (-60,60)],length/2]
    y_edges=[-width/2,*[y+d for y in ys for d in (-60,60)],width/2]
    z_edges=[-height,-500,-grout,0] if grout else [-height,-500,0]
    occupied={(i,j,k):GROUT if grout and k==2 else CONCRETE
              for i in range(5) for j in range(5) for k in range(len(z_edges)-1)
              if not (k and i in (1,3) and j in (1,3))}
    offsets=((0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1))
    sides=(((0,0,-1),(0,3,2,1)),((0,0,1),(4,5,6,7)),((0,-1,0),(0,1,5,4)),
           ((1,0,0),(1,2,6,5)),((0,1,0),(2,3,7,6)),((-1,0,0),(3,0,4,7)))
    for color in sorted(set(occupied.values())):
        indices, faces = {}, []
        for (i,j,k),material in occupied.items():
            if material!=color:
                continue
            for (di,dj,dk),corners in sides:
                if occupied.get((i+di,j+dj,k+dk))==color:
                    continue
                face=[]
                for corner in corners:
                    a,b,c=offsets[corner]
                    vertex=(x_edges[i+a],y_edges[j+b],z_edges[k+c])
                    face.append(indices.setdefault(vertex,len(indices)))
                faces.append(face)
        name='基础_C35二次浇筑层' if color==GROUT else '基础_带预留孔的混凝土'
        add(name,color,list(indices),faces)


def fan_base():
    block('基础_混凝土',-1750,1750,-1400,1400,-100,-50)
    block('基础_二次浇筑层',-1750,1750,-1400,1400,-50,0,GROUT)


def seed_pair_rack():
    # Bearing lines pass under the four wing lugs of each vessel.
    for x in (-1059,1059):
        block('钢架_纵向承托梁',x-80,x+80,-2559,2559,-200,0,STEEL)
        for y in (-2359,0,2359):
            block('钢架_立柱',x-80,x+80,y-80,y+80,-2500,-200,STEEL)
    for y in (-2359,-241,241,2359):
        block('钢架_横向承托梁',-979,979,y-80,y+80,-200,0,STEEL)


def pit(number):
    block('基础_垫层',-1100,1100,-1100,1100,-2350,-2250,BLINDING)
    block('基础_底板',-1000,1000,-1000,1000,-2250,-2000)
    block('基础_东壁',750,1000,-1000,1000,-2000,0)
    block('基础_南壁',-750,750,-1000,-750,-2000,0)
    if number==1:
        block('基础_西壁',-1000,-750,-1000,750,-2000,0)
        block('基础_北壁',-1000,-850,750,1000,-2000,0)
        block('基础_缺口下方',-850,-550,750,1000,-2000,-400)
        block('基础_北壁',-550,750,750,1000,-2000,0)
    else:
        block('基础_北壁',-750,750,750,1000,-2000,0)
        block('基础_西壁',-1000,-750,-1000,-150,-2000,0)
        block('基础_缺口下方',-1000,-750,-150,150,-2000,-800)
        block('基础_西壁',-1000,-750,150,1000,-2000,0)


def pedestals(pads, height, plate, first_plate_offset=0):
    pw,pd,pt=plate
    for i,(x,y,w,d) in enumerate(pads,1):
        # MJ-b may be offset from the center of the concrete support.
        px=x+(first_plate_offset if i==1 else 0)
        x0,x1,y0,y1=x-w/2,x+w/2,y-d/2,y+d/2
        a,b,c,e=px-pw/2,px+pw/2,y-pd/2,y+pd/2
        name=f'基础_混凝土支墩{i}'
        block(name,x0,x1,y0,y1,-height,-pt)
        for lo,hi,front,back in ((x0,a,y0,y1),(b,x1,y0,y1),(a,b,y0,c),(a,b,e,y1)):
            if hi>lo and back>front:
                block(name,lo,hi,front,back,-pt,0)
        block(f'预埋板_支墩顶板{i}',a,b,c,e,-pt,0,PLATE)


def portal(x_span,y_span,height,y_offset=0,braced=False):
    x,y=x_span/2,y_span/2
    for cx in (-x,x):
        for cy in (y_offset-y,y_offset+y):
            block('基础_柱脚墩',cx-225,cx+225,cy-225,cy+225,0,200)
            for dx in (-120,106):
                block('钢架_GZ1柱翼缘',cx+dx,cx+dx+14,cy-120,cy+120,200,height,STEEL)
            block('钢架_GZ1柱腹板',cx-106,cx+106,cy-5,cy+5,200,height,STEEL)
    for cy in (y_offset-y,y_offset+y):
        for dz in (-240,-14):
            block('钢架_GL1横梁翼缘',-x,x,cy-120,cy+120,height+dz,height+dz+14,STEEL)
        block('钢架_GL1横梁腹板',-x,x,cy-5,cy+5,height-226,height-14,STEEL)
        if braced:
            for side in (-1,1):
                brace('钢架_ZC1斜撑',side*(x-120),1500,side*262.5,height-240,100,100,STEEL)
                translate_last(0,cy)
    for cx in ((-x,-262.5,262.5,x) if braced else (-x,x)):
        for dz in (-240,-14):
            block('钢架_GL1纵梁翼缘',cx-120,cx+120,y_offset-y,y_offset+y,height+dz,height+dz+14,STEEL)
        block('钢架_GL1纵梁腹板',cx-5,cx+5,y_offset-y,y_offset+y,height-226,height-14,STEEL)


def cooler_frames():
    for y in (4200,0,-3000):
        portal(4275,1875,4500,y,True)


def demister_frame():
    portal(2800,2400,2000)
    for x0,x1,y0,y1 in [(-1400,-1025,-1200,1200),(1025,1400,-1200,1200),(-1025,1025,850,1200)]:
        block('钢平台_6mm花纹钢板',x0,x1,y0,y1,1994,2000,PLATE)


def steel_tube(name, start, end, diameter=89, wall=3.5):
    axial(name, start, end, diameter/2, STEEL, inner_radius=diameter/2-wall)


def tower_post(x, y, top, diameter, wall, plate_width, plate_height, angle=0):
    for name, width, z0, z1, color in (
        ('支墩_混凝土',500,0,600,CONCRETE),
        ('钢塔架_柱脚板',plate_width,600,600+plate_height,PLATE),
    ):
        box(name,(0,0,(z0+z1)/2),(width,width,z1-z0),color)
        name,color,vertices,faces=parts[-1]
        parts[-1]=name,color,[(x+a*cos(angle)-b*sin(angle),y+a*sin(angle)+b*cos(angle),z)
                              for a,b,z in vertices],faces
    steel_tube('钢塔架_GJ01立柱',(x,y,600+plate_height),(x,y,top),diameter,wall)


def cross_braces(a, b, z0, z1, name='钢塔架_GJ03交叉撑'):
    steel_tube(name,(*a,z0),(*b,z1))
    steel_tube(name,(*b,z0),(*a,z1))


def chimney_platform(left, right, south, north):
    landing_z, landing_y, east = 4800, south+1125, right+1100
    for a,b,c,d in ((left,right,south,north),(right,east,south,landing_y)):
        block('检修平台_6mm花纹钢板',a,b,c,d,landing_z-6,landing_z,PLATE)
    for y in (south,landing_y,north):
        block('检修平台_GJ05横梁',left,east if y!=north else right,y-40,y+40,landing_z-166,landing_z-6,STEEL)
    for x in (left,left+895,left+1790,right,east):
        block('检修平台_GJ06纵梁',x-30,x+30,south,landing_y if x==east else north,landing_z-126,landing_z-6,STEEL)
    steel_tube('检修平台_GJ07托撑',(right,south,3700),(east,south,landing_z-120))
    steel_tube('检修平台_GJ08斜撑',(right,south,landing_z-86),(east,landing_y,landing_z-86))
    rails=[(left,south),(east,south),(east,landing_y),(right,landing_y),(right,north),(left,north),(left,south)]
    for a,b in zip(rails,rails[1:]):
        if a==(east,landing_y):  # opening into the stairs
            continue
        for z in (landing_z+600,landing_z+1200):
            steel_tube('栏杆_LG2-1200',(*a,z),(*b,z),42,3)
        length=((b[0]-a[0])**2+(b[1]-a[1])**2)**0.5
        divisions=ceil(length/1000)
        for i in range(divisions+1):
            x,y=(u+(v-u)*i/divisions for u,v in zip(a,b))
            steel_tube('栏杆_立杆',(x,y,landing_z),(x,y,landing_z+1200),42,3)
    run, bottom_z = 4500, 300
    for i in range(1,15):
        front=landing_y+run-(i+1)*300
        z=bottom_z+i*300
        block('检修钢梯_踏步',right+50,east-50,front,front+300,z-6,z,PLATE)
    block('检修钢梯_C15起步墩',right+50,east-50,landing_y+run-300,landing_y+run,0,bottom_z)
    for x in (right+50,east-50):
        steel_tube('检修钢梯_梯梁',(x,landing_y+run,bottom_z),(x,landing_y,landing_z-120),89,4)
        for offset in (600,1200):
            steel_tube('检修钢梯_斜栏杆',(x,landing_y+run,bottom_z+offset),(x,landing_y,landing_z+offset),42,3)
        for i in range(5):
            y,z=landing_y+900*i,landing_z-900*i
            steel_tube('检修钢梯_栏杆立杆',(x,y,z),(x,y,z+1200),42,3)


def chimney_frame():
    left, right = -1342.5, 1342.5
    south, north = -3100, -775
    rear_triangle=((left,north),(right,north),(0,1550))
    for x,y in rear_triangle:
        tower_post(x,y,13800,152,6,402,20)
    for x in (left,right):
        tower_post(x,south,4800,152,6,402,20)
    levels=(600,3000,5700,8400,11100,13800)
    for a,b in zip(rear_triangle,(*rear_triangle[1:],rear_triangle[0])):
        for z0,z1 in zip(levels,levels[1:]):
            beam_z=min(z1,13800-44.5)
            steel_tube('钢塔架_GJ02水平杆',(*a,beam_z),(*b,beam_z))
            cross_braces(a,b,max(z0,620),beam_z)
    # In-plane GJ04 restraint rods traced from the triangular plan.
    stops=(((-577.4,549.9),(577.4,549.9)),((187.5,-775),(765,-224.9)),((-187.5,-775),(-765,-224.9)))
    for z in levels[1:]:
        beam_z=min(z,13800-44.5)
        for a,b in stops:
            steel_tube('钢塔架_GJ04限位杆',(*a,beam_z),(*b,beam_z))
    for a,b in (((left,south),(right,south)),((left,south),(left,north)),((right,south),(right,north))):
        cross_braces(a,b,620,4720,'检修平台_GJ07交叉撑')
    chimney_platform(left,right,south,north)


def scrubber_frame():
    radius=2400/sqrt(2)
    corners=((radius,0),(0,radius),(-radius,0),(0,-radius))
    for x,y in corners:
        tower_post(x,y,8300,108,4,250,16,pi/4)
    for a,b in zip(corners,(*corners[1:],corners[0])):
        midpoint=tuple((x+y)/2 for x,y in zip(a,b))
        for base in (a,b):
            steel_tube('钢塔架_GJ03倒V撑',(*base,616),(*midpoint,3300))
        for z0,z1 in ((3300,5800),(5800,8300-44.5)):
            cross_braces(a,b,z0,z1)
        for z in (3300,5800,8300-44.5):
            steel_tube('钢塔架_GJ02水平杆',(*a,z),(*b,z))
    # GJ04 ends are read from the plan; final clearance is field-set.
    for corner, before, after in zip(corners,(corners[-1],*corners[:-1]),(*corners[1:],corners[0])):
        a,b=[tuple(x+(y-x)*(773.65/2400) for x,y in zip(corner,neighbor)) for neighbor in (before,after)]
        for z in (3300,5800,8300-44.5):
            steel_tube('钢塔架_GJ04限位杆',(*a,z),(*b,z))


def entry(name, tags, crop, handles, dimensions, note, build, mount=None,
          *, kind='基础', basis=None, offsets=None, combined_label=None, fixture_prefix=None,
          source=DXF, companion=None):
    return locals()


RECORDS = {
    'C41B01': entry('热水预热槽基础',['C41B01'],'c01','2F1B 2F5C 2F74 2F3A 2F54 2F79',
        'Ø3600 × 200 mm，含 50 mm 二次浇筑层。楼面标高 12.000 m。',
        '按楼面以上台座建模，合看以槽底接触基础顶面。',lambda:round_base(3600,200),(0,0,0)),
    'C41B02': entry('钛液预热槽基础',['C41B02'],'c02','2DE8 2E38 2E3B 2E16 2E30 2E55',
        'Ø5700 × 150 mm，含 50 mm 二次浇筑层。楼面标高 12.000 m。',
        '合看以槽底接触基础顶面，楼面梁板延伸部分未计入。',lambda:round_base(5700,150),(0,0,0)),
    'C41B03': entry('稀碱预热槽基础',['C41B03'],'c03','2FF0 3026 3029 3004 301E 3035',
        'Ø1600 × 200 mm，含 50 mm 二次浇筑层。楼面标高 12.000 m。',
        '按 3-3 剖面标注的楼面以上台座建模。',lambda:round_base(1600,200),(0,0,0)),
    'C41B04': entry('偏钛酸冷却器钢框架',['C41B04'],'c04','36ED 3714 36FE 3725 3702 3713 373C 3740 3743 3745 3746 3759 3762 37C9',
        '3 组双机钢框架，每组柱轴距 4275 × 1875 mm，双机中心距 2400 mm，承托面高 4500 mm。',
        '每台按所在梁跨中心就位，两侧设备托耳与 4.500 m 梁顶贴合。GZ1、GL1、ZC1 截面细部示意。',
        cooler_frames,(0,0,0),kind='安装支架',combined_label='三对设备与钢架',
        offsets=tuple((x,y,0) for y in (4200,0,-3000) for x in (-1200,1200))),
    'D41B01': entry('晶种制备槽双机安装支架',['D41B01'],None,'',
        '南北槽中心距 2600 mm，托耳承托面距示意支架底 2500 mm。',
        'B/C 与 D/E 为已识别配对，A 的支架组合未确认。预览以 B/C 平面为样本，南槽镜像布置。俯视及定位点中心距 2600 mm，侧视另标 2500 mm。支架高度参考 EL108.500 至 POSEL111.000，型钢截面暂按示意。',
        seed_pair_rack,(0,0,1180),kind='安装支架',basis='设备布置平面及剖面',combined_label='双槽与支架',
        offsets=((0,-1300,0),(0,1300,0))),
    'D41B02': entry('水解槽带肋基础',['D41B02'],'d41','DB2 DD6 DC5 DC6 DC7 DD1 E9C E8D E8B E8C E8E E8F E73 E74 E75 EBB',
        '上部 Ø6100 mm，7 道肋，两侧宽 800 mm、中间宽 300 mm、净间隔 500 mm。顶 +1.500 m，承台顶 −0.500 m，承台底 −1.000 m。',
        '肋顶含 50 mm 二次浇筑层。承台、垫层宽按剖面 6700、6900 mm，平面按同心圆表达，垫层厚按剖面量测 100 mm。合看以槽底接触肋顶。',hydrolysis,(0,0,0)),
    'F41B01': entry('偏钛酸缓冲槽基础',['F41B01'],'f01','12C0 12BA 1307 12FE 12FF 12AB 12C1 12C2',
        'Ø5200 mm，顶 +0.300 m，底 −1.000 m，含 50 mm 二次浇筑层，垫层每侧宽出 100 mm。',
        '垫层厚按剖面量测 100 mm，合看以槽底接触基础顶面。',lambda:round_base(5200,1300,100),(0,0,0)),
    'F41B02': entry('钛液事故槽、稀碱配置槽、稀碱储槽共用基础',['F41B02','F41B05','F41B06'],'f02','1517 1480 147F 150C 14DD 14D4 14D5 1488 1497 1498',
        'Ø3000 mm，顶 +0.300 m，底 −1.000 m，含 50 mm 二次浇筑层，垫层每侧宽出 100 mm。',
        '三槽共用平剖图。垫层厚按剖面量测 100 mm，合看以槽底接触基础顶面。',lambda:round_base(3000,1300,100),(0,0,0)),
    'F41B03': entry('冷凝水分汽器四支墩',['F41B03'],'f03','2B03 2B06 2B07 2B08 2B09 2B10 2B11 2B14 2B78 2B7B 2B3C',
        '4 个 300 × 300 mm 支墩，相对中心距 1500 mm，露出楼面 100 mm。',
        '设备俯视托耳外端距中心约 591 mm，支墩内缘为 600 mm，预埋中心位置也不同。过渡件待核，支墩独立展示。',
        lambda:pedestals([(750,0,300,300),(-750,0,300,300),(0,750,300,300),(0,-750,300,300)],100,(300,300,10))),
    'F41B04': entry('尾气烟囱基础',['F41B04'],'f04','3142 3136 3149 314B 312E 3114 3147 314E 3152',
        'Ø1400 × 300 mm，含 50 mm 二次浇筑层。螺栓分度圆 Ø1200 mm，12-M24，露头 200 mm。',
        '楼面标高 23.000 m，合看按筒体同心就位，底法兰及螺栓配合待核。',lambda:round_base(1400,300,pitch=1200),(0,0,0)),
    'F41B04-钢塔架': entry('尾气烟囱钢塔架',['F41B04'],None,
        '8C0E 8C44 8D50 8DC4 8DFD 8DFE 8E16 8EDD 8EF1 8F1C 8F1D 8F2F 8F3A 8F4F 8F98 8FA4 8FAD 8FB9 903A 9093 9124 9169 91C1 9387',
        '三柱钢塔架顶标高 36.800 m，支墩 500 × 500 × 600 mm，主柱 Ø152 × 6 mm。高架柱横向轴距 2685 mm，三角形进深 2325 mm。检修平台标高 27.800 m，6 mm 花纹钢板，栏杆高 1200 mm。',
        '以 23.000 m 楼面为基准，三根高柱与两根平台柱按俯视定位。GJ04 按平面布置在各水平层。节点、平台梁截面及钢梯细部作示意。图上方向用于独立浏览，厂房绝对定位待核。',
        chimney_frame,(0,0,-300),kind='安装支架',source=TOWER_DXF,companion='F41B04',
        combined_label='烟囱与钢塔架及基础'),
    'F41B07-1': entry('1#集水坑',['F41B07'],'pit','1920 1927 192C 18DB 197E 18F3 18F4 18EE',
        '净空 1500 × 1500 × 2000 mm，壁厚及底板厚 250 mm，垫层 100 mm，缺口 300 × 400 mm（深）。',
        '按图名独立列示，A/B 位号对应关系待核。保留接地沟缺口。',lambda:pit(1)),
    'F41B07-2': entry('2#集水坑',['F41B07'],'pit','187A 1881 1886 1874 197E 18F3 18F4 18EE',
        '净空 1500 × 1500 × 2000 mm，壁厚及底板厚 250 mm，垫层 100 mm，缺口 300 × 800 mm（深）。',
        '按图名独立列示，A/B 位号对应关系待核。保留接地沟缺口。',lambda:pit(2)),
    'F41B08': entry('密封水循环槽暂定基础',['F41B08'],None,'',
        '暂定 Ø1100 × 200 mm，按 Ø1000 mm 槽体外径加 100 mm。',
        '按用户暂定方案建圆形混凝土台座，绝对楼面标高及浇筑构造待基础详图。',
        lambda:cyl('基础_暂定混凝土',-200,0,550,CONCRETE,96),(0,0,0),basis='用户暂定方案'),
    'L41B01': entry('水解过滤器暂定基础',['L41B01'],None,'',
        '暂定 Ø1300 × 200 mm，按 Ø1200 mm 筒体外径加 100 mm。',
        '与密封水循环槽采用同一暂定规则，绝对楼面标高及浇筑构造待基础详图。',
        lambda:cyl('基础_暂定混凝土',-200,0,650,CONCRETE,96),(0,0,0),basis='用户暂定方案'),
    'L41B02': entry('尾气洗涤塔基础',['L41B02'],'l02','3274 329E 326E 32C4 3296 3281 32B1 32B7 32BC',
        'Ø2600 × 300 mm，含 50 mm 二次浇筑层。螺栓分度圆 Ø2400 mm，12-M24，露头 200 mm。',
        '楼面标高 23.000 m，合看按塔体同心就位，底法兰及螺栓配合待核。',lambda:round_base(2600,300,pitch=2400),(0,0,0)),
    'L41B02-钢塔架': entry('尾气洗涤塔钢塔架',['L41B02'],None,
        '9F62 9F63 9F98 A026 A02C A035 A03D A07E A07F A080 A08D A093 A094 A096 A09A A134 A139 A19D A1A5 A1A6 A1AD A1B4 A1BB A304',
        '柱轴距 2400 × 2400 mm。楼面 23.000 m，柱脚 23.600 m，钢架顶 31.300 m。4 个 500 × 500 × 600 mm 支墩，GJ01 Ø108 × 4 mm，柱脚板 250 × 250 × 16 mm。',
        '按基础平面采用四角呈菱形的布置，底层倒 V 撑，上两层交叉撑。GJ04 限位杆按俯视分层示意，贴塔尺寸以现场放样为准。组合中 26.300 m 层南侧限位杆与既有模型的中下接口相交，该处需复核。厂房绝对定位待核。',
        scrubber_frame,(0,0,-300),kind='安装支架',source=TOWER_DXF,companion='L41B02',
        combined_label='洗涤塔与钢塔架及基础'),
    'L41B03': entry('旋流除雾器钢支架',['L41B03'],'l03','3BA7 3B63 3BB6 3BB7 3BBA 3BBC 3BC9 3BCD 3BCE 3BD3',
        '柱轴距 2800 × 2400 mm，高 2000 mm（23.000 至 25.000 m），柱脚墩高 200 mm。6 mm 花纹钢板，开口 2050 × 2050 mm。',
        '设备按开口中心偏移 175 mm。四向设备托耳落在 25.000 m 平台与承梁，锥体及下排口穿过开口。GZ1、GL1 截面细部示意。',
        demister_frame,(0,0,0),kind='安装支架',offsets=((0,-175,-450),)),
    'L41B04': entry('减温减压器基础',['L41B04'],'l04','2626 2624 2616 261C 2611 2623 2622 2625 266D 268E 2698 264A',
        '两支座为 2650 × 500 mm、500 × 500 mm，高 230 mm，MJ-b 中心距 3300 mm。',
        'MJ-b 预埋板 400 × 400 × 12 mm，顶标高 12.300 m。现有设备缺安装支座，基础独立展示。',
        lambda:pedestals([(-300,0,2650,500),(3300,0,500,500)],230,(400,400,12),first_plate_offset=300)),
    'L41B05': entry('蒸汽分汽缸基础',['L41B05'],'l05','215E 2167 2168 2175 219A 21A5 21C1',
        '单墩 1100 × 400 × 230 mm，MJ-a 预埋板 800 × 300 × 12 mm，顶标高 12.300 m。',
        '详图给单墩。按设备图 2400 mm 鞍座中心距布置两墩，组合时显示两只设备鞍座。鞍座和预埋板的安装孔位待核。',
        lambda:pedestals([(0,-1200,1100,400),(0,1200,1100,400)],230,(800,300,12)),(0,0,0),
        fixture_prefix='鞍座_'),
    'P41B01': entry('水解料中转泵基础',['P41B01'],'p01','4037 4039 3F87 3F91 3FB3 3FBD 3FC4 3FCF 3FC8',
        '1475 × 1095 × 950 mm，顶 +0.050 m，底 −0.900 m。4 个 120 × 120 × 500 mm 预留孔，孔距 915 × 615 mm。',
        '50 mm C35 二次浇筑层。通用泵模型底脚孔位待核，泵座独立展示。',lambda:pump_base(1475,1095,950,915,615,50)),
    'P41B02': entry('一洗压滤供料泵基础',['P41B02'],'p02','403B 403D 3FFB 3FF1 4015 402B 4031 4034 4019',
        '1405 × 1040 × 1040 mm，顶 +0.440 m，底 −0.600 m。4 个 120 × 120 × 500 mm 预留孔，孔距 805 × 560 mm。',
        '二次浇筑厚度图中未单列。通用泵模型底脚孔位待核，泵座独立展示。',lambda:pump_base(1405,1040,1040,805,560,0)),
    'P41B10': entry('尾气风机基础',['P41B10'],'p10','33B4 33DD 33B1 33B2 33B3 33F3 33EB 33D7',
        '3500 × 2800 × 100 mm，含 50 mm 二次浇筑层。楼面标高 23.000 m。',
        '传动底座和蜗壳支架随设备展示。整机就位标高待核，土建基础独立展示。',fan_base),
}

# Above datum, below datum, and blinding thickness in mm. Floor levels use the
# drawing's notation. A local floor label is used where no EL is stated.
LEVELS = {
    'C41B01':(200,0,0,'楼面 12.000 m'), 'C41B02':(150,0,0,'楼面 12.000 m'),
    'C41B03':(200,0,0,'楼面 12.000 m'), 'C41B04':(4500,0,0,'楼面 ±0.000 m'),
    'D41B01':(2500,0,0,'支架底 · 图示 EL108.500 m'), 'D41B02':(1500,1000,100,'地面 ±0.000 m'),
    'F41B01':(300,1000,100,'地面 ±0.000 m'), 'F41B02':(300,1000,100,'地面 ±0.000 m'),
    'F41B03':(100,0,0,'楼面'), 'F41B04':(300,0,0,'楼面 23.000 m'),
    'F41B04-钢塔架':(13800,0,0,'楼面 23.000 m'),
    'F41B07-1':(0,2250,100,'地面 ±0.000 m'), 'F41B07-2':(0,2250,100,'地面 ±0.000 m'),
    'F41B08':(200,0,0,'暂定楼面'), 'L41B01':(200,0,0,'暂定楼面'),
    'L41B02':(300,0,0,'楼面 23.000 m'), 'L41B02-钢塔架':(8300,0,0,'楼面 23.000 m'),
    'L41B03':(2000,0,0,'楼面 23.000 m'),
    'L41B04':(230,0,0,'楼面'), 'L41B05':(230,0,0,'楼面'),
    'P41B01':(50,900,0,'地面 ±0.000 m'), 'P41B02':(440,600,0,'地面 ±0.000 m'),
    'P41B10':(100,0,0,'楼面 23.000 m'),
}


def equipment_only():
    """Publish cleaned exports and leave the underlying archive mesh intact."""
    batch=LIBRARY/'示图建模_20260521'/'模型'
    archives=LIBRARY/'设备档案'
    omitted=('基础_','支撑_','支脚_','鞍座_','Leg_','Pad_','驱动_轴承座底脚','驱动_电机底脚')
    result={}
    for source in sorted([*batch.glob('*/model_data.js'),*archives.glob('*/model_data.js')]):
        key=source.parent.name.split('_')[0]
        if key=='F41B07':  # The old pit preview contains civil geometry only.
            continue
        text=source.read_text(encoding='utf-8-sig').strip()
        original=json.loads(text.removeprefix('window.MODEL_PARTS=').removesuffix(';'))
        keep=[part for part in original if not part['name'].startswith(omitted)
              or part['name']=='支撑_换热器托耳']
        if len(keep)==len(original) and key!='D41B01':
            continue
        assert keep,key
        parts[:]=[(p['name'],p['color'],p['vertices'],p['faces']) for p in keep]
        archive_ports(key)
        supplemented=len(parts)>len(keep)
        folder=OUT/'设备净模'/key
        export_model(folder,key,color_materials=True,smooth=True)
        preview=folder/'model_data.js'
        added=json.loads(preview.read_text(encoding='utf-8').strip()
                         .removeprefix('window.MODEL_PARTS=').removesuffix(';'))[len(keep):] if supplemented else []
        mesh=keep+added
        # Keep original display normals and positions on every retained part.
        preview.write_text('window.MODEL_PARTS='+json.dumps(mesh,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
        retained={id(p) for p in keep}
        removed=[p['name'] for p in original if id(p) not in retained]
        bounds=[round(max(axis)-min(axis),1) for axis in zip(*(v for p in mesh for v in p['vertices']))]
        record={'path':f'设备净模/{key}/','bounds':bounds,'removed':removed,
                'source':source.relative_to(PROJECT.parent).as_posix()}
        if supplemented:
            record['接口增补']={'图元句柄':ARCHIVE_PORT_HANDLES[key],'标高':'未明示的法兰高度按示意'}
        result[key]=record
        original_parameters=json.loads((source.parent/'参数.json').read_text(encoding='utf-8-sig'))
        (folder/'参数.json').write_text(json.dumps({
            '净模位号':key,'尺寸单位':'mm','设备净模':record,'原档案参数':original_parameters,
        },ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


def write_equipment_audit():
    ledger=LIBRARY/'示图建模_20260521'/'设备台账对照.json'
    rows=json.loads(ledger.read_text(encoding='utf-8'))['清单']
    outcomes={
        'C41B01':'保留人孔和六只接管，西侧和西南侧的两只小接管直接接在槽盖上。顶口伸出高度暂定。',
        'C41B02':'按用户确认回退至六处盖面接口及两处侧口的版本。',
        'C41B03':'四处盖面接口按内外径复核，东侧盖口依剖面作两级。侧身接口沿用。',
        'C41B04':'三组双机，每组中心距 2400 mm，托耳贴合 4.500 m 梁顶。补两处下口与四处侧口。',
        'D41B01':'槽顶区分人孔盖、接管及东侧共座双接管。四处侧口及托耳沿用，A 的支架待核。',
        'D41B02':'增补 11 处盖面接口。盖面结构线作为结构参考，法兰伸出高度暂定。',
        'F41B01':'七处盖面接口按俯视区分东侧人孔盖和六处接管。侧视局部缺线，未发现可辨认的侧法兰。',
        'F41B02':'六处盖面位置与俯视对应，西南大口按剖面加呼吸弯管。三处侧口沿用。',
        'F41B03':'四向安装托耳已补。托耳与支墩平面位置不完全吻合，过渡件和托耳标高待核。',
        'F41B04':'新版基础 DXF 背立面量测烟囱 Ø1000×15100 mm，筒底 23.300 m，筒顶约 38.400 m。台账高 17000 mm，旧侧视高 11000 mm。新增三柱钢塔架和 27.800 m 检修平台，与原圆基础组合。底法兰孔位待核。',
        'F41B07':'保留 1#、2# 两种集水坑。俯视内小矩形按泵位标识处理，A/B 对照待核。',
        'F41B08':'按俯视及台账采用 Ø1000 × 1000 mm 一体圆柱，已消除盖缘重面。圆形基础 Ø1100 × 200 mm 暂定。',
        'P41B10':'恢复蜗壳下方的两只原支脚与脚底板，电机传动底座随设备展示。整机就位标高待核。',
        'L41B01':'两处顶口法兰 Ø165、中心开口 Ø50。西偏北侧口及南侧出口沿用，基础 Ø1300 × 200 mm 暂定。',
        'L41B02':'按两视图复核北侧大口、西侧低位排口和南侧四个侧口。新版基础 DXF 新增 2400×2400 mm 四柱钢塔架，架顶 31.300 m，与塔体和原圆基础组合。26.300 m 层南侧限位杆与模型中下接口相交，限位杆现场放样及底法兰螺栓配合待核。',
        'L41B03':'东侧下口、北侧偏东上口、锥底排口及四向托耳已核对。设备穿过 2050 mm 平台开口并落在承托面上。',
        'L41B04':'俯视主管、变径与两处圆形附件已有表达，立面与设备支座未见，暂独立展示基础。',
        'L41B05':'六处顶口及 2400 mm 鞍座中心距与俯视一致，组合显示双墩与安装鞍座，预埋孔位待核。',
    }
    report=['# 水解设备 DXF 逐项核对', '',
            '按《水解设备模型示图》更新版、设备布置图、设备基础图和 2026.5.21 台账核对。平面位置及外廓可量处按图；未给出的法兰伸出高度、厚度及部分支架截面按示意。',
            '', '| 位号组 | 设备 | 可用设备视图 | 核对结果 |', '|---|---|---|---|']
    for row in rows:
        tag=row['位号'][:6]
        views='、'.join(row['视图']) or '布置图量测'
        if tag in ('F41B05','F41B06'):
            outcome=outcomes['F41B02']+' 与钛液事故槽共用外形。'
        elif tag in ('P41B04','P41B07','P41B09'):
            outcome='布置图为管道泵或立泵安装符号。沿用已确认的卧式示意外形，接口实际标高待总图。基础略过。'
        elif row['名称'].endswith('泵'):
            measure=row['尺寸量测']
            x,y=measure['出口中心_xy_mm']
            outcome=f'对照俯视的轴向进液与偏置上出液。泵局部出口中心 X/Y 为 {x:g}/{y:g} mm。基础略过。'
            if tag=='P41A08':
                outcome+=' 暂沿用 P41B08 外形，安装位置待核。'
        elif tag.startswith('V41B'):
            outcome='对照共用侧视 27CA 的小车、卷筒与吊钩。起升行程按各自台账，轨道略过。'
        else:
            outcome=outcomes[tag]
        report.append(f"| {row['位号']} | {row['名称']} | {views} | {outcome} |")
    (OUT/'DXF逐项核对.md').write_text('\n'.join(report)+'\n',encoding='utf-8')


def build():
    sources={}
    for path in (DXF,TOWER_DXF):
        raw=path.read_bytes()
        lines=raw.splitlines()
        handles={value.strip().decode('ascii') for code,value in zip(lines[::2],lines[1::2])
                 if code.strip()==b'5' and re.fullmatch(rb'[0-9A-F]+',value.strip())}
        sources[path]=(sha256(raw).hexdigest(),handles)
    index={'source':DXF.name,'sha256':sources[DXF][0],'supplemental_source':TOWER_DXF.name,
           'assets':{},'tags':{},'civilOnly':['F41B07']}
    for key,data in RECORDS.items():
        source_handles=data['handles'].split()
        path=data['source']
        source_hash,handles=sources[path]
        missing=set(source_handles)-handles
        if missing:
            raise ValueError(f'{key}: missing DXF handles {missing}')
        parts.clear()
        data['build']()
        folder=OUT/key
        export_model(folder,key,color_materials=True,smooth=True)
        obj=folder/f'{key}.obj'
        text=obj.read_text(encoding='utf-8')
        basis=data['basis'] or path.name
        obj.write_text(f'# Civil or support model. Source: {basis}. OBJ meters, Z-up.\n'+text.split('\n',1)[1],encoding='utf-8')
        record={k:data[k] for k in ('name','dimensions','note','mount','tags','kind','offsets','combined_label','fixture_prefix')}
        record['basis']=basis
        if data['companion']:
            record['companion']=data['companion']
            record['source']=path.name
            record['sha256']=source_hash
        above,below,blinding,label=LEVELS[key]
        structural_z=[z for name,_,vertices,_ in parts if '垫层' not in name and not name.startswith('地脚螺栓_')
                      for _,_,z in vertices]
        top,bottom=max(structural_z),min(structural_z)
        if abs(top-bottom-above-below)>0.001:
            raise ValueError(f'{key}: drawn height does not match datum heights')
        record['datum']={'z':top-above,'top':top,'bottom':bottom,'above':above,'below':below,
                         'blinding':blinding,'label':label}
        record.update({'view':f"图纸摘录/{data['crop']}.png" if data['crop'] else None,'handles':source_handles,
                       'bounds':[round(max(axis)-min(axis),3) for axis in zip(*(v for _,_,verts,_ in parts for v in verts))]})
        if key=='D41B01':
            record['related_views']=[f'screenshots/D41B01B-{label}.png' for label in ('俯视图','侧视图')]
            members=[('D41B01B','D41B01C'),('D41B01D','D41B01E')]
            positions={tag:json.loads((LIBRARY/'parameters'/f'{tag}.json').read_text(encoding='utf-8-sig'))['cad_position_mm']
                       for pair in members for tag in pair}
            for a,b in members:
                if positions[a][0]!=positions[b][0] or positions[b][1]-positions[a][1]!=2600:
                    raise ValueError(f'Pair {a}/{b} no longer matches the 2600 mm north–south layout')
            record['pairs']=members
            record['layout_centers_mm']=positions
            record['mirror_y_indices']=[0]
        elif key in ('F41B08','L41B01'):
            record['related_views']=[f'示图建模_20260521/视图/{key}_俯视.svg']
        if 'related_views' in record:
            record['related_view_sha256']={
                path:sha256((LIBRARY/path).read_bytes()).hexdigest() for path in record['related_views']}
        index['assets'][key]=record
        for tag in data['tags']:
            index['tags'].setdefault(tag,[]).append(key)
        (folder/'参数.json').write_text(json.dumps({
            '基础编号':key,'依据':basis,'SHA256':source_hash if source_handles else None,'单位':'mm',
            '基准':'独立模型坐标。圆台、泵座与支墩以顶面为 Z=0，钢框架及集水坑以楼面为 Z=0。组合预览偏移见 mount。',
            **record},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    index['equipment']=equipment_only()
    write_equipment_audit()
    (OUT/'基础索引.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'foundation_data.js').write_text('window.EQUIPMENT_FOUNDATIONS='+json.dumps(index,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    print(f"{len(index['assets'])} foundation models, {len(index['tags'])} equipment groups")


if __name__=='__main__':
    build()

