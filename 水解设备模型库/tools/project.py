"""Equipment module versions: preserve the actual current runtime and pin cross-module assets."""
from pathlib import Path
import json,hashlib,shutil,sys
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
INDEX=ROOT/'data/文件清单.json'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def files(root):return {p.relative_to(root).as_posix():sha(p) for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts and p!=INDEX}
def freeze():
 target=ROOT/'版本/1.0';assert not target.exists(),'1.0 exists; never overwrite it'
 dest=target/'快照';original={}
 def copy(source,relative):
  if source.is_dir():
   for p in sorted(source.rglob('*')):
    if not p.is_file() or '__pycache__' in p.parts:continue
    copy(p,Path(relative)/p.relative_to(source))
  else:
   q=dest/relative;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,q);original[str(relative)]=sha(source)
 # Current library runtime, all 32 type models, original records and exports. Original
 # CAD stays shared and is fingerprinted separately; no extra copies of 40 MB drawings.
 for p in ROOT.iterdir():
  if p.name in ['版本','水解设备图纸','obj','screenshots','tools','data']:continue
  if p.name=='示图建模_20260521':
   for child in p.iterdir():
    if child.name not in ['原始资料','__pycache__']:copy(child,Path(ROOT.name)/p.name/child.name)
  else:copy(p,Path(ROOT.name)/p.name)
 copy(REPO/'水解桥架工程/models/设备/设备基础_20261106',Path('水解桥架工程/models/设备/设备基础_20261106'))
 copy(REPO/'水解桥架工程/models/整体',Path('水解桥架工程/models/整体'))
 copy(REPO/'水解总装工程',Path('水解总装工程'))
 for name in ['model_data.js','building_style.js','building_measure.js','building_measure.css']:
  copy(REPO/'厂房外观模型/建筑'/name,Path('厂房外观模型/建筑')/name)
 copy(REPO/'README.md',Path('README.md'))
 # Freeze original script too; the runtime adaptation only redirects shared raw links.
 p=dest/'水解设备模型库/library_viewer.js';shutil.copy2(p,target/'原始_library_viewer.js')
 s=p.read_text().replace("const foundationSourceRoot = '../水解桥架工程/data/原始资料/设备基础/';","const foundationSourceRoot = '../../../../../水解桥架工程/data/原始资料/设备基础/';")
 s=s.replace("batch+'原始资料/'+encodeURIComponent(file)","'../../../../../水解设备模型库/示图建模_20260521/原始资料/'+encodeURIComponent(file)")
 p.write_text(s)
 raw={}
 for directory in [ROOT/'水解设备图纸',ROOT/'示图建模_20260521/原始资料',REPO/'水解桥架工程/data/原始资料/设备基础']:
  for p in directory.rglob('*'):
   if p.is_file():raw[p.relative_to(REPO).as_posix()]=sha(p)
 write(target/'冻结清单.json',{'version':'1.0','baseline_commit':'f17af0a','date':'2026-11-18','scope':'35组99项设备、当前类型模型和基础/支架、72条安装表和27条待定位记录、完整总装运行几何','files':files(dest),'original_source_hashes':original,'shared_raw_sources':raw,'runtime_adaptation':'仅调整原始资料下载相对路径；快照几何、参数和安装表逐字节保留。原library_viewer.js另存。'})
 (target/'index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>设备1.0 · 冻结原版</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{height:40px;display:flex;align-items:center;justify-content:space-between;padding:0 20px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 40px);border:0}</style><header><b>设备1.0 · 整改前冻结版本</b><span><a href="快照/水解总装工程/index.html">1.0原安装总装</a> · <a href="../2.0/index.html">设备2.0工作版</a></span></header><iframe src="快照/水解设备模型库/index.html" title="设备1.0"></iframe></html>')
 print('Equipment 1.0 frozen:',len(original),'runtime files; shared raw sources fingerprinted.')
def check_frozen():
 base=ROOT/'版本/1.0';d=json.loads((base/'冻结清单.json').read_text())
 for name,digest in d['files'].items():assert sha(base/'快照'/name)==digest,name
 for name,digest in d['shared_raw_sources'].items():assert sha(REPO/name)==digest,name
 extra=base/'补充归档清单.json'
 if extra.exists():
  for name,digest in json.loads(extra.read_text())['files'].items():assert sha(base/name)==digest,name
 print('Equipment 1.0 frozen geometry, placements and shared raw sources passed.')
def main():
 command=sys.argv[1] if len(sys.argv)>1 else 'check'
 if command=='freeze':freeze()
 elif command=='snapshot':write(INDEX,files(ROOT));print('Equipment SHA256 snapshot updated.')
 elif command=='check':
  assert json.loads(INDEX.read_text())==files(ROOT),'Equipment files changed; review then snapshot'
  check_frozen()
  import subprocess
  factory=['C41B01','C41B03','F41B01','F41B02','F41B05','F41B06','D41B02','L41B05']
  classes=['C41B02','C41B04','D41B01','L41B01','F41B03','L41B02','F41B04','L41B03']+factory
  selected=sys.argv[2:] or classes
  assert set(selected)<=set(classes),'Unknown equipment class'
  for key in selected:
   if key in factory:continue
   if (ROOT/('版本/2.0/'+key+'/设备/model_data.js')).exists():subprocess.run([sys.executable,str(ROOT/('tools/test_'+key.lower()+'.py'))],check=True)
  if any(key in factory for key in selected):subprocess.run([sys.executable,str(ROOT/'tools/test_factory_batch_v2.py'),*[key for key in selected if key in factory]],check=True)
 elif command=='build-c41b01':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/fix_c41b01_top.py')],check=True)
 elif command=='build-c41b02':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_c41b02_v2.py')],check=True)
 elif command=='build-c41b04':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_c41b04_v2.py'),'--frame-policy','layout'],check=True)
 elif command=='build-d41b01':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_d41b01_v2.py')],check=True)
 elif command=='build-l41b01':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_l41b01_v2.py')],check=True)
 elif command=='build-f41b03':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_f41b03_v2.py')],check=True)
 elif command=='build-l41b02':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_l41b02_v2.py')],check=True)
 elif command=='build-f41b04':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_f41b04_v2.py')],check=True)
 elif command=='build-l41b03':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_l41b03_v2.py')],check=True)
 elif command=='build-factory':
  import subprocess
  subprocess.run([sys.executable,str(ROOT/'tools/build_factory_batch_v2.py')],check=True)
 else:raise SystemExit('Use freeze | build-CLASS | build-factory | snapshot | check [CLASS ...]')
if __name__=='__main__':main()
