"""Verify the requested revision against the independent source records."""
from pathlib import Path
import json,numpy as np
from check_assembly import script
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'水解总装工程'
cfg=json.loads((OUT/'assembly.json').read_text());building=script(ROOT/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts'];source=json.loads((ROOT/'厂房外观模型/建筑/结构立柱数据.json').read_text())['columns']
cols=[p for p in building if p['kind']=='structure'];assert len(cols)==88
for i,c in enumerate(source):
 existing=next((p for p in cols if p['name']=='COL-%03d'%i),None)
 if c['width']==400 and c['x']>38000:assert existing is None
 else:
  assert existing is not None
  v=np.array(existing['vertices']);assert np.allclose(v.max(0)-v.min(0),[c['width'],c['depth'],23000]);assert np.allclose((v.max(0)+v.min(0))[:2]/2,[c['x'],c['y']])
floors=[p for p in building if p['kind']=='floor'];assert sorted(p['el'] for p in floors)==[100,106,112,123]
assert all(not p['check'] for p in floors)
for p in floors:assert max(v[2] for v in p['vertices'])==(p['el']-100)*1000
assert all(p['rotation_deg']==(180 if p['id'][6] in 'DE' else 0) and p['mirror_y']==(p['id'][6] in 'DE') for p in cfg['equipment'] if p['asset']=='D41B02')
assert all(p['rotation_deg']==0 for p in cfg['equipment'] if p['asset']=='C41B01')
seed={p['id']:p for p in cfg['equipment'] if p['asset']=='D41B01'}
assert seed['D41B01B']['mirror_y'] and not seed['D41B01C']['mirror_y']
review=json.loads((OUT/'data/布置复核.json').read_text());extra=(6 if 'C41B04' in cfg['equipment_versions'] else 0)-(5 if 'D41B01' in cfg['equipment_versions'] else 0);assert review['reviewed']==51+extra and review['pending']==21-extra
assert len([r for r in review['records'] if r.get('equipment_version')==cfg['equipment_versions']['C41B02'] and '待核' in r['status']])==5
for r in review['records']:
 w=r.get('evidence',{}).get('top_port_witness')
 if w and r['id'][:6] in ['D41B02','F41B01','C41B01','C41B02','C41B03','D41B01','C41B04']:assert w['matched_within_5mm']==w['model_features'],r['id']
for p in cfg['equipment']:
 if p['asset'] in ['P41B01','P41B02','P41B08']:assert 'sample_model_origin_world_mm' in p['layout_review']
report=json.loads((OUT/'data/桥架立柱核对.json').read_text());assert report['columns_retained']==88
assert all(p['interior_sample_depth_mm']>report['contact_tolerance_mm'] for p in report['penetrations'])
assert all(p['status']=='表面接触（正常）' for p in report['normal_contacts'])
print(f"建筑柱/楼板保持；平面方向复核{review['reviewed']}台、待核{review['pending']}台；C41B02新接口待核标签及表面接触分类通过")
