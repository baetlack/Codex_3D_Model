"""Reconstruct the annotated side view as a provisional top-entry agitator."""
import argparse
import math

from build_tank_mixer import ROOT, add, box, cyl, export_model, parts, ring

OUT = ROOT / 'models/设备/槽罐搅拌器_标注侧视'
STEM = '槽罐搅拌器_v0.3'
MOTOR, DRIVE, SHAFT, IMPELLER, FRAME, MOUNT = (
    '#387f7c', '#597a98', '#d6a45a', '#bb9955', '#6d8497', '#9baab4'
)


def build(height):
    # Measurements use the 1368 x 1824 reference display. Widths average both
    # sides of the slightly leaning photographed centerline. Z=0 is the seat.
    parts.clear()
    scale = height / (1594 - 112)

    def z(row):
        return (1594 - row) * scale

    def disk(name, top, bottom, radius, color, lower_radius=None):
        cyl(name, z(bottom), z(top), (lower_radius or radius) * scale, color, r2=radius * scale)

    def annulus(name, top, bottom, outer, bore, color):
        ring(name, z(bottom), z(top), outer * scale, bore * scale, color)

    def turn(name, profile, color, steps=64):
        """A solid stepped profile, from the bottom ring to the top ring."""
        vertices = [(r*scale*math.cos(a), r*scale*math.sin(a), z(row))
                    for row, r in reversed(profile) for a in angles(steps)]
        faces = [tuple(reversed(range(steps)))]
        for base in range(0, len(vertices) - steps, steps):
            for i in range(steps):
                j = (i+1) % steps
                faces.append((base+i, base+j, base+steps+j, base+steps+i))
        faces.append(tuple(range(len(vertices)-steps, len(vertices))))
        add(name, color, vertices, faces)

    def open_sides(prefix, profile, thickness, color, steps=24):
        """Two side shells. Varying sector angles round the access-window ends."""
        stride = 2*(steps+1)
        for side, center in enumerate((0, math.pi), 1):
            vertices = []
            for row, radius, spread in reversed(profile):
                for r in (radius, radius-thickness):
                    for i in range(steps+1):
                        a = center + math.radians(spread) * (2*i/steps-1)
                        vertices.append((scale*r*math.cos(a), scale*r*math.sin(a), z(row)))
            faces = []
            inner = steps+1
            for a in range(0, len(vertices)-stride, stride):
                b = a+stride
                for i in range(steps):
                    j = i+1
                    faces.extend([(a+i, a+j, b+j, b+i),
                                  (a+inner+j, a+inner+i, b+inner+i, b+inner+j)])
                faces.extend([(a+inner, a, b, b+inner),
                              (a+steps, a+stride-1, b+stride-1, b+steps)])
            top = len(vertices)-stride
            for i in range(steps):
                faces.extend([(i+1, i, inner+i, inner+i+1),
                              (top+i, top+i+1, top+inner+i+1, top+inner+i)])
            add(f'{prefix}_{side}', color, vertices, faces)

    def window_frame(profile, bands, seats, thickness, steps=24):
        """Build the window shell and both bored seats as one connected mesh."""
        side_size = steps + 1
        stride = 2 * side_size
        levels = list(reversed(profile))
        level_by_row = {row: i for i, (row, _, _) in enumerate(levels)}
        seat_flange_rows = {flange for flange, _ in seats}
        web_columns = {side * side_size + i for side in range(2) for i in range(8, 16)}

        def sector_angles(spread):
            return [center + math.radians(spread) * (2*i/steps-1)
                    for center in (0, math.pi) for i in range(side_size)]

        def point(row, radius, angle):
            r = radius * scale
            return (r*math.cos(angle), r*math.sin(angle), z(row))

        vertices = []
        for inset in (0, thickness):
            for row, radius, spread in levels:
                vertices.extend(point(row, radius-inset, a) for a in sector_angles(spread))

        outer, inner = [], []
        offset = len(vertices) // 2
        for level, (lower, upper) in enumerate(zip(levels, levels[1:])):
            continuous = any(start <= upper[0] and lower[0] <= end for start, end in bands)
            flange = (upper[0], lower[0]) in seat_flange_rows
            base = level * stride
            for i in range(stride):
                if continuous or (i+1) % side_size:
                    a, b = base+i, base+(i+1) % stride
                    face = (a, b, b+stride, a+stride)
                    outer.append(face)
                    if not (flange and i in web_columns):
                        inner.append(tuple(v+offset for v in reversed(face)))

        edges = {(a, b) for face in outer for a, b in zip(face, (*face[1:], face[0]))}
        rims = [(b, a, a+offset, b+offset) for a, b in sorted(edges) if (b, a) not in edges]
        faces = outer + inner + rims

        columns = [(i, step/8) for i in range(stride)
                   for step in range(8 if (i+1) % side_size == 0 else 1)]
        bore_radius = 31
        for (top, bottom), seat_profile in seats:
            top_level, bottom_level = level_by_row[top], level_by_row[bottom]
            top_spread, bottom_spread = levels[top_level][2], levels[bottom_level][2]
            lower_base, upper_base = offset + bottom_level*stride, offset + top_level*stride
            outline = [(seat_profile[-1][0], bore_radius), *reversed(seat_profile), (seat_profile[0][0], bore_radius)]
            rings = []
            # Run from the lower bore edge around the outside and back to the bore.
            for row, radius in outline:
                fraction = max(0, min(1, (row-top)/(bottom-top)))
                if radius == bore_radius:
                    fraction = 0.5
                polar = sector_angles(top_spread + fraction*(bottom_spread-top_spread))
                polar.append(polar[0] + math.tau)
                rings.append(len(vertices))
                vertices.extend(point(row, radius, polar[i] + (polar[i+1]-polar[i])*t) for i, t in columns)

            # Replace matching wall patches on the seat and shell with radial webs.
            joins, join_edges = {}, set()
            for k, lower_ring in enumerate(rings):
                next_ring = (k+1) % len(rings)
                upper_ring = rings[next_ring]
                flange = (outline[k][0], outline[next_ring][0]) == (bottom, top)
                for j, (i, _) in enumerate(columns):
                    n = (j+1) % len(columns)
                    face = (lower_ring+j, lower_ring+n, upper_ring+n, upper_ring+j)
                    if flange and i in web_columns:
                        joins.update(zip(face, (lower_base+i, lower_base+i+1, upper_base+i+1, upper_base+i)))
                        join_edges.update(zip(face, (*face[1:], face[0])))
                    else:
                        faces.append(face)
            faces.extend((a, b, joins[b], joins[a]) for a, b in sorted(join_edges) if (b, a) not in join_edges)

        add('06_Tapered_window_frame_with_bored_seats', FRAME, vertices, faces)

    turn('01_Motor', [(112, 89), (116, 96), (124, 101), (209, 101),
                      (211, 94), (382, 94), (383, 103), (395, 103),
                      (405, 94), (405, 90), (422, 90), (422, 142), (436, 142)], MOTOR)
    for i, a in enumerate(angles(24), 1):
        box(f'01_Fin_{i:02}', (0, 0, z(296)), (10*scale, 5*scale, 168*scale), MOTOR)
        name, color, vertices, faces = parts[-1]
        parts[-1] = (name, color, [((x+98*scale)*math.cos(a)-y*math.sin(a),
                                   (x+98*scale)*math.sin(a)+y*math.cos(a), zz)
                                  for x, y, zz in vertices], faces)

    annulus('02_Upper_mount_flange', 436, 460, 190, 130, DRIVE)
    annulus('02_Upper_housing', 460, 538, 149, 130, DRIVE)
    annulus('02_Middle_flange_top', 538, 556, 191, 124, DRIVE)
    annulus('02_Middle_flange_bottom', 556, 574, 191, 124, DRIVE)
    open_sides('02_Lower_housing', [(574, 139, 58), (588, 134, 56),
                                   (675, 134, 56), (686, 139, 58)], 12, DRIVE)
    annulus('02_Base_flange_top', 686, 705, 231, 67, DRIVE)
    annulus('02_Base_flange_bottom', 705, 724, 231, 67, DRIVE)
    disk('02_Drive_output_shaft', 436, 724, 40, DRIVE)
    disk('02_Output_sleeve', 724, 775, 61, DRIVE)

    shaft_head = [(775, 101), (815, 101), (815, 61), (875, 61), (879, 57), (879, 30)]
    shaft_end = [(775 + 1710 - row, radius) for row, radius in reversed(shaft_head)]
    turn('03_Intermediate_shaft', shaft_head + shaft_end, SHAFT)
    disk('05_Impeller_hub', 1803, 1854, 53, IMPELLER)
    pitch = math.radians(30)
    for i, a in enumerate(angles(4), 1):
        box(f'05_Pitched_blade_{i}', (0, 0, 0), (187*scale, 56*scale, 7*scale), IMPELLER)
        name, color, vertices, faces = parts[-1]
        rotated = []
        for x, y, zz in vertices:
            radial = x + 137.5*scale
            tangent = y*math.cos(pitch)-zz*math.sin(pitch)
            rotated.append((radial*math.cos(a)-tangent*math.sin(a),
                            radial*math.sin(a)+tangent*math.cos(a),
                            z(1830)+y*math.sin(pitch)+zz*math.cos(pitch)))
        parts[-1] = (name, color, rotated, faces)

    # Outer housing stays tapered. The curved opening edges are inferred in depth.
    frame_rows = [(724, 86), (751, 83), (759, 76), (776, 60), (796, 52),
                  (988, 46.65), (1025, 45.62),
                  (1119, 43), (1136, 54), (1146, 65), (1153, 83),
                  (1199, 83), (1205, 67), (1217, 56), (1233, 49),
                  (1322, 47.47), (1363, 46.77),
                  (1466, 45), (1485, 53), (1500, 67), (1510, 82), (1575, 86)]
    seats = [((988, 1025), [(957, 71), (969, 81), (988, 81), (988, 121),
                           (1025, 121), (1025, 81), (1076, 81), (1088, 70), (1092, 63)]),
             ((1322, 1363), [(1290, 68), (1301, 80), (1322, 80), (1322, 122),
                             (1363, 122), (1363, 80), (1408, 80), (1423, 66), (1427, 58)])]
    window_frame([(y, 161+(y-724)*66/851, a) for y, a in frame_rows],
                 [(724, 751), (1153, 1199), (1510, 1575)], seats, 16)
    annulus('06_Frame_foot', 1575, 1594, 287, 205, FRAME)
    annulus('07_Tank_interface_rim', 1594, 1628, 337, 286, MOUNT)
    annulus('07_Tank_interface_short_wall', 1628, 1672, 294, 282, MOUNT)


