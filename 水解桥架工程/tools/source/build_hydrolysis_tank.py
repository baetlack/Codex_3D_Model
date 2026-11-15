"""Build the D41B02 type model using the supplied side elevation."""
import json
import math
from pathlib import Path
import shutil

from build_tank_mixer import MIXER_HEIGHTS, box, cyl, export_model, hollow_frustum, mixer_at, parts


LIBRARY = Path(__file__).resolve().parents[3] / '水解设备模型库'
STEM = 'D41B02_水解槽'
OUT = LIBRARY / '设备档案' / STEM
PREHEATER = OUT.parent / 'C41B02_钛液预热槽'
DIAMETER, BODY_HEIGHT, MIXER_HEIGHT = 5900, 4700, MIXER_HEIGHTS['D41B02']
MOTOR_TOP = BODY_HEIGHT + MIXER_HEIGHT
MOUNT_Z = 5020
PIERS = ((-2640, 790), (-1500, 290), (-710, 290), (80, 290),
         (870, 290), (1660, 290), (2640, 790))


def build():
    parts.clear()
    radius = DIAMETER / 2
    hollow_frustum('Tank_shell', 0, BODY_HEIGHT, radius, radius, 18, '#a5b9c3')
    cyl('Tank_flat_bottom', 0, 24, radius - 18, '#a5b9c3', 96)
    cyl('Tank_cover_lid', BODY_HEIGHT, MOUNT_Z, 3035, '#b7c8d0', 96)
    assembly = mixer_at(MOUNT_Z, MOTOR_TOP)
    parts.extend(assembly)

    for i in range(12):
        angle = (i + 0.5) * math.tau / 12
        x, y = 2730 * math.cos(angle), 2730 * math.sin(angle)
        for j, (z, w, h) in enumerate(((-15, 190, 30), (-100, 76, 140), (-185, 190, 30)), 1):
            box(f'Leg_{i + 1:02}_{j}', (x, y, z), (w, w, h), '#a6b6bf')
    box('Pad_foundation_cap', (0, 0, -295), (6070, 6070, 190), '#8d827b')
    for i, (x, width) in enumerate(PIERS, 1):
        box(f'Pad_foundation_strip_{i:02}', (x, 0, -1040), (width, 6070, 1300), '#8d827b')

    export_model(OUT, STEM, color_materials=True, smooth=True)
    write_elevation(assembly)
    write_viewer()
    params = {
        '位号组': 'D41B02',
        '名称': '水解槽',
        '版本': '1.1',
        '外径_mm': DIAMETER,
        '槽体高度_mm': BODY_HEIGHT,
        '搅拌总高_mm': MIXER_HEIGHT,
        '搅拌高度基准': '主槽体顶缘 Z=4700 至电机顶，包含槽顶以上各构件高度',
        '槽底至电机顶_mm': MOTOR_TOP,
        '搅拌总成': {'源模型': '槽罐搅拌器_标注侧视 v0.3', '安装面Z_mm': MOUNT_Z,
                   '缩放': (MOTOR_TOP-MOUNT_Z)/2000, '分件': ['01', '02', '03', '06']},
        '图示基础底Z_mm': -1690,
        '展示样式': 'C41B02 正交样本。中性冷灰、平滑曲面法线，沿用原槽体与基础几何。',
        '坐标': '槽底中心为原点，东+X、北+Y、上+Z；GLB米制Y向上，OBJ米制Z向上',
        '来源': {'确认尺寸': '用户本轮给定', '侧视图': '来源_用户侧视图.png',
                 '位号映射': '../../parameters/D41B02A1.json（D41B02 水解槽类型）'},
        '模型说明': [
            '槽顶采用通用开窗支架、驱动与双端对称中间轴，槽内叶轮待设备资料。',
            '槽体及支架壳厚、支脚、基础平面深度和基础底高度为示意值；基础可单独隔离。',
            '独立类型模型，保留原槽体、槽盖及基础尺寸。',
        ],
    }
    (OUT / '参数.json').write_text(json.dumps(params, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_viewer():
    html = (PREHEATER / '3d.html').read_text(encoding='utf-8-sig')
    replacements = {
        'C41B02 · 钛液预热槽': 'D41B02 · 水解槽',
        'C41B02 钛液预热槽 · 3D 模型': 'D41B02 水解槽 · 3D 模型',
        'C41B02_钛液预热槽': STEM,
        'Ø5500 × 5000': 'Ø5900 × 4700',
        '2185 mm': '3076 mm',
        '7185 mm': '7776 mm',
        '模型档案 v1.4': '模型档案 v1.1',
        '<option value="shaft">轴与叶轮</option>': '',
    }
    for old, new in replacements.items():
        html = html.replace(old, new)
    (OUT / '3d.html').write_text(html, encoding='utf-8')


def write_elevation(assembly):
    def rectangle(x, z, width, height, css):
        return f'<rect x="{x}" y="{-z-height}" width="{width}" height="{height}" class="{css}"/>'

    drawing = [
        rectangle(-2950, 0, 5900, 4700, 'tank'),
    ]
    projected = []
    for _, color, verts, faces in assembly:
        for face in faces:
            points = [verts[i] for i in face]
            depth = sum(y for _, y, _ in points)/len(points)
            xy = ' '.join(f'{x:.1f},{-z:.1f}' for x, _, z in points)
            projected.append((depth, f'<polygon points="{xy}" fill="{color}"/>'))
    drawing.extend(polygon for _, polygon in sorted(projected, reverse=True))
    drawing.append(rectangle(-3035, 4700, 6070, 320, 'steel'))
    drawing.append(rectangle(-3035, -390, 6070, 190, 'foundation'))
    drawing.extend(rectangle(x-width/2, -1690, width, 1300, 'foundation') for x, width in PIERS)
    for i in range(12):
        x = 2730 * math.cos((i + 0.5) * math.tau / 12)
        drawing.extend(rectangle(x-w/2, z-h/2, w, h, 'steel')
                       for z, w, h in ((-15, 190, 30), (-100, 76, 140), (-185, 190, 30)))
    page = f'''<!doctype html>
<html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>D41B02 水解槽正立侧视</title>
<style>
body {{ background:#202931; color:#edf3f6; margin:0 auto; max-width:60rem; padding:1rem; font:16px sans-serif }}
a {{ color:#8fe6eb; margin-right:1rem }}
svg {{ display:block; width:100%; height:min(75vh,850px); margin-top:1rem }}
.tank {{ fill:#586b76; stroke:#bbd0d8; stroke-width:36 }}
.steel {{ fill:#566772; stroke:#dce6eb; stroke-width:20 }}
.rib {{ stroke:#dce6eb; stroke-width:8 }}
.foundation {{ fill:#5a514c; stroke:#c1afa2; stroke-width:20 }}
.dim {{ fill:none; stroke:#ffd47e; stroke-width:18 }}
text {{ fill:#ffd47e; font-size:210px }}
</style>
<h1>D41B02 水解槽 · 正立侧视</h1>
<nav><a href="3d.html">打开可旋转 3D 模型</a><a href="来源_用户侧视图.png">参考侧视图</a><a href="{STEM}.glb" download>下载 GLB</a></nav>
<svg viewBox="-4060 -8310 8500 10360" role="img" aria-label="水解槽侧视和主要尺寸">
{''.join(drawing)}
<path class="dim" d="M 620 -7776 H 900 V -4700 H 620 M 3100 -4700 H 3450 V 0 H 3100 M -2950 -380 V -730 H 2950 V -380"/>
<text x="960" y="-6238">3076</text><text x="3510" y="-2300">4700</text>
<text x="0" y="-830" text-anchor="middle">Ø5900</text>
</svg>
<p>尺寸单位 mm。槽底至电机顶 7776 mm，支脚及基础另计。</p>
</html>
'''
    (OUT / 'index.html').write_text(page, encoding='utf-8')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, help='原始侧视截图，仅首次归档时提供')
    args = parser.parse_args()
    build()
    if args.source:
        source_copy = OUT / '来源_用户侧视图.png'
        if not source_copy.exists():
            shutil.copyfile(args.source, source_copy)
