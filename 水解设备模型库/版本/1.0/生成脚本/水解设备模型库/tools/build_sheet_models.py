"""Reconcile the 2026-05-21 ledger and reference DXF, and build supported type models."""
from collections import Counter
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path
import re
import sys

from read_equipment_dxf import read_drawing
from read_legacy_ledger import read_xls

LIB = Path(__file__).resolve().parents[1]
SOURCE_TOOLS = LIB.parent / '水解桥架工程' / 'tools' / 'source'
sys.path.insert(0, str(SOURCE_TOOLS))
from build_tank_mixer import MIXER_HEIGHTS, add, box, cyl, export_model, hollow_frustum, mixer_at, parts, ring

OUT = LIB / '示图建模_20260521'
RAW = OUT / '原始资料'
XLS = RAW / '2.水解水洗设备一览表 2026.5.21.xls'
DXF = RAW / '水解设备模型示图_更新20261105.dxf'
LAYOUT = RAW / '3.水解工段设备布置图+2026.5.21.dxf'
FAN_REFERENCE = RAW / 'P41B10_用户外形参考.png'
FAN_PORT_REFERENCE = RAW / 'P41B10_用户进出口参考.png'
PUMP_REFERENCE = RAW / '五类卧式泵_用户外形参考.png'
PUMP_PLAN = RAW / '五类卧式泵_项目俯视摘图.png'
PUMP_OUTLINE = '视图/五类卧式泵_共用外形.svg'
PUMP_TAGS = {'P41B01', 'P41B02', 'P41B03', 'P41B04', 'P41B05', 'P41B06', 'P41B07', 'P41B09'}
BODY, STEEL, BASE = '#a5b9c3', '#b7c8d0', '#818b90'

# Model-space INSERT handles, or x/y crop for unblocked drawing objects.
VIEWS = {
    'C41B01': ('503', '2BFB'),
    'C41B02': ('4DB', '2C75'),
    'C41B03': ('8FA', '2BB3'),
    'C41B04': (('24C7', '24C8', '24C9', '24CA'), '2E2B'),
    'D41B01': ('144A', '2A41'),
    'D41B02': ('1688', '2AB1'),
    'F41B01': ('1D8C', '2ADD'),
    'F41B02': ('1C3A', '2B25'),
    'F41B04': ('2582', '2F41'),
    'L41B02': ((18100, 21250, 18490, 29100), '2E93'),
    'L41B03': ('25D9', '2F1D'),
    'P41B10': ('278C', '2E63'),
    'P41B01': (None, '35D1'),
    'P41B02': (None, '35DC'),
    'P41B03': (None, '359B'),
    'P41B05': (None, '359A'),
    'P41B06': (None, '3598'),
    'P41B08': (None, '365B'),
    'P41B11': (None, '358A'),
    'L41B01': (None, '352F'),
    'F41B03': (None, ('3625', '3623', '3626')),
    'F41B07': (None, '3564'),
    'F41B08': (None, '353F'),
    'L41B04': (None, '2F6D'),
    'L41B05': (None, (96500, 99500, -7500, -900)),
    'hoist': ('27CA', None),
    'pump': (None, ('3332', '3351')),
    'cool_body': ('242E', None),
    'cool_stand': ((70400, 73000, 1100, 5700), None),
}

REUSED = {
    'C41B02': 'C41B02_钛液预热槽',
    'D41B02': 'D41B02_水解槽',
}
SHARED = {'F41B05': 'F41B02', 'F41B06': 'F41B02', 'P41A08': 'P41B08'}
NOTES = {
    'C41B01': '台账 Ø3500×4000。槽盖含一处人孔、六处接管，西侧和西南侧的两只小接管直接接槽盖。伸出高度暂定。',
    'C41B02': '保留确认档案的 Ø5500×5000 槽体和 2185 mm 搅拌总高，设备库模型采用六处盖面接口及两处侧口的版本。',
    'C41B03': '台账 Ø1500×2000。四处顶口按俯视内外径及剖面相对高度修正，东侧盖口分两级。东侧大法兰、西侧斜口和南侧低位口沿用。',
    'C41B04': 'DXF 本体筒径约 1300 mm，高约 4980 mm。补下部和侧面法兰，双机托耳落在钢框架承梁。230 m² 为换热面积。',
    'D41B01': '台账 Ø1800×1600。槽顶按俯视和侧视修正人孔、接管及东侧共座的双接管。四处侧安装口和四向翼式托耳沿用。',
    'D41B02': '保留确认档案的 Ø5900×4700 槽体和 3076 mm 搅拌总高，按俯视补 11 处槽盖接口。',
    'F41B01': '台账 Ø5000×5900。顶面按俯视区分东侧人孔盖与六处接管，接管标高按图估取。',
    'F41B02': '三槽共用 DXF 和 Ø2800×2500 外形。西南大口按剖面表现为盖板加呼吸弯管，其余五处顶口按俯视定位。侧口沿用。',
    'F41B04': '新版基础 DXF 钢塔架背立面量测筒体 Ø1000×15100 mm，筒底 23.300 m、筒顶约 38.400 m。台账高 17000 mm，旧设备侧视高 11000 mm。新版平面圆外径约 Ø1100 mm，筒径按立面及台账。',
    'L41B02': '台账 Ø2200×10300。按俯视定位北侧大口、南侧接口组及西侧低位排口，法兰标高取侧视比例。',
    'L41B03': '本体采用台账 Ø1800×3100。调整东侧下口、北侧偏东上口，补锥底排口及四向承托耳，与钢架平台开口对中。',
    'P41B10': '台账 Q=40000 m³/h、ΔP=3000 Pa。正面轴向圆口进风，蜗壳侧上方切向出风。设备含电机下传动底座及蜗壳下原有支脚、脚底板。土建基础独立展示。',
    'L41B04': 'DXF 俯视 2F6D 的外廓 5250×639 mm，按轮廓建主管、变径段和两处圆形附件。侧视缺失，管心高、法兰厚度及附件立面为示意。',
    'L41B05': '台账和俯视均为 Ø1000×3800 mm 筒段。按 DXF 俯视定位六个法兰口和两处鞍座，管口暂按向上表达；封头曲面和管口立面高度为示意。',
    'L41B01': '台账 Ø1200×1220 mm。俯视 352F 两处顶盖法兰外径 Ø165、中心开口 Ø50。西侧偏北接口及南侧中心接口沿用，中心高暂取 880 mm。',
    'F41B03': '台账直筒段 Ø1000×1000 mm。按俯视 3625 补四块安装托耳。无侧视，托耳高度暂定，支墩连接待核。',
    'F41B07': '台账地坑净尺寸 1500×1500×2000 mm。新版俯视 3564 内框 1500 mm、外框 1700 mm。底厚暂按 100 mm，坑口为 Z=0，向下建模。',
    'F41B08': '按俯视 353F、台账和用户确认，槽体采用 Ø1000 × 1000 mm 的一体圆柱。',
}


def translate_last(dx, dy, dz=0):
    name, color, vertices, faces = parts[-1]
    parts[-1] = name, color, [(x+dx, y+dy, z+dz) for x, y, z in vertices], faces


def axial(name, start, end, radius, color=STEEL, end_radius=None, inner_radius=None):
    direction = [b-a for a, b in zip(start, end)]
    length = math.hypot(*direction)
    axis = [v/length for v in direction]
    horizontal = math.hypot(axis[0], axis[1])
    if horizontal < 1e-9:
        u = (1, 0, 0)
    else:
        u = (-axis[1]/horizontal, axis[0]/horizontal, 0)
    v = (axis[1]*u[2]-axis[2]*u[1], axis[2]*u[0]-axis[0]*u[2], axis[0]*u[1]-axis[1]*u[0])
    if inner_radius is None:
        cyl(name, 0, length, radius, color, 48, end_radius)
    else:
        ring(name, 0, length, radius, inner_radius, color, 48)
    name, color, vertices, faces = parts[-1]
    parts[-1] = name, color, [tuple(start[i]+u[i]*x+v[i]*y+axis[i]*z for i in range(3))
                             for x, y, z in vertices], faces