def angles(count):
    return (math.tau*i/count for i in range(count))


def verify():
    """Check each exported component is an oriented, nondegenerate closed mesh."""
    from collections import Counter

    names = set()
    for name, _, vertices, faces in parts:
        assert name not in names, name
        names.add(name)
        edges = Counter((a, b) for face in faces for a, b in zip(face, (*face[1:], face[0])))
        assert all(a != b and count == edges[b, a] == 1 for (a, b), count in edges.items()), name
        volume = 0
        for face in faces:
            a = vertices[face[0]]
            for i in range(1, len(face)-1):
                b, c = vertices[face[i]], vertices[face[i+1]]
                u, v = [y-x for x, y in zip(a, b)], [y-x for x, y in zip(a, c)]
                normal = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                assert math.hypot(*normal) > 1e-9, name
                volume += sum(x*y for x, y in zip(a, normal))/6
        assert volume > 0, name
    assert {name[:2] for name in names} == {'01', '02', '03', '05', '06', '07'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--height', type=float, default=2000, help='provisional motor-top height above Z=0, in mm')
    parser.add_argument('--out', type=type(OUT), default=OUT, help='model export directory')
    args = parser.parse_args()
    if not math.isfinite(args.height) or args.height <= 0:
        parser.error('--height must be positive and finite')
    build(args.height)
    verify()
    export_model(args.out, STEM, color_materials=True, smooth=True)
    print(f'{len(parts)} named components exported and checked.')
