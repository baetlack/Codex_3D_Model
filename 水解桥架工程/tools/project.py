"""Portable maintenance entry. Execute from any directory; all paths are project-relative."""
from pathlib import Path
import json, sys, tempfile, shutil, subprocess, hashlib

ROOT=Path(__file__).resolve().parent.parent
CONFIG=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))
P={k:ROOT/v for k,v in CONFIG['paths'].items()}
INDEX=ROOT/'data/文件清单.json'

def hashes():
    return {p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in sorted(ROOT.rglob('*')) if p.is_file() and p!=INDEX
            and '__pycache__' not in p.parts and not any(s.startswith(('.assembly-','.build-')) for s in p.parts)}

def snapshot():
    INDEX.write_text(json.dumps({'algorithm':'SHA256','files':hashes()},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def stage(work):
    shutil.copytree(ROOT/'tools/source',work,dirs_exist_ok=True)
    shutil.copytree(P['extracted'],work,dirs_exist_ok=True)
    shutil.copytree(P['raw']/'连接件',work/'连接件')
    shutil.copytree(P['fitting_library'],work/'连接件模型库')
    shutil.copytree(P['assembly'],work/'三层桥架模型')

def run(work,name):
    subprocess.run([sys.executable,str(work/name)],cwd=work,check=True)

def refresh_entry():
    import re
    html=(P['assembly']/'index.html').read_text(encoding='utf-8')
    html=html.replace('src="viewer_data.js"','src="models/整体/viewer_data.js"').replace('src="viewer.js"','src="viewer/viewer.js"')
    html=html.replace('../../viewer/','viewer/')
    html=re.sub(r'href="models/','href="models/整体/models/',html)
    for prefix in ['previews/','reports/']:
        html=html.replace('src="'+prefix,'src="models/整体/'+prefix).replace('href="'+prefix,'href="models/整体/'+prefix)
    html=html.replace('当前为装配初版。直段端点已适配连接件接口，未新增层间连接线路。','三层桥架工程；参数来源、装配规则与当前边界见工程说明。')
    html=html.replace('<span class="version">','<a href="models/连接件库/index.html">连接件库</a> · <a href="README.md">工程说明</a> · <span class="version">')
    if CONFIG.get('active_version')=='2.0':
        html=html.replace('整体装配预览 v0.2','桥架 2.0 · 柱面接触整改').replace('<span class="version">','<a href="版本/1.0/浏览.html">1.0 原版</a> · <a href="版本/2.0/index.html">2.0 整改版</a> · <span class="version">')
    html='\n'.join(line.rstrip() for line in html.splitlines())+'\n'
    (ROOT/'index.html').write_text(html,encoding='utf-8')
    js=(P['assembly']/'viewer.js').read_text(encoding='utf-8').replace('href="reports/装配说明.html"','href="models/整体/reports/装配说明.html"')
    (ROOT/'viewer/viewer.js').write_text(js,encoding='utf-8')

def main():
    command=sys.argv[1] if len(sys.argv)>1 else 'check'
    if command=='versions':
        run(ROOT/'tools','version_pages.py'); return
    if command=='snapshot': snapshot(); print('SHA256 snapshot updated.'); return
    if command=='build-agitator':
        run(ROOT/'tools/source','build_annotated_agitator.py')
        return
    if command=='build-equipment-foundations':
        run(ROOT/'tools/source','build_equipment_foundations.py')
        return
    if command=='check-v2':
        run(ROOT/'tools/source','verify_columns_v2.py'); return
    if command not in ['check','build','build-library']: raise SystemExit('Use check | build | build-library | build-agitator | build-equipment-foundations | snapshot')
    if command=='check':
        expected=json.loads(INDEX.read_text(encoding='utf-8'))['files'];actual=hashes()
        changed=[name for name in sorted(set(expected)|set(actual)) if expected.get(name)!=actual.get(name)]
        if changed: raise SystemExit('Changed / missing / new files; review before snapshot:\n'+'\n'.join(changed))
    with tempfile.TemporaryDirectory(prefix='.build-',dir=ROOT) as temp:
        assert Path(temp).resolve().parent==ROOT.resolve()
        work=Path(temp);stage(work)
        if command=='build-library': run(work,'build_fitting_library.py')
        run(work,'verify_fitting_library.py')
        if command.startswith('build'):
            if CONFIG.get('active_version')=='2.0':
                subprocess.run([sys.executable,str(ROOT/'tools/source/rectify_columns_v2.py'),'--output',str(work/'三层桥架模型')],check=True)
            else: run(work,'build_tray_assembly.py')
            run(work,'render_riser_dimensions.py')
        run(work,'verify_tray_assembly.py')
        if command.startswith('build'):
            if command=='build-library': shutil.copytree(work/'连接件模型库',P['fitting_library'],dirs_exist_ok=True)
            shutil.copytree(work/'三层桥架模型',P['assembly'],dirs_exist_ok=True)
            refresh_entry()
            # Browser evidence belongs to the prior baseline until explicitly rerun.
            browser=P['assembly']/'reports/browser_check.json'
            if browser.exists():
                evidence=json.loads(browser.read_text(encoding='utf-8'))
                evidence['current_build_status']='not_rerun_after_rebuild'
                browser.write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
            if CONFIG.get('active_version')=='2.0': run(ROOT/'tools','version_pages.py')
            print('Build complete. Update provenance/version; rerun browser review, then snapshot.')
    if CONFIG.get('active_version')=='2.0' and command=='check': run(ROOT/'tools/source','verify_columns_v2.py')
    print('Geometry and interfaces passed. '+('File hashes passed.' if command=='check' else ''))

if __name__=='__main__': main()
