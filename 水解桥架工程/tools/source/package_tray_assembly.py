from pathlib import Path
import zipfile,json
root=Path(__file__).parent;folder=root/'三层桥架模型'
assert json.loads((folder/'reports'/'verification.json').read_text(encoding='utf-8'))['status']=='passed'
assert json.loads((folder/'reports'/'browser_check.json').read_text())['status']=='passed'
archive=root/'三层桥架模型_v0.2.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as out:
 for file in folder.rglob('*'):
  if file.is_file():out.write(file,file.relative_to(root))
print(archive.name,archive.stat().st_size,'bytes')