def vessel(diameter, height, bottom=0, lid=36, lid_radius=None):
    radius = diameter / 2
    hollow_frustum('本体_筒壳', bottom, bottom+height, radius, radius, 12, BODY)
    cyl('本体_平底', bottom, bottom+18, radius-12, BODY, 96)
    cyl('槽盖_盖板', bottom+height-lid, bottom+height, lid_radius or radius, STEEL, 96)


def flanged_port(name, start, end, neck_radius, flange_radius, thickness=20):
    direction=[b-a for a,b in zip(start,end)]
    length=math.hypot(*direction)
    shoulder=tuple(b-thickness*d/length for b,d in zip(end,direction))
    bore=neck_radius-8
    axial(f'接口_{name}接管',start,shoulder,neck_radius,inner_radius=bore)
    axial(f'接口_{name}法兰',shoulder,end,flange_radius,inner_radius=bore)


def radial_point(angle, radius, z):
    return (radius*math.cos(angle),radius*math.sin(angle),z)


def cover_flanges(z, locations, flange_color='#9aafb9'):
    """Locations are plan centres and measured outer/bore radii in mm."""
    first=1+sum(name.startswith('接口_顶盖法兰') for name,_,_,_ in parts)
    for i,(x,y,outer,bore,height) in enumerate(locations,first):
        neck=bore+min(12,(outer-bore)*.45)
        rim=min(24,height/3)
        ring(f'接口_顶盖接管{i:02}',z,z+height-rim,neck,bore,BODY,48)
        translate_last(x,y)
        ring(f'接口_顶盖法兰{i:02}',z+height-rim,z+height,outer,bore,flange_color,48)
        translate_last(x,y)


def roof_manhole(z,x,y,outer,cover,height):
    ring('接口_人孔座圈',z,z+height-16,outer,cover-18,BODY,64)
    translate_last(x,y)
    cyl('接口_人孔盖',z+height-16,z+height,cover,STEEL,64)
    translate_last(x,y)
    box('接口_人孔盖提手',(x,y,z+height+12),(cover*.52,24,24),BASE)


def roof_vent(z,x,y):
    # The side section shows a vent turning out from the large round cover.
    roof_manhole(z,x,y,312.5,250,175)
    dx,dy=(v/math.hypot(x,y) for v in (x,y))
    base=z+175
    axial('接口_呼吸弯管立段',(x,y,base),(x,y,base+160),49,inner_radius=40)
    radius=145
    rings=17
    sides=32
    vertices=[]
    for tube in (49,40):
        for i in range(rings):
            a=i*math.pi/(2*(rings-1))
            r=radius*(1-math.cos(a))
            height=base+160+radius*math.sin(a)
            for j in range(sides):
                b=j*math.tau/sides
                c,s=tube*math.cos(b),tube*math.sin(b)
                vertices.append((x+dx*r-dy*c-dx*s*math.cos(a),
                                 y+dy*r+dx*c-dy*s*math.cos(a),height+s*math.sin(a)))
    layer=rings*sides
    faces=[]
    for i in range(rings-1):
        for j in range(sides):
            a=i*sides+j
            b=i*sides+(j+1)%sides
            faces.extend(((a,b,b+sides,a+sides),(a+layer,a+sides+layer,b+sides+layer,b+layer)))
    for j in range(sides):
        k=(j+1)%sides
        faces.append((k,j,j+layer,k+layer))
        a,b=layer-sides+j,layer-sides+k
        faces.append((a,b,b+layer,a+layer))
    add('接口_呼吸弯管弧段',STEEL,vertices,faces)


ARCHIVE_PORT_HANDLES = {
    'C41B02':['2C02','2C08','2C44','2C53','2C55','2C5A','2C5B','2C5C','2C63','2C65'],
    'D41B02':['2A55','2A5B','2A5E','2A81','2A85','2A8D','2A8F','2A91','2A96','2AA3','2AA4'],
}

PORT_REVIEW_HANDLES = {
    'C41B01':['2BC5','2BC6','2BCC','2BCE','2BD0'],
    'C41B03':['2B91','2B97','2BA0','2BA2'],
    'C41B04':['2E03','2E08','2E06'],
    'F41B02':['2AF6','2B04','2B0A','2B0B','2B12','2B13','2AEE','2AEF'],
    'F41B03':['3629','362A','362B','3623','3626'],
    'L41B02':['2E68','2E6E','2E73','2E76'],
    'L41B03':['2EFE','2EF0','2EF3','2EF5','2EF6','2EF7','2ECB','2EE6','2EF9']
}

ROOF_REVIEW_HANDLES = {
    'C41B01':(['2BD1','2BDB','2BDC','2BE0','2BE5','2BE9','2BEA'],[]),
    'C41B03':(['2B77','2B78','2B8A','2B8C'],['861','877','895']),
    'C41B04':(['2E03','2E06','2E08'],[]),
    'D41B01':(['284D','2854','29A1','29A2','29A6','29B0','2A2A'],['CD5','FC5','13CE']),
    'F41B01':(['2AC1','2AC3','2AC5','2AC9','2ACC','2ACE','2AD0'],[]),
    'F41B02':(['2AEA','2AF4','2AF6','2B05','2B14','2B16'],[]),
    'L41B01':(['34F2','34F3','34F4','34F5'],[]),
}


def archive_ports(tag):
    if tag=='C41B02':
        cover_flanges(5055,[
            (1767.8,1767.8,185,113.3,125),(1996.6,-1504.5,80,32.5,95),
            (2150,0,245,175,140),(-261.3,-2486.3,125,85,100),
            (-261.3,-1786.3,187.5,140,120),(-2500,0,187.5,100,120)
        ],flange_color=STEEL)
        flanged_port('东侧',(2730,0,300),(3150,0,300),140.3,227)
        angle=math.radians(135)
        flanged_port('西北侧',radial_point(angle,2730,950),radial_point(angle,3150,950),140,227)
    elif tag=='D41B02':
        cover_flanges(5020,[
            (0,-2140,140,79.5,120),(-1639.3,-1375.6,195,125,150),
            (946.7,-2030.1,80,38,90),(-2240,0,80,38,90),
            (-1513.2,1513.2,97.5,44.5,100),(-904.4,1939.5,97.5,44.5,100),
            (0,2450,380,315,180),(946.7,2030.1,80,38,90),
            (1513.2,1513.2,175,136.5,140),(2350,0,187.5,79.5,140),(2350,400,132.5,54,115)
        ])


def bearing_lug(name, angle, radius, end, width, z, rise):
    """Build a vessel-mounted bearing pad and its two radial stiffeners."""
    dx,dy,_=radial_point(angle,1,0)
    cx,cy,_=radial_point(angle,(radius+end)/2,0)
    depth=end-radius
    cardinal_x=abs(dx)>.5
    box(f'托耳_{name}底板',(cx,cy,z+12),(depth,width,24) if cardinal_x else (width,depth,24),BASE)
    profile=((radius,z+24),(end,z+24),(end,z+50),(radius+45,z+rise),(radius,z+rise))
    for side in (-1,1):
        loop=[(dx*r-dy*w,dy*r+dx*w,h)
              for w in (side*width*.30-7,side*width*.30+7) for r,h in profile]
        n=len(profile)
        faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
        faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
        add(f'托耳_{name}筋板{side:+d}',BASE,loop,faces)


def seed_lugs():
    profile=((895,1200),(1166,1200),(1166,1230),(1016,1600),(895,1600))
    for index in range(4):
        angle=index*math.pi/2
        dx,dy,_=radial_point(angle,1,0)
        x,y,_=radial_point(angle,1021,0)
        size=(290,400,20) if index%2==0 else (400,290,20)
        box(f'托耳_翼式底板{index+1}',(x,y,1190),size,BASE)
        for side in (-1,1):
            loop=[(dx*r-dy*w,dy*r+dx*w,z)
                  for w in (side*117-8,side*117+8) for r,z in profile]
            n=len(profile)
            faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
            faces += [(i,i+n,(i+1)%n+n,(i+1)%n) for i in range(n)]
            add(f'托耳_翼式筋板{index+1}_{side:+d}',BASE,loop,faces)


