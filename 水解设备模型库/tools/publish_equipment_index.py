"""Render the common version index from the revision registry, retaining every class."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[1]
def publish():
    project=json.loads((ROOT/'project.json').read_text());revisions=project['revisions'];last=next(reversed(revisions))
    style='body{max-width:1080px;margin:35px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.8}a{color:#7cdce6}table{width:100%;border-collapse:collapse}td,th{border-bottom:1px solid #344957;padding:12px;text-align:left}'
    entries={**revisions,**project.get('reviews',{})}
    rows=''.join(f'<tr><td>{k}</td><td>{v["version"]}</td><td>{html.escape(v["status"])}</td><td><a href="2.0/{k}/index.html">查看模型</a> · <a href="2.0/{k}/整改说明.html">来源与待核</a></td></tr>' for k,v in entries.items())
    coverage='35组99项均已有首轮记录；' if project['counts'].get('reviewed_items')==99 else '35组99项；'
    follow='下一类：'+project['next_class']+'。' if project.get('next_class') else '首轮无待开始类别；缺失资料、型号/型式和安装未决项继续保留，不能把首轮覆盖当作制造或安装全部确认。'
    (ROOT/'版本/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>设备版本与逐类整改</title><style>'+style+'</style><h1>设备模块 · 版本与进度</h1><p>'+coverage+str(project['counts']['revised_items'])+'项进入逐类2.0，其余'+str(project['counts']['other_items_unchanged'])+'项保留原几何。<a href="1.0/index.html">设备1.0冻结原版</a> · <a href="../../水解总装工程/index.html">当前总装</a></p><table><tr><th>位号</th><th>版本/复核记录</th><th>处置与限制</th><th>入口</th></tr>'+rows+'</table><p>'+follow+'</p></html>')
    (ROOT/'版本/2.0/index.html').write_text('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>设备2.0逐类整改</title><style>body{margin:0;background:#101923;color:#dce8ef;font:14px sans-serif}header{padding:10px 18px}a{color:#7cdce6}iframe{width:100%;height:calc(100vh - 44px);border:0}</style><header>设备2.0 · <a href="../index.html">全部已整改类型与版本</a> · <a href="'+last+'/整改说明.html">本次整改说明</a></header><iframe title="设备2.0" src="../../index.html?type='+last+'"></iframe></html>')
if __name__=='__main__':publish()
