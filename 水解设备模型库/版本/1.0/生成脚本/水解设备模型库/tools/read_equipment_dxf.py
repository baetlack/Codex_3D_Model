"""Extract visible 2D equipment outlines and DXF handles from the reference sheet."""
from collections import defaultdict
from dataclasses import dataclass
from math import atan, atan2, ceil, cos, hypot, pi, radians, sin, tau
from pathlib import Path


@dataclass
class Path2D:
    points: list
    handle: str
    parent: str
    layer: str


def read_entities(path):
    raw = Path(path).read_bytes()
    try:
        lines = raw.decode('utf-8-sig').splitlines()
    except UnicodeError:
        lines = raw.decode('gb18030').splitlines()
    kind, fields = None, None
    for key, value in zip(lines[::2], lines[1::2]):
        code = int(key)
        if code == 0:
            if fields is not None:
                yield kind, fields
            kind, fields = value.strip(), defaultdict(list)
        elif fields is not None:
            fields[code].append(value)
            if kind == 'LWPOLYLINE' and code in (10, 20, 42):
                fields['vertices'].append((code, float(value)))
    if fields is not None:
        yield kind, fields


def first(fields, key, default=''):
    return fields.get(key, [default])[0]


def number(fields, key, default=0.0):
    return float(first(fields, key, default))


def arc(cx, cy, radius, start, end):
    count = max(3, ceil(abs(end - start) / (pi / 24)))
    return [(cx + radius * cos(start + (end - start) * i / count),
             cy + radius * sin(start + (end - start) * i / count)) for i in range(count + 1)]


def polyline(fields):
    vertices = []
    for code, value in fields['vertices']:
        if code == 10:
            vertices.append([value, 0.0, 0.0])
        else:
            vertices[-1][1 if code == 20 else 2] = value
    if not vertices:
        return []
    closed = int(number(fields, 70)) & 1
    endpoints = vertices[1:] + (vertices[:1] if closed else [])
    path = [tuple(vertices[0][:2])]
    for (x, y, bulge), (xx, yy, _) in zip(vertices, endpoints):
        length = hypot(xx-x, yy-y)
        if bulge and length:
            dx, dy = xx-x, yy-y
            offset = (1-bulge*bulge)/(4*bulge)
            cx, cy = (x+xx)/2-dy*offset, (y+yy)/2+dx*offset
            start = atan2(y-cy, x-cx)
            path.extend(arc(cx, cy, hypot(x-cx, y-cy), start, start+4*atan(bulge))[1:])
        else:
            path.append((xx, yy))
    return path


def geometry(kind, fields):
    x, y = number(fields, 10), number(fields, 20)
    if kind == 'LINE':
        return [(x, y), (number(fields, 11), number(fields, 21))]
    if kind in {'CIRCLE', 'ARC'}:
        start = radians(number(fields, 50))
        end = radians(number(fields, 51, 360))
        return arc(x, y, number(fields, 40), start, end if end > start else end + tau)
    if kind == 'LWPOLYLINE':
        return polyline(fields)
    if kind == 'ELLIPSE':
        u, v = number(fields, 11), number(fields, 21)
        ratio = number(fields, 40)
        start, end = number(fields, 41), number(fields, 42, tau)
        circle = arc(0, 0, 1, start, end if end > start else end + tau)
        return [(x + a*u - b*v*ratio, y + a*v + b*u*ratio) for a, b in circle]
    return []


def read_drawing(path):
    blocks, root = {}, []
    section = ''
    active = None
    for kind, fields in read_entities(path):
        if kind == 'SECTION':
            section = first(fields, 2)
        elif kind == 'ENDSEC':
            section = ''
        elif section == 'BLOCKS':
            if kind == 'BLOCK':
                active = []
                blocks[first(fields, 2)] = (number(fields, 10), number(fields, 20), active)
            elif kind == 'ENDBLK':
                active = None
            elif active is not None:
                active.append((kind, fields))
        elif section == 'ENTITIES' and first(fields, 410, 'Model') == 'Model':
            root.append((kind, fields))

    def expand(entities, transform, parent='', inherited='0', chain=()):
        for kind, fields in entities:
            handle, layer = first(fields, 5), first(fields, 8)
            if layer == '0':
                layer = inherited
            if kind == 'INSERT':
                name = first(fields, 2)
                if name not in blocks or name in chain:
                    continue
                bx, by, children = blocks[name]
                tx, ty = number(fields, 10), number(fields, 20)
                sx, sy = number(fields, 41, 1), number(fields, 42, 1)
                angle = radians(number(fields, 50))
                c, s = cos(angle), sin(angle)

                def placed(x, y):
                    x, y = (x-bx)*sx, (y-by)*sy
                    return transform(tx + c*x - s*y, ty + s*x + c*y)

                yield from expand(children, placed, parent or handle, layer, (*chain, name))
            else:
                points = geometry(kind, fields)
                if points:
                    yield Path2D([transform(x, y) for x, y in points], handle, parent or handle, layer)

    return list(expand(root, lambda x, y: (x, y))), root


if __name__ == '__main__':
    import sys
    from PIL import Image, ImageDraw

    paths, _ = read_drawing(sys.argv[1])
    x0, y0, x1, y1 = 0, -9000, 102000, 42000
    scale = 0.023
    img = Image.new('RGB', (int((x1-x0)*scale), int((y1-y0)*scale)), '#172029')
    draw = ImageDraw.Draw(img)
    for item in paths:
        draw.line([((x-x0)*scale, (y1-y)*scale) for x, y in item.points], fill='#d5e4ec')
    for x in range(0, 102000, 5000):
        draw.text(((x-x0)*scale, (y1-14000)*scale), str(x), fill='orange')
    for y in range(-5000, 42000, 5000):
        draw.text((1, (y1-y)*scale), str(y), fill='orange')
    img.save(sys.argv[2])