def mixer(z, tag):
    labels = {'01': '驱动', '02': '驱动', '03': '双端对称中间轴', '06': '支架'}
    for name, color, verts, faces in mixer_at(z, z+MIXER_HEIGHTS[tag]):
        add(f'{labels[name[:2]]}_{name}', color, verts, faces)


def feet(radius, count, height):
    for i in range(count):
        a = i*math.tau/count
        box(f'支撑_支脚{i+1:02}', (radius*math.cos(a), radius*math.sin(a), -height/2),
            (155, 155, height), BASE)


def hot_water():
    vessel(3500, 4000, lid_radius=1850)
    cyl('支撑_基座', -200, 0, 1850, BASE, 96)
    cover_flanges(4000,[(-671.8,387.9,138.2,72.75,70),(-630.3,-1091.7,106.65,48.5,65),
        (630.3,1091.7,106.65,48.5,65),(1091.7,-630.3,96.95,38.8,65)])
    cover_flanges(4000,[(-1260.6,0,96.95,38.8,64),(-1091.7,-630.3,96.95,38.8,64)])
    roof_manhole(4000,0,775.8,290.9,242.4,90)
    for label,deg,radius,flange,z in (('东侧',0,77.1,135.8,350),('西侧',180,38.8,97,220),
                                      ('西北侧',150,55,105,760)):
        angle=math.radians(deg)
        flanged_port(label,radial_point(angle,1730,z),radial_point(angle,1842.4,z),radius,flange,17)


def alkali_preheater():
    vessel(1500, 2000, lid_radius=778)
    mixer(2000, 'C41B03')
    cover_flanges(2000,[(-514.2,296.9,121.05,75.35,152),(387.6,-387.6,91.35,36.55,145),
        (387.6,387.6,100.5,45.7,166),(548.1,0,100.5,45.7,166)])
    cover_flanges(2166,[(548.1,0,82.5,40,145)])
    flanged_port('东侧大口',(725,0,500),(847.7,0,500),242.1,283.2,26)
    flanged_port('西侧斜口',(-735,0,475),(-829.5,0,660),26,75.4,17.4)
    flanged_port('南侧低位',(0,-730,58),(0,-829.5,58),26,75.4,17.4)


def seed():
    vessel(1800, 1600, bottom=180, lid_radius=942)
    cyl('本体_浅锥底', 0, 180, 105, BODY, 96, 900)
    cyl('接口_底排短管', -165, 0, 78, STEEL, 48)
    seed_lugs()
    for name,deg,tip in (('南向',-90,1021),('东北',30,1021),('西北水平',150,1021)):
        angle=math.radians(deg)
        flanged_port(name,radial_point(angle,880,750),radial_point(angle,tip,750),79.5,132.5)
    angle=math.radians(135)
    flanged_port('西北斜向',radial_point(angle,875,505),radial_point(angle,1096,726),79.5,153)
    roof_manhole(1780,-550,0,263,213,112)
    cover_flanges(1780,[(-477.3,-477.3,132.5,50,125),(420,0,100,40,106),
        (424.3,424.3,110,50,126),(477.3,-477.3,105,62.5,110)])
    box('接口_双接管安装座',(700,0,1808),(300,500,56),BASE)
    cover_flanges(1836,[(700,90,82.5,25.5,163),(700,-90,82.5,25.5,163)])
    mixer(1780, 'D41B01')


def accident():
    vessel(2800, 2500, lid_radius=1500)
    cyl('支撑_环形底座', -155, 0, 1450, BASE, 96)
    mixer(2500, 'F41B02')
    cover_flanges(2500,[(-900,-53.6,141,100,160),(-473,765.7,116.65,75,160),
        (0,900,116.65,75,160),(473.2,766,75,48,105),(426.6,-792.5,40,25,60)])
    roof_vent(2500,-426.6,-792.5)
    flanged_port('东侧低位',(1380,-53.6,170),(1800,-53.6,170),75,140)
    for label,angle,radius,outer,end,z in [
        ('西南检修',math.radians(240),175,335,1750,610),
        ('东北侧',math.pi/4,100,142.5,1800,1080)
    ]:
        flanged_port(label,radial_point(angle,1380,z),radial_point(angle,end,z),radius,outer)


def buffer():
    vessel(5000, 5900, lid_radius=2600, lid=200)
    mixer(5900, 'F41B01')
    feet(2280, 12, 200)
    cover_flanges(5900,[(-1800,0,100,40,80),(-1272.8,1272.8,142.5,75,80),(-900,1558.8,142.5,75,80),
        (900,-1558.8,222.5,150,110),(900,1558.8,142.5,75,80),(1558.8,-900,245,175,115)])
    roof_manhole(5900,1800,0,300,250,100)


def cooler():
    z = 1806
    cyl('本体_石墨换热器筒', z+242, z+4579, 650, BODY, 96)
    cyl('本体_下封头', z+85, z+242, 490, BODY, 96, 650)
    cyl('本体_上封头', z+4579, z+4760, 650, BODY, 96, 515)
    for height in (145, 505, 4300, 4740):
        cyl('本体_连接环', z+height, z+height+70, 730, STEEL, 96)
    cover_flanges(z+4760,[(-240,-390,197.5,135,210),(240,-390,197.5,135,210),(0,.5,75,53,130)])
    for x in (-240,240):
        flanged_port('底部',(x,0,z+105),(x,0,z-35),115,180)
    for sign in (-1,1):
        for height in (z+235,z+4510):
            flanged_port('侧面',(sign*640,0,height),(sign*820,0,height),95,135)
    for x in (-987, 987):
        for y in (-770, 770):
            box('支撑_立柱', (x, y, 2180), (150, 150, 4360), BASE)
        box('支撑_顶部横梁', (x, 0, 4425), (150, 1690, 130), BASE)
    for y in (-770, 770):
        box('支撑_顶部横梁', (0, y, 4425), (2124, 150, 130), BASE)
    for i,angle in enumerate((0,math.pi),1):
        bearing_lug(f'换热器{i}',angle,645,1075,300,4500,350)


def chimney():
    hollow_frustum('本体_烟囱直筒', 0, 15100, 500, 500, 16, BODY)


def tower():
    cyl('本体_下封底', 0, 130, 1100, BODY, 96)
    hollow_frustum('本体_塔身', 130, 9440, 1100, 1100, 18, BODY)
    hollow_frustum('本体_塔顶收口', 9440, 10110, 1100, 481, 18, BODY)
    ring('接口_顶部法兰', 10110, 10300, 591, 481, STEEL, 96)
    for x, y in ((985, 0), (-985, 0), (0, 985), (0, -985)):
        box('支撑_底部托座', (x, y, 75), (260, 260, 150), BASE)
    for name,angle,tip,height,neck,flange in [
        ('西侧排口',math.pi,1443.8,375,68.8,126.4),
        ('北侧大口',math.pi/2,1375,2120,481.2,591.2),
        ('南侧下口',-math.pi/2,1375,1150,137.5,233.8),
        ('南侧中下',-math.pi/2,1345,3050,120,165),
        ('南侧中上',-math.pi/2,1345,5750,120,165),
        ('南侧上口',-math.pi/2,1250,8420,118,155)
    ]:
        flanged_port(name,radial_point(angle,1025,height),radial_point(angle,tip,height),neck,flange)


def demister():
    cyl('本体_下锥段', 790, 1540, 37, BODY, 96, 900)
    cyl('本体_直筒', 1540, 3440, 900, BODY, 96)
    cyl('本体_收口封头', 3440, 3810, 900, BODY, 96, 410)
    ring('接口_顶部法兰', 3810, 3890, 430, 340, STEEL, 96)
    flanged_port('东侧下口',(880,0,1950),(1062,0,1950),225,290,27)
    flanged_port('北侧偏东',(697.5,435,3030),(697.5,945,3030),185,243,30)
    flanged_port('锥底排口',(0,0,800),(0,0,690),34,76,20)
    for index,(angle,end) in enumerate(((0,1150),(math.pi/2,1120),(math.pi,1150),(-math.pi/2,1120)),1):
        bearing_lug(f'除雾器{index}',angle,890,end,310,2450,230)
    for x in (-1175, 1175):
        for y in (-1175, 1175):
            box('支撑_立柱', (x, y, 1120), (100, 100, 2240), BASE)
        box('支撑_框架横梁', (x, 0, 2240), (100, 2450, 100), BASE)
    for y in (-1175, 1175):
        box('支撑_框架横梁', (0, y, 2240), (2450, 100, 100), BASE)


