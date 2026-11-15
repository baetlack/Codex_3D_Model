"""Validate portable entry links, inventories and screenshot provenance."""
from pathlib import Path
import json,re,hashlib
from urllib.parse import unquote
ROOT=Path(__file__).resolve().parent.parent
broken=[]
for page in ['index.html','models/连接件库/index.html','models/整体/index.html','models/整体/reports/装配说明.html']:
    f=ROOT/page
    for url in re.findall(r'''(?:src|href)=["']([^"']+)''',f.read_text(encoding='utf-8')):
        if url.startswith(('http:','https:','data:','#')):continue
        if not (f.parent/unquote(url.split('#')[0])).exists():broken.append([page,url])
assert not broken,broken
raw=ROOT/'data/原始资料/连接件'
images=list(raw.glob('*.png'));assert len(images)==56
for p in images:
    q=ROOT/'models/连接件库/screenshots'/p.name
    assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(q.read_bytes()).digest(),p.name
assembly=json.loads((ROOT/'models/整体/assembly.json').read_text(encoding='utf-8'))
sources=json.loads((ROOT/'data/来源记录.json').read_text(encoding='utf-8'))
assert {p['id'] for p in assembly['parts']}=={p['id'] for p in sources['parts']}
for p in sources['parts']:
    if 'parameter_record' in p:assert (ROOT/p['parameter_record']).is_file()
assert len(assembly['parts'])==112 and len(assembly['connections'])==110
report={'status':'passed','portable_html_links':'passed','parts_with_provenance':112,
        'connections':110,'preserved_original_screenshots':56,
        'screenshot_copies_sha256_identical':True,
        'rebuild_report':'重建检查.json','browser_report':'../models/整体/reports/browser_check.json',
        'scope':'工程文件整理与来源完整性；几何与浏览交互见各独立报告。'}
(ROOT/'data/工程检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
