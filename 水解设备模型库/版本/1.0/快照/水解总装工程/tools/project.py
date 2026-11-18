"""Rebuild/check assembly artifacts and source fingerprints."""
from pathlib import Path
import json,hashlib,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];INDEX=ROOT/'data/文件清单.json'
def hashes():
 return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=INDEX and '__pycache__' not in p.parts}
def run(name):subprocess.run([sys.executable,str(ROOT/'tools'/name)],check=True)
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'check'
 if command=='build':run('build_assembly.py');run('check_assembly.py')
 if command in ('snapshot','build'):INDEX.write_text(json.dumps(hashes(),ensure_ascii=False,indent=2)+'\n');print('总装 SHA256 快照已更新')
 elif command=='check':
  assert json.loads(INDEX.read_text())==hashes(),'总装快照不一致，核对变更后重建'
  sources=json.loads((ROOT/'data/来源与哈希.json').read_text())['sources']
  for p,h in sources.items():assert hashlib.sha256((ROOT.parent/p).read_bytes()).hexdigest()==h,p
  cfg=json.loads((ROOT/'assembly.json').read_text());data=json.loads((ROOT/'data/assembly.js').read_text().split('=',1)[1].strip().rstrip(';'));assert cfg==data
  assert len(set(p['id'] for p in cfg['equipment']))==len(cfg['equipment'])
  assert not set(p['id'] for p in cfg['equipment'])&set(p['id'] for p in cfg['unplaced'])
  assert len(cfg['equipment'])+len(cfg['unplaced'])==99
  for p in cfg['assets'].values():assert (ROOT.parent/p['source']).is_file(),p
  print('总装文件、源文件指纹、99台设备完整性与模型引用检查通过')
 else:raise SystemExit('Use build | check | snapshot')