def x_loft(name, color, loops, omit=()):
    """Join equal-length YZ contours at successive X stations."""
    count = len(loops[0][1])
    vertices = [(x, y, z) for x, section in loops for y, z in section]
    faces = []
    for level in range(len(loops)-1):
        a, b = level*count, (level+1)*count
        for i in range(count):
            if (level, i) not in omit:
                j = (i+1) % count
                faces.append((a+i, a+j, b+j, b+i))
    add(name, color, vertices, faces)


def fan_outlet(z, silver):
    """Open transition from the tangential rectangular throat to the circular flange."""
    y_mid = (245 + 974) / 2
    angles = sorted({i*math.tau/96 for i in range(96)} | {
        math.atan2(y*364.5, x*179) % math.tau for x in (-1, 1) for y in (-1, 1)})

    def rectangle(w, d):
        points = []
        for a in angles:
            x, y = math.cos(a), math.sin(a)
            radius = min(w/max(abs(x), 1e-12), d/max(abs(y), 1e-12))
            points.append((radius*x, y_mid+radius*y))
        return points

    def circle(r):
        return [(r*math.cos(a), y_mid+r*math.sin(a)) for a in angles]

    # Cyclic coordinate permutation reuses the same outward winding around +Z.
    outer = [(z, rectangle(179, 364.5)), (2493, circle(272)),
             (2505, circle(272)), (2505, circle(325)), (2530, circle(325))]
    inner = [(2530, circle(246)), (2493, circle(246)), (z, rectangle(160, 346.5))]
    x_loft('接口_上出风圆法兰及过渡管', silver, outer+inner+outer[:1])
    name, color, vertices, faces = parts[-1]
    parts[-1] = name, color, [(x, y, zz) for zz, x, y in vertices], faces
    for i in range(12):
        a = i*math.tau/12
        cyl(f'紧固件_出风法兰螺栓{i+1:02}', 2530, 2543, 11, silver, 6)
        translate_last(297*math.cos(a), y_mid+297*math.sin(a))


def fan():
    silver, steel, blue, yellow = '#b8c3cc', '#758896', '#205d7a', '#e8af27'
    axis_z = 1693
    box('支撑_整机底座', (880, 0, 50), (3000, 2040, 100), blue)
    box('传动底座_主座', (1190, 0, 654), (1814, 910, 1108), '#898784')
    box('传动底座_安装板', (1190, 0, 1263), (1814, 910, 110), blue)
    box('传动底座_电机抬高座', (1703, 0, 1375), (788, 550, 114), blue)

    # Viewed from the inlet, the tangential throat rises at the left of the scroll.
    outlet_z = 2410
    profile = [(245, outlet_z)]
    for i in range(97):
        a = math.radians(259+(540-259)*i/96)
        growth = i / 96
        ry = 735 + 239*growth + 130*math.sin(math.pi*growth)
        rz = 710 + 145*growth + 40*math.sin(math.pi*growth)
        profile.append((-ry*math.cos(a), axis_z-rz*math.sin(a)))
    profile[-1] = (974, axis_z)
    profile.append((974, outlet_z))
    inner = [(y*.982, axis_z+(z-axis_z)*.982) for y, z in profile]
    inner[0], inner[-1] = (263, outlet_z), (956, outlet_z)
    angles = [math.atan2(z-axis_z, y) for y, z in profile]

    def bore(radius):
        return [(radius*math.cos(a), axis_z+radius*math.sin(a)) for a in angles]

    # The final segment is the outlet opening. Keep it open through the sheet skin.
    opening = len(profile)-1
    x_loft('本体_蜗壳围板', steel, [(-179, profile), (179, profile),
                                   (179, inner), (-179, inner), (-179, profile)],
           omit={(level, opening) for level in range(4)})
    for side, x0, x1, radius in (('进风侧', -189, -169, 315), ('传动侧', 169, 189, 87)):
        opening_loop = bore(radius)
        x_loft(f'本体_{side}蜗壳板', silver, [(x1, profile), (x1, opening_loop),
                                              (x0, opening_loop), (x0, profile), (x1, profile)])
    fan_outlet(outlet_z, silver)
    for x in (-187, 187):
        bracket = [(-500, 130), (500, 130), (245, 955), (-245, 955)]
        x_loft('蜗壳支架_支脚', steel, [(x-37.5, bracket), (x+37.5, bracket)])
        name, color, vertices, faces = parts[-1]
        parts[-1] = (name, color, vertices, faces+[(3, 2, 1, 0), (4, 5, 6, 7)])
        box('蜗壳支架_脚底板', (x, 0, 115), (160, 1020, 30), silver)

    # Use uniformly sampled circles on the inlet so the bellmouth stays round.
    def circle(radius):
        return [(radius*math.cos(i*math.tau/96), axis_z+radius*math.sin(i*math.tau/96))
                for i in range(96)]

    stations = [(-620, 374), (-596, 374), (-421, 338), (-372, 345),
                (-343, 375), (-318, 375), (-318, 347), (-189, 347),
                (-189, 315), (-318, 297), (-421, 286), (-596, 318), (-620, 331)]
    x_loft('接口_中空喇叭口及进风法兰', silver,
           [(x, circle(r)) for x, r in stations + stations[:1]])
    for i in range(16):
        a = i*math.tau/16
        y, z = 353*math.cos(a), axis_z+353*math.sin(a)
        axial(f'紧固件_进风法兰螺栓{i+1:02}', (-358, y, z), (-343, y, z), 11, steel)

    axial('内部示意_叶轮背盘', (118, 0, axis_z), (146, 0, axis_z), 530, '#52616d')
    axial('内部示意_叶轮轴毂', (37, 0, axis_z), (174, 0, axis_z), 123, steel)
    for i in range(10):
        a = i*math.tau/10
        # Only the exposed silhouette is represented. Blade count and pitch are illustrative.
        blade = [(r*math.cos(a+t), axis_z+r*math.sin(a+t))
                 for r, t in ((210, 0), (514, .24), (515, .28), (210, .055))]
        x_loft(f'内部示意_叶片{i+1:02}', '#657783',
               [(65, blade), (119, blade)])

    axial('驱动_传动轴', (146, 0, axis_z), (1560, 0, axis_z), 71, steel)
    axial('驱动_轴承座壳体', (285, 0, axis_z), (1168, 0, axis_z), 197, blue)
    for x in (295, 1130):
        axial('驱动_轴承座端环', (x, 0, axis_z), (x+34, 0, axis_z), 209, steel)
    box('传动底座_轴承座底脚', (727, 0, 1405), (880, 510, 177), blue)
    axial('驱动_联轴器', (1170, 0, axis_z), (1540, 0, axis_z), 132, steel)
    hood = [(-202, 1432), (202, 1432)] + [
        (202*math.cos(i*math.pi/24), axis_z+202*math.sin(i*math.pi/24)) for i in range(25)]
    lining = [(-190, 1432), (190, 1432)] + [
        (190*math.cos(i*math.pi/24), axis_z+190*math.sin(i*math.pi/24)) for i in range(25)]
    x_loft('护罩_联轴器拱形罩', yellow, [(1182, hood), (1460, hood), (1460, lining),
                                         (1182, lining), (1182, hood)],
           omit={(level, 0) for level in range(4)})
    for x, x1, r0, r1 in ((1450, 1533, 156, 216), (1533, 2019, 218, 218),
                          (2019, 2110, 218, 195), (2110, 2128, 195, 168)):
        axial('驱动_电机外壳', (x, 0, axis_z), (x1, 0, axis_z), r0, blue, r1)
    for i in range(24):
        a = i*math.tau/24
        y, z = 217*math.cos(a), axis_z+217*math.sin(a)
        axial(f'驱动_电机散热筋{i+1:02}', (1575, y, z), (1990, y, z), 7, blue)
    box('传动底座_电机底脚', (1730, 0, 1455), (540, 495, 46), blue)
    box('驱动_电机接线盒', (1720, 263, 1760), (211, 185, 150), blue)


