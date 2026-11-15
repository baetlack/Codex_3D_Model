from pathlib import Path
from collections import Counter
import csv
import hashlib, json

ROOT = Path(__file__).resolve().parent
SRC = ROOT / '原始资料'
ARCH = SRC / '20251027 B系列结晶冷却厂房建施图_t3.dxf'
STRUCT = SRC / '20260813 (补充条件)B系列结晶冷却厂房结构施工图(1).dxf'


def entities(path):
    lines = path.read_bytes().decode('cp936', errors='replace').splitlines()
    inside = False
    current = None
    for code, value in zip(lines[::2], lines[1::2]):
        code, value = code.strip(), value.strip()
        if code == '2' and value == 'ENTITIES':
            inside = True
            continue
        if inside and code == '0' and value == 'ENDSEC':
            if current:
                yield current
            break
        if not inside:
            continue
        if code == '0':
            if current:
                yield current
            current = {'type': value, 'data': []}
        elif current:
            current['data'].append((code, value))


def get(entity, code, default=None):
    return next((v for c, v in entity['data'] if c == code), default)


def block_bounds(path):
    lines = path.read_bytes().decode('cp936', errors='replace').splitlines()
    pairs = [(a.strip(), b.strip()) for a, b in zip(lines[::2], lines[1::2])]
    inside, current, result = False, None, {}

    def save():
        if not current or not current['name']:
            return
        xs, ys = [], []
        for code, value in current['data']:
            if code in ('10','11','12','13','14','15','16','17','18'):
                try: xs.append(float(value))
                except ValueError: pass
            elif code in ('20','21','22','23','24','25','26','27','28'):
                try: ys.append(float(value))
                except ValueError: pass
        if xs and ys:
            result[current['name']] = (min(xs), min(ys), max(xs), max(ys))

    for code, value in pairs:
        if code == '2' and value == 'BLOCKS':
            inside = True
            continue
        if inside and code == '0' and value == 'ENDSEC':
            save()
            break
        if not inside:
            continue
        if code == '0' and value == 'BLOCK':
            save()
            current = {'name': None, 'data': []}
        elif code == '0' and value == 'ENDBLK':
            save()
            current = None
        elif current and current['name'] is None and code == '2':
            current['name'] = value
        elif current:
            current['data'].append((code, value))
    return result


