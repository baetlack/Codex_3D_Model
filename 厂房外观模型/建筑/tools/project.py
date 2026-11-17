from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];INDEX=ROOT/'data/建筑文件清单.json'
def hashes():return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=INDEX and '__pycache__' not in p.parts}
if __name__=='__main__':
 command=sys.argv[1] if len(sys.argv)>1 else 'check'
 if command=='build':subprocess.run([sys.executable,str(ROOT/'tools/build_building.py')],check=True)
 if command in ('snapshot','build'):INDEX.write_text(json.dumps(hashes(),ensure_ascii=False,indent=2)+'\n');print('建筑SHA256快照已更新')
 elif command=='check':
  assert json.loads(INDEX.read_text())==hashes(),'建筑文件快照不一致'
  metadata=json.loads((ROOT/'building.json').read_text())
  for name,digest in metadata['source_files'].items():assert hashlib.sha256((ROOT/'原始资料'/name).read_bytes()).hexdigest()==digest,name
  print('建筑文件、原始图纸指纹及共享网格完整性通过')
 else:raise SystemExit('Use build | check | snapshot')