def filter_vessel():
    vessel(1200, 1220, lid_radius=630)
    ring('接口_上盖法兰圈', 1150, 1195, 630, 586, STEEL, 96)
    cover_flanges(1220,[(400,-200,82.5,25,58),(400,200,82.5,25,58)])
    flanged_port('西侧偏北',(-275,500,880),(-751.5,500,880),100,170)
    flanged_port('南侧出口',(0,-590,880),(0,-750,880),100,170)


def condensate_separator():
    hollow_frustum('本体_直筒段', 0, 1000, 500, 500, 12, BODY)
    for z in (0, 976):
        ring('本体_端缘', z, z+24, 552, 488, STEEL, 96)
    for i,(x,y,size) in enumerate(((540.25,0,(102,137.5,24)),(-540.25,0,(102,137.5,24)),
                                   (0,540.25,(137.5,102,24)),(0,-540.25,(137.5,102,24))),1):
        box(f'托耳_支墩安装板{i}',(x,y,12),size,BASE)


def wastewater_pit():
    box('土建_坑底', (0, 0, -2050), (1700, 1700, 100), BASE)
    for x in (-800, 800):
        box('土建_纵向坑壁', (x, 0, -1000), (100, 1700, 2000), BASE)
    for y in (-800, 800):
        box('土建_横向坑壁', (0, y, -1000), (1500, 100, 2000), BASE)


# Layout model-space roots matched by the adjacent equipment tags. For inline pumps
# and the sump pump the geometry here is a symbol, not a horizontal assembly outline.
PUMP_LAYOUT = {
    'P41B01': ('FB3D3',), 'P41B02': ('B5E5D',), 'P41B03': ('5D24E',),
    'P41B04': ('ACEDB', 'ACEDD', 'ACEDE', 'ACEDF', 'ACEE0', 'ACEE1', 'ACEE2'),
    'P41B05': ('5D245',), 'P41B06': ('3804E',), 'P41B07': ('3800B', 'DA4D8'),
    'P41B08': ('B5E59',),
    'P41B09': ('DE5A3', 'DE5A6', 'DE5A7', 'DE5A8', 'DE5A9', 'DE5AA', 'DE5AB'),
    'P41B11': ('113DEC',),
}
PUMP_LAYOUT_TAG = {
    'P41B01': 'P41B01A', 'P41B02': 'P41B02A1', 'P41B07': 'P41B07A/B',
    'P41B09': 'P41B09A（A/B同符号）',
}
PUMP_SYMBOLS = {'P41B04', 'P41B07', 'P41B09'}
ROTATED_PUMPS = {'P41B02', 'P41B08', 'P41B11'}
SUCTION_RADII = {'P41B01': 125, 'P41B02': 107.5, 'P41B08': 107.5, 'P41B11': 55}


def pump_layout_measurements():
    paths, _ = read_drawing(LAYOUT)
    by_root = {}
    for path in paths:
        if not any(layer in path.layer for layer in ('中心线', '点划线')):
            by_root.setdefault(path.parent, []).append(path)

    measurements = {}
    for tag, handles in PUMP_LAYOUT.items():
        geometry = [p for handle in handles for p in by_root[handle]]
        if tag == 'P41B07':
            # Extract the pump symbol inside the pit. Exclude the pit walls and slope.
            motor_symbol = {'1EDE9', '1EDEA', '1EDEB', '1EDEC', '1EDED', '1EDEE', '1EDEF', '1EDF0'}
            geometry = [p for p in geometry if p.handle in motor_symbol]
        primary = [p for p in geometry if p.parent == handles[0]] if tag == 'P41B07' else geometry

        def oriented(x, y):
            return (y, -x) if tag in ROTATED_PUMPS or tag in PUMP_SYMBOLS else (x, y)

        u, v = zip(*(oriented(x, y) for p in primary for x, y in p.points))
        measured_l, measured_w = max(u)-min(u), max(v)-min(v)
        length, width = measured_l, measured_w
        if tag == 'P41B07':
            length = round(2*width)
        x_out, y_out, r_out = .17*length, -.22*width, .16*width
        if tag not in PUMP_SYMBOLS:
            circles = []
            for p in primary:
                if len(p.points) < 25 or math.dist(p.points[0], p.points[-1]) > .01:
                    continue
                xx, yy = zip(*(oriented(x, y) for x, y in p.points))
                d = max(xx)-min(xx)
                if d > 1 and abs(d-(max(yy)-min(yy))) < .25:
                    circles.append((d/2, (min(xx)+max(xx))/2-min(u),
                                    (min(yy)+max(yy))/2-(min(v)+max(v))/2))
            if circles:
                r_out, x_out, y_out = max(circles)
        if tag in PUMP_TAGS:
            y_out = -abs(y_out)
        height = round(1.20*width)
        measurements[tag] = {
            '来源设备': PUMP_LAYOUT_TAG.get(tag, tag), '布置图': LAYOUT.name,
            '根句柄': list(handles), '轮廓图元句柄': sorted({p.handle for p in geometry}),
            '量测性质': '平面安装符号' if tag in PUMP_SYMBOLS else '俯视可见外轮廓（已排除中心线）',
            '布置图投影长宽_mm': [round(measured_l, 2), round(measured_w, 2)],
            '模型长宽高_mm': [round(length, 2), round(width, 2), height],
            '出口中心_xy_mm': [round(x_out, 2), round(y_out, 2)],
            '出口法兰外径_mm': round(2*r_out, 2),
            '进口法兰外径_mm': round(2*SUCTION_RADII.get(tag, .2115*width), 2),
        }
        filename = f'{tag}_布置图量测.svg'
        # A/B sump symbols have the same outline, so show one at readable scale.
        write_drawing(OUT / '视图' / filename, primary)
        measurements[tag]['布置图量测视图'] = f'视图/{filename}'
    return measurements


def horizontal_pump(measurement):
    length, width, top = measurement['模型长宽高_mm']
    out_x, out_y = measurement['出口中心_xy_mm']
    out_r, inlet_r = (measurement[key]/2 for key in ('出口法兰外径_mm', '进口法兰外径_mm'))
    head, adapter, motor = '#d8e7e5', '#3a847b', '#538f86'
    axis = .53*width
    head_radius = .48*width
    head_end = max(.32*length, out_x+.08*length)
    motor_start = max(head_end+.12*length, .49*length)
    flange_t = min(.031*length, .09*width)

    def circle(r):
        return [(r*math.cos(i*math.tau/64), axis+r*math.sin(i*math.tau/64)) for i in range(64)]

    # Continuous external head and open axial inlet profile.
    head_profile = [(0, inlet_r), (flange_t, inlet_r), (flange_t, .66*inlet_r),
                    (.075*length, .66*inlet_r), (.095*length, .72*head_radius),
                    (.15*length, .96*head_radius), (.22*length, head_radius),
                    (head_end, head_radius), (head_end, .30*inlet_r),
                    (.14*length, .30*inlet_r), (.07*length, .55*inlet_r), (0, .55*inlet_r)]
    x_loft('泵体_圆弧壳与轴向进液口', head,
           [(x, circle(r)) for x, r in head_profile+head_profile[:1]])
    for i in range(4):
        a = math.pi/4 + i*math.tau/4
        y, z = inlet_r*.82*math.cos(a), axis+inlet_r*.82*math.sin(a)
        axial(f'紧固件_进液口螺栓{i+1}', (0, y, z), (flange_t, y, z), .045*inlet_r, adapter)

    nozzle_z = axis + .67*math.sqrt(max(0, head_radius**2-out_y**2))
    flange_h = min(.06*width, 36)
    ring('接口_偏置竖向出液管', nozzle_z, top-flange_h, out_r*.66, out_r*.48, head)
    translate_last(out_x, out_y)
    ring('接口_朝上出液法兰', top-flange_h, top, out_r, out_r*.48, head)
    translate_last(out_x, out_y)

    axial('连接座_泵壳连接环', (head_end, 0, axis), (head_end+.036*length, 0, axis),
          head_radius, adapter)
    axial('连接座_短连接段', (head_end+.036*length, 0, axis), (motor_start, 0, axis),
          .33*width, adapter, .41*width)
    axial('电机_连接法兰', (motor_start, 0, axis), (motor_start+.043*length, 0, axis),
          .455*width, motor)
    motor_body_start = motor_start+.043*length
    motor_body_end = .946*length
    motor_r = .392*width
    axial('电机_带筋机壳', (motor_body_start, 0, axis), (motor_body_end, 0, axis), motor_r, motor)
    axial('电机_圆弧尾罩', (motor_body_end, 0, axis), (length, 0, axis), motor_r, motor, .32*width)
    for i in range(18):
        a = i*math.tau/18
        y, z = motor_r*math.cos(a), axis+motor_r*math.sin(a)
        axial(f'电机_散热筋{i+1:02}', (motor_body_start, y, z), (.91*length, y, z),
              .014*width, adapter)
    box('电机_接线盒', (.79*length, .405*width, axis), (.14*length, .19*width, .28*width), motor)
    for x in (.64*length, .87*length):
        box('支脚_电机底脚', (x, 0, .073*width), (.11*length, width, .146*width), adapter)