def main():
    # Read doors and windows from the four elevations. The elevation drawings are
    # authoritative for facade positions; plan INSERT coordinates were misaligned.
    origin_x, origin_y, width, depth = 4388240.0, 171772.0, 44650.0, 72650.0
    block_dims = block_bounds(ARCH)
    views = [
        {'name':'long_elevation_1', 'side':'east', 'x0':4386551.0, 'x1':4459201.0, 'base_y':30811.0},
        {'name':'long_elevation_2', 'side':'west', 'x0':4519084.0, 'x1':4591734.0, 'base_y':30811.0},
        {'name':'end_elevation_1', 'side':'south', 'x0':4652447.0, 'x1':4697097.0, 'base_y':30811.0},
        {'name':'end_elevation_2', 'side':'north', 'x0':4722537.0, 'x1':4767187.0, 'base_y':30811.0},
    ]
    doors = []
    # Door apertures are baseline gaps in A-Elev-Wall elevation polylines.
    for view in views:
        segments = []
        for e in entities(ARCH):
            if get(e, '8', '') != 'A-Elev-Wall':
                continue
            if e['type'] == 'LINE':
                a = (float(get(e, '10', '0')), float(get(e, '20', '0')))
                b = (float(get(e, '11', '0')), float(get(e, '21', '0')))
                pairs = [(a, b)]
            elif e['type'] == 'LWPOLYLINE':
                points, x = [], None
                for code, value in e['data']:
                    if code == '10':
                        x = float(value)
                    elif code == '20' and x is not None:
                        points.append((x, float(value)))
                        x = None
                pairs = list(zip(points, points[1:]))
            else:
                continue
            for a, b in pairs:
                if (abs(a[1] - 32211.0) <= 5 and abs(b[1] - 32211.0) <= 5
                        and abs(a[0] - b[0]) > 50
                        and min(a[0], b[0]) >= view['x0'] - 100
                        and max(a[0], b[0]) <= view['x1'] + 100):
                    segments.append((min(a[0], b[0]), max(a[0], b[0])))
        merged = []
        for lo, hi in sorted(segments):
            if merged and lo <= merged[-1][1] + 10:
                merged[-1] = (merged[-1][0], max(hi, merged[-1][1]))
            else:
                merged.append((lo, hi))
        for (_, left_end), (right_start, _) in zip(merged, merged[1:]):
            gap = right_start - left_end
            if not 900 <= gap <= 5200:
                continue
            height = (4800 if view['name'] == 'end_elevation_1' and gap >= 4000
                      else 3600 if view['name'] == 'long_elevation_2' and gap >= 2800
                      else 3300 if view['name'] == 'long_elevation_2'
                      else 2700)
            sill = (200 if view['name'] == 'end_elevation_1' and gap >= 4000
                    else 300 if view['name'] == 'long_elevation_2' and gap >= 2800 else 0)
            cad_block = ('M4848' if view['name'] == 'end_elevation_1' and gap >= 4000
                         else 'm3036' if view['name'] == 'long_elevation_2' and gap >= 2800
                         else 'A-Elev-Wall-gap')
            doors.append({'side': view['side'], 'kind': 'door',
                          'center': round((left_end + right_start) / 2 - view['x0'], 2),
                          'width': round(gap, 2), 'sill': sill, 'height': height,
                          'cad_block': cad_block, 'elevation': view['name']})
    window_blocks = {'C1818','C1812','C1218','C1212','C1212a','C0609'}
    windows = []
    for view in views:
        for e in entities(ARCH):
            if e['type'] != 'INSERT' or get(e, '8', '') != '0':
                continue
            block = get(e, '2', '')
            if block not in window_blocks or block not in block_dims:
                continue
            ix, iy = float(get(e, '10', '0')), float(get(e, '20', '0'))
            if not (view['x0'] - 100 <= ix <= view['x1'] + 100 and 30800 <= iy <= 52000):
                continue
            bx0, by0, bx1, by1 = block_dims[block]
            sx, sy = float(get(e, '41', '1')), float(get(e, '42', '1'))
            xs = [ix + sx * bx0, ix + sx * bx1]
            ys = [iy + sy * by0, iy + sy * by1]
            u0, u1 = min(xs) - view['x0'], max(xs) - view['x0']
            sill, head = min(ys) - view['base_y'], max(ys) - view['base_y']
            if u1 <= 0 or u0 >= view['x1'] - view['x0'] or head <= 0:
                continue
            windows.append({'side': view['side'], 'kind':'window', 'center':round((u0+u1)/2,2),
                            'width':round(u1-u0,2), 'sill':round(sill,2), 'head':round(head,2),
                            'cad_block':block, 'elevation':view['name']})
    # The supplied east-face screenshot shows 11 additional C1818-sized window
    # openings that are not separate INSERTs in the elevation DXF. Their bay
    # positions follow the same 7,200 mm facade rhythm and their level/size match
    # adjacent C1818 windows. Record these screenshot-confirmed omissions explicitly.
    east_screenshot_windows = [
        (11125, 1400, 3200), (25525, 1400, 3200), (39925, 1400, 3200), (61525, 1400, 3200),
        (11125, 7400, 9200), (25525, 7400, 9200), (39925, 7400, 9200),
        (11125, 13400, 15200), (25525, 13400, 15200),
        (39925, 13400, 15200), (61525, 13400, 15200),
    ]
    for center, sill, head in east_screenshot_windows:
        windows.append({'side':'east', 'kind':'window', 'center':center, 'width':1800,
                        'sill':sill, 'head':head, 'cad_block':'C1818-screenshot-confirmed',
                        'elevation':'east-face-screenshot'})
    # The construction drawing has one gridded transom above a wide door on a dedicated layer.
    transoms = {}
    for e in entities(ARCH):
        if e['type'] != 'LWPOLYLINE' or get(e, '8', '') != 'A-ELEV-WIND':
            continue
        points, x = [], None
        for code, value in e['data']:
            if code == '10':
                x = float(value)
            elif code == '20' and x is not None:
                points.append((x, float(value)))
                x = None
        if len(points) < 4:
            continue
        xs, ys = [q[0] for q in points], [q[1] for q in points]
        cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
        view = next((v for v in views if v['x0'] <= cx <= v['x1']), None)
        if not view or not (30800 <= cy <= 52000):
            continue
        key = (view['side'], round(cx/100), round(cy/100))
        transoms.setdefault(key, []).append((max(xs)-min(xs), max(ys)-min(ys), min(xs), max(xs), min(ys), max(ys), view))
    for group in transoms.values():
        w, h, x0, x1, y0, y1, view = max(group, key=lambda q:q[0]*q[1])
        if w < 500 or h < 300:
            continue
        windows.append({'side':view['side'], 'kind':'window', 'center':round((x0+x1)/2-view['x0'],2),
                        'width':round(w,2), 'sill':round(y0-view['base_y'],2),
                        'head':round(y1-view['base_y'],2), 'cad_block':'A-ELEV-WIND',
                        'elevation':view['name']})
    # The west elevation is drawn L→A, opposite the model's +Y facade coordinate.
    # Reverse its horizontal opening order to match the supplied exterior screenshot.
    for opening in doors + windows:
        if opening['side'] == 'west':
            opening['center'] = round(depth - opening['center'], 2)
    openings = doors + windows
    # Collapse duplicate INSERT references while preserving distinct stacked windows.
    clean, seen = [], set()
    for a in openings:
        key = (a['side'], a['kind'], a['center'], a['width'], a.get('sill'), a.get('height'))
        if key not in seen:
            seen.add(key)
            clean.append(a)
    window_counts = Counter(a['side'] for a in clean if a['kind'] == 'window')
    door_counts = Counter(a['side'] for a in clean if a['kind'] == 'door')
    doc = {
        'source': ARCH.name, 'source_sha256': hashlib.sha256(ARCH.read_bytes()).hexdigest(),
        'revision': 'opening-correction-west-m3036-2026-11-05',
        'units': 'mm', 'axes': {'east': '+X', 'north': '+Y', 'up': '+Z'},
        'plan_bounds_mm': [width, depth], 'origin_source_xy': [origin_x, origin_y],
        'elevation_mapping': {'long_elevation_1':'east', 'long_elevation_2':'west',
                             'end_elevation_1':'south', 'end_elevation_2':'north'},
        'facade_orientation_note': 'West elevation openings are reversed horizontally from CAD view coordinates to match the supplied exterior screenshot direction L-to-A in the model +Y facade coordinate. South and north end elevations are assigned to opposite cardinal sides per user screenshot review.',
        'window_source_note': 'Window position, width, sill, and head are transformed from C* window block extents in the four architectural elevations. The east-face screenshot shows 11 additional C1818-sized openings omitted as separate DXF INSERTs; their bay positions follow the 7,200 mm facade rhythm and dimensions/levels match adjacent C1818 windows. These screenshot-confirmed openings are recorded explicitly.',
        'door_height_note': 'Door/gate positions and clear widths are extracted from baseline gaps in the four elevation A-Elev-Wall polylines. South M4848 is 4,800 mm high from +200 to +5,000 mm. West m3036 is 3,600 mm high from +300 to +3,900 mm. Other door heights follow legible elevation annotations.',
        'openings': clean,
        'counts': {'window':sum(window_counts.values()), 'door':sum(door_counts.values())},
        'window_counts_by_side': dict(window_counts), 'door_counts_by_side': dict(door_counts),
    }
    (ROOT / '立面门窗数据.json').write_text(json.dumps(doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / '立面门窗数据.js').write_text('window.FACADE_DATA=' + json.dumps(doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')

    # Extract closed COLU footprints from the structural sheet titled 5.970m~9.900m.
    # They form the complete 8 x 11 frame plus ten additional local 400 mm columns.
    target = []
    for e in entities(STRUCT):
        if get(e, '8', '') != 'COLU' or e['type'] != 'LWPOLYLINE' or not (int(get(e, '70', '0')) & 1):
            continue
        pts, x = [], None
        for c, v in e['data']:
            if c == '10':
                x = float(v)
            elif c == '20' and x is not None:
                pts.append((x, float(v)))
                x = None
        if len(pts) < 4:
            continue
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        if 8259000 <= x0 and x1 <= 8305500 and -3254000 <= y0 and y1 <= -3179000:
            target.append({'cx': sum(xs) / len(xs), 'cy': sum(ys) / len(ys), 'width': x1 - x0, 'depth': y1 - y0})
    if len(target) != 98:
        raise RuntimeError(f'Expected 98 columns in the 5.970m~9.900m plan, found {len(target)}')
    x_min = min(c['cx'] for c in target)
    y_min = min(c['cy'] for c in target)
    columns = [{'x': round(c['cx'] - x_min, 2), 'y': round(c['cy'] - y_min, 2),
                'width': round(c['width'], 2), 'depth': round(c['depth'], 2)} for c in target]
    columns.sort(key=lambda c: (c['y'], c['x']))
    massing = json.loads((ROOT / '主体尺寸.json').read_text(encoding='utf-8'))['massing']
    levels = massing['floor_levels']
    col_doc = {
        'source': STRUCT.name, 'source_sha256': hashlib.sha256(STRUCT.read_bytes()).hexdigest(),
        'units': 'mm', 'axes': {'east': '+X', 'north': '+Y', 'up': '+Z'},
        'plan_title': '5.970m~9.900m柱平面布置图', 'cad_bounds': [8259000, -3254000, 8305500, -3179000],
        'local_origin_cad_xy': [round(x_min, 2), round(y_min, 2)],
        'story_ranges_mm': list(zip(levels, levels[1:])),
        'building_massing': massing,
        'column_count': len(columns), 'columns': columns,
        'note': '平面位置和截面取自结构图 COLU 闭合柱轮廓。该图直接标注基础顶面至+5.970m、+5.970m至+9.900m；上部+9.900m以上柱段未在该张图内分段，本模型按同一柱位连续显示至+23.000m，待上部柱平面复核。',
    }
    (ROOT / '结构立柱数据.json').write_text(json.dumps(col_doc, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    (ROOT / '结构立柱数据.js').write_text('window.STRUCTURE_COLUMNS=' + json.dumps(col_doc, ensure_ascii=False, separators=(',', ':')) + ';\n', encoding='utf-8')
    with (ROOT / '结构立柱定位表.csv').open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['柱编号', '柱段', '中心东坐标X(mm)', '中心北坐标Y(mm)', '截面X(mm)', '截面Y(mm)', '柱底标高(mm)', '柱顶标高(mm)', '备注'])
        ranges = col_doc['story_ranges_mm']
        for i, col in enumerate(columns, 1):
            for level, (z0, z1) in enumerate(ranges, 1):
                note = '该柱段截面/平面取自 5.970m~9.900m 柱平面；+9.900m以上连续显示部分待上部柱平面复核。' if level == 3 else '柱位与截面取自 5.970m~9.900m 柱平面。'
                writer.writerow([f'K{i:03d}', level, col['x'], col['y'], col['width'], col['depth'], z0, z1, note])
    print('openings', doc['counts'], 'columns', len(columns), 'column sizes', Counter((c['width'], c['depth']) for c in columns))


if __name__ == '__main__':
    main()
