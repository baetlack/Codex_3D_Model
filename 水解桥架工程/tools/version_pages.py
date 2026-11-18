"""Publish portable 1.0/2.0 entries without modifying any frozen 1.0 file."""
from pathlib import Path
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1]
def publish():
 archive=ROOT/'版本/1.0';frozen=json.loads((archive/'冻结清单.json').read_text())
 for name,digest in frozen['files'].items():assert hashlib.sha256((archive/name).read_bytes()).hexdigest()==digest,name
 target=ROOT/'版本/2.0'
 for name in ['index.html','project.json','viewer','models/整体','models/连接件库']:
  source=ROOT/name;dest=target/name
  if source.is_dir():shutil.copytree(source,dest,dirs_exist_ok=True)
  else:dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
 p=target/'index.html';p.write_text(p.read_text().replace('版本/1.0/浏览.html','../1.0/浏览.html').replace('版本/2.0/index.html','index.html').replace('href="README.md"','href="../../README.md"'))
 report=json.loads((ROOT/'models/整体/reports/2.0整改核对.json').read_text())
 files={p.relative_to(target).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(target.rglob('*')) if p.is_file() and p.name!='版本清单.json'}
 (target/'版本清单.json').write_text(json.dumps({'version':'2.0','date':'2026-11-18','files':files,'penetration_pairs':report['after_penetrations'],'baseline':'../1.0/冻结清单.json'},ensure_ascii=False,indent=2)+'\n')
 (ROOT/'版本/index.html').write_text('''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>桥架工程 · 版本对比</title><style>body{max-width:1000px;margin:60px auto;padding:20px;background:#101923;color:#dce8ef;font:16px sans-serif;line-height:1.9}a{color:#7cdce6}table{border-collapse:collapse;width:100%}td,th{padding:15px;border-bottom:1px solid #34475c;text-align:left}</style><h1>桥架工程 · 1.0 / 2.0</h1><p>两版均完整保留在桥架工程内，可独立浏览与下载。总装默认使用2.0。建筑与设备源模型不变。</p><table><tr><th>版本</th><th>内容</th><th>穿柱配对</th><th>打开</th></tr><tr><td>1.0 · 冻结</td><td>2026-11-18整改前原版</td><td>69组</td><td><a href="1.0/浏览.html">查看原版</a></td></tr><tr><td>2.0 · 当前</td><td>柱外轮廓约束，连接件与直段联动</td><td>0组</td><td><a href="2.0/index.html">查看整改版</a></td></tr></table><p>范围：112件桥架、120根柱；接触容差0.1mm。连接件形状、朝向、截面、标高保持。较小截面柱处允许留缝；不强行逐柱贴合。</p><p><a href="2.0/models/整体/reports/装配说明.html">整改说明</a> · <a href="2.0/models/整体/reports/2.0构件变更.csv">逐件位移与长度变化</a> · <a href="../../../水解总装工程/index.html">进入总装</a></p><p>校核基于当前建筑模型；上部柱截面仍待原结构图逐段复核。</p></html>'''.replace('../../../水解总装工程','../../水解总装工程'))
 print('1.0 frozen files verified; portable 2.0 and version comparison published.')
if __name__=='__main__':publish()