def horizontal_ring(name, y0, y1, axis_z, outer, inner, color=STEEL):
    ring(name, 0, y1-y0, outer, inner, color, 64)
    part, material, verts, faces = parts[-1]
    parts[-1] = part, material, [(x, y0+z, axis_z-y) for x,y,z in verts], faces


def desuperheater():
    # Plan coordinates relative to the lower end of the DXF outline.
    axis = 365
    axial('主管_直管段', (0, 55, axis), (0, 3701.9, axis), 319.5, BODY)
    axial('主管_变径段', (0, 3701.9, axis), (0, 4226.9, axis), 319.5, BODY, 204.7)
    axial('主管_短接管', (0, 4301.9, axis), (0, 5175, axis), 248, BODY)
    horizontal_ring('法兰_首端法兰', 0, 55, axis, 319.5, 270)
    horizontal_ring('法兰_变径连接法兰', 4226.9, 4301.9, axis, 292.5, 200)
    horizontal_ring('法兰_末端法兰', 5175, 5250, axis, 292.5, 200)
    for name, y, radius, top in (('调节阀示意', 750, 251.2, 1080),
                                 ('短接管附件', 4738.45, 104.8, 810)):
        cyl(f'附件_{name}接颈', 565, top-40, radius*.64, STEEL, 48)
        translate_last(0, y)
        ring(f'附件_{name}法兰', top-40, top, radius, radius*.58, STEEL, 64)
        translate_last(0, y)
    cyl('附件_小接管', 660, 765, 37.5, STEEL, 32)
    translate_last(0, 3251.9)


def steam_header():
    # The two saddle stations and six nozzle stations are measured along the plan.
    axis, half_length = 630, 1900
    def head(depth):
        stations = []
        for i in range(1, 9):
            t = math.pi*i/16
            stations.append((half_length+depth*math.sin(t), max(3,500*math.cos(t))))
        return stations

    stations = [(-y,r) for y,r in reversed(head(330))]
    stations += [(-half_length,500),(half_length,500)] + head(80)
    sides = 64
    loops = [(y, [(r*math.cos(i*math.tau/sides), r*math.sin(i*math.tau/sides))
                 for i in range(sides)]) for y,r in stations]
    x_loft('筒体_直段与封头', BODY, loops)
    name, color, verts, faces = parts[-1]
    caps = [tuple(reversed(range(sides))), tuple(range(len(verts)-sides,len(verts)))]
    parts[-1] = name, color, [(x,y,axis-z) for y,x,z in verts], faces+caps

    for i, (station, outer, bore) in enumerate(((3400,290,200),(300,260,175),
                 (2850,170,100),(800,170,100),(2500,57.5,12.5),(2200,57.5,12.5)), 1):
        y = station-half_length
        flange_bottom = 1240 if outer > 100 else 1195
        wall = min(15, .28*(outer-bore))
        ring(f'接口_接管{i:02}', 1102, flange_bottom, bore+wall, bore, STEEL, 48)
        translate_last(0,y)
        ring(f'接口_法兰{i:02}', flange_bottom, flange_bottom+30, outer, bore, STEEL, 64)
        translate_last(0,y)

    for i, y in enumerate((-1200,1200), 1):
        box(f'鞍座_底板{i}', (0,y,22), (1200,200,44), BASE)
        # A stepped cradle follows the lower arc without filling the vessel silhouette.
        for j in range(-5,6):
            x = 78*j
            contact = axis-math.sqrt(500**2-x*x)
            box(f'鞍座_托体{i}_{j+6:02}', (x,y,(contact+44)/2),
                (78,200,contact-44), BASE)


HOIST_VARIANTS = {
    'V41B01': (1, 6, .90),
    'V41B02': (2, 12, 1.00),
    'V41B03': (2, 24, 1.00),
    'V41B04': (5, 24, 1.20),
}


def electric_hoist(scale):
    # Side outline 27CA. X follows the drum, Z is measured from the depicted hook bottom.
    start = len(parts)
    motor, frame = '#527f83', '#78919c'
    axial('葫芦_卷筒外壳', (-625,0,1097), (770,0,1097), 150, BODY)
    axial('葫芦_电机端罩', (-754,0,1097), (-625,0,1097), 112, motor, 150)
    axial('葫芦_减速端盖', (770,0,1097), (969,0,1097), 150, frame, 122)
    for x in (-328,634):
        axial('葫芦_外壳环箍', (x,0,1097), (x+60,0,1097), 180, STEEL)

    box('小车_悬挂座', (183,0,1307), (833,330,120), frame)
    for x in (-278,25):
        box('小车_侧板连接座', (x,0,1460), (110,360,186), frame)
        for y in (-175,175):
            axial('小车_行走轮', (x,y-30,1617), (x,y+30,1617), 150, '#475b64')
    box('小车_传动托座', (415,0,1460), (100,150,186), frame)
    axial('小车_行走传动', (415,-117,1620), (415,117,1620), 118, motor)

    hook_x = -100
    cyl('吊具_示意钢丝绳', 222, 947, 8, STEEL, 12)
    translate_last(hook_x,0)
    verts, faces = [], []
    sections, sides = 36, 10
    for i in range(sections+1):
        angle = math.pi/2+(math.tau-math.pi/2)*i/sections
        for j in range(sides):
            t = j*math.tau/sides
            tube = 17-8*(i/sections)**4
            radius = 99+tube*math.cos(t)
            verts.append((hook_x+radius*math.cos(angle), tube*math.sin(t),
                          116+radius*math.sin(angle)))
    for i in range(sections):
        for j in range(sides):
            k = (j+1)%sides
            faces.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
    faces.extend((tuple(reversed(range(sides))), tuple(range(sections*sides,(sections+1)*sides))))
    add('吊具_吊钩', '#526976', verts, faces)
    for i in range(start,len(parts)):
        name, color, points, polygons = parts[i]
        parts[i] = name, color, [(x*scale,y*scale,z*scale) for x,y,z in points], polygons


def hoist_note(tag):
    load, lift, scale = HOIST_VARIANTS[tag]
    return (f'台账额定起重量 {load} t、起升高度 {lift} m。按共用侧视 27CA 建卷筒、电机、行走小车和吊钩。'
            f'以 2 t 方案为示意基准，整体倍率 {scale:g}；俯视宽度、悬绳和吊钩位置为示意。'
            '起升高度是行程参数，模型表现的是侧视图所示的短悬绳状态。')


BUILDERS = {
    'C41B01': hot_water, 'C41B03': alkali_preheater, 'C41B04': cooler,
    'D41B01': seed, 'F41B01': buffer, 'F41B02': accident, 'F41B04': chimney,
    'L41B02': tower, 'L41B03': demister, 'P41B10': fan,
    'L41B01': filter_vessel, 'F41B03': condensate_separator,
    'F41B07': wastewater_pit, 'F41B08': lambda: cyl('本体_直筒段', 0, 1000, 500, BODY, 96),
    'L41B04': desuperheater, 'L41B05': steam_header,
}


