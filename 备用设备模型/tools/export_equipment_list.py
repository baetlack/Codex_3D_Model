"""Export the equipment register from the maintained equipment model catalog."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT.parent / '水解设备模型库'
catalog = json.loads((LIB / 'catalog.json').read_text(encoding='utf-8-sig'))
rows = []
for item in catalog['models']:
    tag = item.get('id', '')
    cad = item.get('cad_position_mm') or ['', '']
    historical_dims = ''
    if item.get('w') and item.get('h'):
        historical_dims = f"{item['w']:g} × {item['h']:g} mm"
    archive_dims = ''
    note = ''
    if tag in {f'C41B02{x}' for x in 'ABCDE'}:
        archive_dims = 'Ø5500 × 5000 mm'
        note = 'C41B02已确认类型模型；旧模型库几何保留未覆盖'
    pos_el = item.get('pos_el')
    rows.append({
        '设备名称': item.get('name', ''),
        '设备位号': tag,
        '所属位号组': item.get('group', ''),
        '台账规格': item.get('spec', ''),
        '台账组数量': item.get('qty', ''),
        '模型库现有外形尺寸(宽×高)': historical_dims,
        '本次确认类型模型尺寸': archive_dims,
        '楼层': item.get('level', ''),
        'POS EL(m)': pos_el if pos_el is not None else '',
        'DXF定位X(mm)': cad[0] if len(cad) > 0 else '',
        'DXF定位Y(mm)': cad[1] if len(cad) > 1 else '',
        '平面图': item.get('plan_sheet', ''),
        '设备类别': item.get('shape', ''),
        '定位状态': '已定位' if cad and len(cad) >= 2 and cad[0] is not None and cad[1] is not None else '未定位',
        '高度依据': item.get('height_basis', ''),
        '备注': note,
    })

out = ROOT / '设备清单.csv'
fields = list(rows[0]) if rows else []
with out.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
print(f'Wrote {len(rows)} equipment records to {out}')