def view_paths(paths, selector):
    if selector is None:
        return []
    if isinstance(selector, str):
        return [p for p in paths if p.parent == selector]
    if isinstance(selector[0], str):
        return [p for p in paths if p.parent in selector]
    x0, x1, y0, y1 = selector
    return [p for p in paths if all(x0 <= x <= x1 and y0 <= y <= y1 for x, y in p.points)]


def write_drawing(path, geometry):
    x, y = zip(*(point for item in geometry for point in item.points))
    span = max(max(x)-min(x), max(y)-min(y))
    pad = span*.04
    width, height = max(x)-min(x)+2*pad, max(y)-min(y)+2*pad
    with path.open('w', encoding='utf-8') as file:
        file.write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{min(x)-pad} {-max(y)-pad} {width} {height}">\n')
        file.write(f'<rect x="{min(x)-pad}" y="{-max(y)-pad}" width="{width}" height="{height}" fill="#17222c"/>\n')
        file.write(f'<g fill="none" stroke="#d5e2eb" stroke-width="{span/670:.3f}">\n')
        for item in geometry:
            points = ' '.join(f'{x:.2f},{-y:.2f}' for x, y in item.points)
            file.write(f'<polyline points="{points}"/>\n')
        file.write('</g></svg>\n')


def text_cell(cells, row, col):
    value = cells.get((row, col), '')
    return value.strip() if isinstance(value, str) else f'{value:g}'


def ledger_rows(cells):
    items = []
    for row in range(6, max(r for r, _ in cells) + 1):
        if not re.match(r'^[A-Z]\d{2}[A-Z]\d{2}', text_cell(cells, row, 1)):
            if items and any(text_cell(cells, row, col) for col in (2, 3, 6)):
                items[-1]['附件规格'].append({key: text_cell(cells, row, col)
                                             for key, col in (('名称', 2), ('规格', 3), ('型号', 6))})
            continue
        item = {key: text_cell(cells, row, col) for key, col in (
            ('位号', 1), ('名称', 2), ('台账规格', 3), ('图号或型号', 6),
            ('单位', 7), ('数量', 8), ('材料', 9), ('备注', 17))}
        item.update({'台账行': row + 1, '附件规格': []})
        items.append(item)
    return items


def main():
    paths, _ = read_drawing(DXF)
    drawings = {}
    drawing_dir = OUT / '视图'
    drawing_dir.mkdir(exist_ok=True)
    for tag, selectors in VIEWS.items():
        drawings[tag] = {}
        for name, selector in zip(('侧视', '俯视'), selectors):
            geometry = view_paths(paths, selector)
            if geometry:
                filename = f'{tag}_{name}.svg'
                write_drawing(drawing_dir / filename, geometry)
                drawings[tag][name] = {
                    '文件': f'视图/{filename}',
                    '模型空间根句柄': sorted({p.parent for p in geometry}),
                    '图元句柄': sorted({p.handle for p in geometry}),
                }

    pump_measurements = pump_layout_measurements()
    ledger = read_xls(XLS)
    modifications = ledger.get('设备图修改', {})
    rows = ledger_rows(ledger['水解'])
    models = {}
    for item in rows:
        tag = item['位号'][:6]
        model = SHARED.get(tag, tag)
        reference = 'hoist' if tag.startswith('V41B') else model
        item['视图'] = drawings.get(reference, {})
        measured = pump_measurements.get(model)
        hoist = HOIST_VARIANTS.get(tag)
        note = hoist_note(tag) if hoist else NOTES.get(model)
        if tag in MIXER_HEIGHTS:
            note += ' 槽顶采用标注侧视搅拌器 v0.3，含开窗支架和双端对称中间轴。'
        if measured:
            a, b = measured['布置图投影长宽_mm']
            length, width, height = measured['模型长宽高_mm']
            x, y = measured['出口中心_xy_mm']
            note = (
                f'布置图{measured["量测性质"]} {a:g} × {b:g} mm；'
                f'卧式模型外形 {length:g} × {width:g} × {height:g} mm（长×宽×高，高度按比例估取）。'
                f'泵端轴向进液，俯视出口在轴线{"下" if y < 0 else "上"}侧，偏置 {abs(y):g} mm。'
            )
            if model in PUMP_SYMBOLS:
                note += ' 台账为管道泵或立式泵，按用户指定用共用卧式外形表达；该投影只用于定示意尺度，整机外形及接口待厂家总图核对。'
                if model == 'P41B07':
                    note += ' 暂定卧式长度取安装符号宽度的约两倍。'
            elif model not in PUMP_TAGS:
                note += ' 新版示图的俯视轮廓与共用泵相近，外部构造暂按同类表达。'
            if model in {'P41B03', 'P41B05', 'P41B06'}:
                note += ' 三组在布置图中复用了同尺寸块，实际设备尺寸可能有差异。'
            item['尺寸量测'] = measured
        if model in BUILDERS or measured or hoist:
            item['状态'] = '本批初模'
            item['模型入口'] = f'viewer.html?model={model}'
            if model not in models:
                parts.clear()
                if measured:
                    horizontal_pump(measured)
                elif hoist:
                    electric_hoist(hoist[2])
                else:
                    BUILDERS[model]()
                export_model(OUT / '模型' / model, model, color_materials=True, smooth=True)
                axes = list(zip(*(v for _, _, vertices, _ in parts for v in vertices)))
                models[model] = {'name': item['名称'], 'note': note,
                                 'spec': item['台账规格'], 'views': item['视图'],
                                 'bounds': [round(max(axis)-min(axis), 1) for axis in axes]}
                params = {
                    '位号组': model, '名称': item['名称'], '单位': 'mm',
                    '模型包围盒最小点': [round(min(axis), 3) for axis in axes],
                    '模型包围盒最大点': [round(max(axis), 3) for axis in axes],
                    '台账规格': item['台账规格'], '台账行': item['台账行'],
                    '依据': note, '坐标': 'X东、Y北、Z上；OBJ米制Z向上，GLB米制Y向上',
                    'DXF源视图': item['视图'],
                    '展示样式': 'C41B02 正交样本。中性冷灰、平滑曲面法线，保留设备识别色。',
                }
                if hoist:
                    params['起升参数'] = {'额定起重量_t': hoist[0], '起升高度_m': hoist[1], '示意外形比例': hoist[2]}
                elif model == 'L41B04':
                    params['俯视量测'] = {'外廓长宽_mm': [5250, 639], '主管直段_mm': 3701.9, '变径段长_mm': 525}
                elif model == 'L41B05':
                    params['筒体台账尺寸'] = {'外径_mm': 1000, '直段长_mm': 3800}
                    params['俯视量测'] = {'鞍座中心距_mm': 2400, '管口数量': 6}
                elif model == 'D41B01':
                    params['安装口及托耳'] = {
                        '侧口方位': ['南向','东北30°','西北150°水平','西北135°上斜'],
                        '翼式托耳': {'数量':4,'底板宽_mm':400,'承托面Z_mm':1180},
                        '平面图元句柄':['29B6','29BA','29D0','29D9','29E8','29F6','29FD','2A02'],
                        '侧视图元句柄':['CB7','CBB','CC1','1147','117F','1193'],
                        '高度口径':'斜口取侧视比例，东北及西北水平口暂按与南向口同高'}
                elif model == 'L41B01':
                    params['侧接口'] = {
                        '俯视根句柄':'352F','西侧偏北端面_xy_mm':[-751.5,500],'南侧端面_xy_mm':[0,-750],
                        '图元句柄':['34E9','34EC','34ED','34EE','34EF','34FA','34FB','34FC','34FD'],
                        '接口中心高_mm':880,'高度口径':'仅据俯视定位，标高暂取'}
                if model in MIXER_HEIGHTS:
                    params['搅拌总成'] = {'源模型': '槽罐搅拌器_标注侧视 v0.3',
                                        '安装面至电机顶_mm': MIXER_HEIGHTS[model],
                                        '分件': ['01', '02', '03', '06']}
                if model in PORT_REVIEW_HANDLES:
                    params['接口复核']={'关键俯视图元句柄':PORT_REVIEW_HANDLES[model],
                                        '尺寸口径':'平面可量轮廓取 DXF；未标注的接口标高与法兰厚度为示意'}
                if model in ROOF_REVIEW_HANDLES:
                    plan_handles,side_handles=ROOF_REVIEW_HANDLES[model]
                    params['顶盖接口复核']={'俯视图元句柄':plan_handles,'侧视图元句柄':side_handles,
                                         '尺寸口径':'按俯视内外轮廓定位；可见阶梯和弯管按侧视复核，未标注的高度和厚度暂取'}
                if measured:
                    params['尺寸量测'] = measured
                    params['模型坐标基准'] = 'X 从进液端指向电机，Y 正向为俯视上侧，Z 向上；放置时按图纸朝向旋转'
                    params['外形依据'] = [PUMP_OUTLINE, f'原始资料/{PUMP_REFERENCE.name}']
                    models[model]['layout'] = measured['布置图量测视图']
                    models[model]['reference'] = PUMP_OUTLINE
                if model == 'P41B10' and FAN_REFERENCE.is_file():
                    reference_url = f'原始资料/{FAN_REFERENCE.name}'
                    models[model]['reference'] = reference_url
                    params['外形参考图'] = {'文件': reference_url, '用途': '构造与配色类比', 'SHA256': sha256(FAN_REFERENCE.read_bytes()).hexdigest()}
                    params['版本'] = '1.1'
                if model == 'P41B10' and FAN_PORT_REFERENCE.is_file():
                    reference_url = f'原始资料/{FAN_PORT_REFERENCE.name}'
                    models[model]['portsReference'] = reference_url
                    params['进出口参考图'] = {
                        '文件': reference_url, '用途': '确认正面轴向进风、侧上方切向出风及出风法兰朝向',
                        'SHA256': sha256(FAN_PORT_REFERENCE.read_bytes()).hexdigest(),
                    }
                    params['基础'] = '独立分件，按 DXF 中传动组件下方的方形轮廓表示'
                    params['版本'] = '1.2'
                (OUT / '模型' / model / '参数.json').write_text(
                    json.dumps(params, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        elif model in REUSED:
            item['状态'] = '复用确认模型'
            item['模型入口'] = f'../设备档案/{REUSED[model]}/3d.html'
        else:
            item['状态'] = '待补资料'
            item['模型入口'] = ''
        item['建模口径或缺项'] = note or {
            'hoist': '共用葫芦侧视示图，缺俯视及四种规格的外形尺寸；起升高度另列。',
        }.get(reference, '示图未找到对应两视图，待设备外形图或可核对的尺寸。')
        if tag in SHARED:
            item['建模口径或缺项'] += f' 此位号沿用 {model} 共用外形。'
        if tag == 'P41A08':
            item['建模口径或缺项'] += ' 台账型号相同，量测源为 P41B08，P41A08 的安装位置待确认。'
        if measured and (OUT / PUMP_OUTLINE).is_file():
            item['外形示意'] = PUMP_OUTLINE

    originals = [path for path in (XLS, DXF, LAYOUT, RAW / '水解设备模型示图.dxf',
                                   FAN_REFERENCE, FAN_PORT_REFERENCE, PUMP_REFERENCE, PUMP_PLAN)
                 if path.is_file()]
    data = {'版本': '1.6', '台账': XLS.name, '图纸': DXF.name, '布置图': LAYOUT.name, '工作表': '水解',
            '原件SHA256': {path.name: sha256(path.read_bytes()).hexdigest() for path in originals},
            '清单': rows,
            '设备图修改表水解段': [
                {'台账行': r+1, '原表位号': text_cell(modifications, r, 1),
                 '名称': text_cell(modifications, r, 2), '改造说明': text_cell(modifications, r, 5),
                 '传动参数': text_cell(modifications, r, 6)} for r in range(1, 9)],
            '补充视图': {key: drawings[key] for key in ('cool_body', 'cool_stand', 'pump', 'hoist')}}
    (OUT / '设备台账对照.json').write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    (OUT / 'ledger_data.js').write_text(
        'window.EQUIPMENT_LEDGER = '+json.dumps(data, ensure_ascii=False, separators=(',', ':'))+';\n',
        encoding='utf-8')
    (OUT / 'models.js').write_text('window.BATCH_MODELS = '+json.dumps(models, ensure_ascii=False)+';\n', encoding='utf-8')
    write_catalog(rows, drawings)
    print(f'{len(rows)} equipment groups, {sum(int(r["数量"]) for r in rows)} ledger units; '
          f'{len(models)} new type meshes; {dict(Counter(r["状态"] for r in rows))}')


def link(url, label):
    return f'<a href="{escape(url, quote=True)}">{escape(label)}</a>'


def write_catalog(rows, drawings):
    entries = []
    for row in rows:
        view_links = [link(v['文件'], k) for k, v in row['视图'].items()]
        if row.get('外形示意'):
            view_links.append(link(row['外形示意'], '共用外形示意'))
        if row.get('尺寸量测'):
            view_links.append(link(row['尺寸量测']['布置图量测视图'], '布置量测'))
        views = ' · '.join(view_links) or '—'
        model = link(row['模型入口'], '打开 3D') if row['模型入口'] else '—'
        cells = [str(row['台账行']), escape(row['位号']), escape(row['名称']),
                 escape(row['数量']+row['单位']), escape(row['台账规格']),
                 escape(row['图号或型号']), views, escape(row['状态']), model,
                 escape(row['建模口径或缺项'])]
        entries.append(f'<tr data-status="{row["状态"]}">' + ''.join(f'<td>{c}</td>' for c in cells)+'</tr>')
    cool_views = ' · '.join(link(drawings[k]['侧视']['文件'], name) for k, name in
                            [('cool_body', '冷却器本体侧视'), ('cool_stand', '冷却器支架侧视')])
    header = ''.join(f'<th>{s}</th>' for s in
                     ('台账行','位号组','设备','数量','台账规格','图号或型号','DXF 视图','状态','模型','建模依据 / 待补'))
    html = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>水解设备 · 2026.5.21 台账和示图</title>
<style>
body{{background:#111c26;color:#e2edf4;font:14px "Microsoft YaHei",sans-serif;margin:24px}}
a{{color:#8ce5ec}}p{{line-height:1.75}}section{{overflow:auto;border:1px solid #364d60}}
table{{border-collapse:collapse;width:100%;min-width:1020px}}th,td{{padding:9px 10px;text-align:left;vertical-align:top;border-bottom:1px solid #364d60}}
th{{background:#233a4c;position:sticky;top:0}}td:nth-child(-n+4),td:nth-child(7),td:nth-child(8),td:nth-child(9){{white-space:nowrap}}
tr:nth-child(even){{background:#192a38}}input,select{{font:inherit;padding:8px;margin:0 8px 12px 0}}
</style>
<h1>水解设备台账与示图建模</h1>
<p>范围为 2026.5.21 设备一览表「水解」页。上方为侧视，下方为俯视；每行按台账位号组记录。<br>
{link('设备台账对照.json','带来源句柄与附件规格的清单')} · {cool_views}<br>
{link('原始资料/'+XLS.name,'原始设备台账')} · {link('原始资料/'+DXF.name,'新版 DXF 示图')} · {link('原始资料/'+LAYOUT.name,'设备布置 DXF')}</p>
<input id="query" placeholder="搜索位号、名称或规格" aria-label="搜索">
<select id="filter" aria-label="筛选建模状态"><option value="">全部状态</option><option>本批初模</option><option>复用确认模型</option><option>待补资料</option></select>
<section><table><thead><tr>{header}</tr></thead><tbody>{''.join(entries)}</tbody></table></section>
<script>
const query=document.getElementById('query'),filter=document.getElementById('filter');
function refresh() {{
  const keyword=query.value.trim().toLowerCase();
  for(const row of document.querySelectorAll('tbody tr')) {{
    row.hidden=(filter.value && filter.value!==row.dataset.status) || !row.textContent.toLowerCase().includes(keyword);
  }}
}}
query.addEventListener('input',refresh);filter.addEventListener('change',refresh);
</script></html>'''
    (OUT / 'index.html').write_text(html, encoding='utf-8')


if __name__ == '__main__':
    main()
