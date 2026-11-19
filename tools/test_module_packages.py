"""Verify ZIP contents, source hashes and actual extracted module viewers."""
from pathlib import Path
import argparse, hashlib, json, subprocess, tempfile, zipfile
from urllib.parse import quote, unquote, urlsplit
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from package_modules import MODULES, ROOT, selected_files


@contextmanager
def local_server(directory):
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, *args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(directory)))
    thread=Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield f'http://127.0.0.1:{server.server_port}'
    finally:server.shutdown();server.server_close();thread.join()


def verify(output, browser_checks=False):
    published=json.loads((output/'packages.json').read_text())
    tracked=[p for p in subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0') if p]
    report={'source_commit':published['source_commit'],'packages':[],'errors':[]}
    with tempfile.TemporaryDirectory(prefix='hydrolysis-packages-') as temporary:
        extracted={}
        for asset in published['packages']:
            key=asset['module'];module=MODULES[key];archive=output/asset['asset']
            assert hashlib.sha256(archive.read_bytes()).hexdigest()==asset['sha256']
            dest=Path(temporary)/key;extracted[key]=dest
            with zipfile.ZipFile(archive) as z:
                manifest=json.loads(z.read('下载包清单.json'));names=set(z.namelist())
                assert len(names)==len(z.namelist()),'duplicate ZIP member'
                assert set(manifest['source_files_sha256'])==set(selected_files(module,tracked))
                assert manifest['source_commit']==published['source_commit']
                for name,digest in manifest['source_files_sha256'].items():
                    assert hashlib.sha256(z.read(name)).hexdigest()==digest,name
                    assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
                for name in names:assert dest.resolve() in (dest/name).resolve().parents,name
                assert module['entry'] in names and 'index.html' in names
                assert 'README.md' in names
                if key=='bridge':assert not any(n.startswith('水解桥架工程/models/设备/') for n in names)
                if key in ('equipment','assembly'):
                    for name in ['水解桥架工程/models/设备/设备基础_20261106/foundation_data.js','水解设备模型库/版本/2.0/C41B02/设备/C41B02.glb','水解设备模型库/版本/1.0/冻结清单.json']:assert name in names,name
                z.extractall(dest)
            report['packages'].append({'module':key,'source_files':len(manifest['source_files_sha256']),'source_hashes_and_extraction':'passed'})
            print(f'{key}: ZIP, source hashes, dependencies and extraction passed',flush=True)
        if browser_checks:
            with local_server(temporary) as base_url:browser_test(extracted,output,report,base_url)
    report['status']='passed'
    (output/'package-check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print('All module package checks passed.',flush=True)


def browser_test(extracted,output,report,base_url):
    from playwright.sync_api import sync_playwright
    errors=report['errors'];checks={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1500,'height':1000})
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:errors.append(r.url+' '+str(r.failure)))
        page.on('response',lambda r:errors.append(r.url+' '+str(r.status)) if r.status>=400 and 'favicon' not in r.url else None)
        def visit(key,entry=None):page.goto(base_url+'/'+key+'/'+quote(entry or MODULES[key]['entry'],safe='/'))
        def downloads():
            for link in page.locator('a[download]').all():
                absolute=page.evaluate('(href)=>new URL(href,location.href).href',link.get_attribute('href'));parsed=urlsplit(absolute)
                if absolute.startswith(base_url+'/'):
                    target=next(iter(extracted.values())).parent/unquote(parsed.path).lstrip('/');assert target.is_file(),str(target)
                    if target.suffix=='.glb':assert target.read_bytes()[:4]==b'glTF'
        visit('bridge')
        page.wait_for_function('window.ASSEMBLY?.parts.length===112 && document.querySelectorAll("#list button").length===48')
        downloads();page.screenshot(path=str(output/'preview-bridge.png'))
        for version in ['1.0','2.0']:
            visit('bridge',f'水解桥架工程/版本/{version}/index.html');page.wait_for_function('window.ASSEMBLY?.parts.length===112');downloads()
        visit('bridge','水解桥架工程/models/连接件库/index.html');page.wait_for_function('document.querySelectorAll("#list button").length===47')
        checks['bridge_current_frozen_versions_112_parts_47_fittings_downloads']=True
        print('bridge: extracted HTTP viewer and versions passed',flush=True)
        visit('building');page.wait_for_function('!!window.buildingViewer && document.getElementById("loading").hidden')
        page.locator('#inside').click();page.locator('#top').click()
        assert page.get_by_role('button',name='测量尺寸').count()
        page.screenshot(path=str(output/'preview-building.png'));checks['building_viewer_and_measurement']=True
        print('building: extracted HTTP viewer and measurement control passed',flush=True)
        visit('equipment');page.wait_for_function('document.querySelectorAll("#list button").length===35 && document.getElementById("preview-message").hidden')
        for i in range(35):
            page.locator('#list button').nth(i).click();page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0');downloads()
            modes=page.locator('#foundation-mode option').evaluate_all('(els)=>els.map(e=>e.value)') if page.locator('#foundation-mode').is_visible() else []
            for value in modes:
                page.evaluate('async(value)=>{const mode=document.getElementById("foundation-mode");mode.value=value;await mode.onchange();}',value)
                page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0')
            if i%10==0:print(f'equipment: {i+1}/35 groups passed',flush=True)
        page.locator('#search').fill('C41B02');page.locator('#list button').click();page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0');page.screenshot(path=str(output/'preview-equipment.png'))
        visit('equipment','水解设备模型库/版本/1.0/快照/水解设备模型库/index.html');page.wait_for_function('document.querySelectorAll("#list button").length===35 && document.getElementById("preview-message").hidden')
        checks['equipment_all_35_groups_foundations_downloads_frozen_viewer']=True
        print('equipment: extracted HTTP all groups and foundations passed',flush=True)
        visit('assembly');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
        assert page.evaluate('assemblyViewer.cfg.equipment.length')==72
        assert page.evaluate('assemblyViewer.cfg.unplaced.length')==27
        expected=json.loads((ROOT/'水解设备模型库/project.json').read_text())['revisions']['C41B02']['version']
        assert page.evaluate('(version)=>assemblyViewer.cfg.equipment.filter(e=>e.asset==="C41B02"&&e.equipment_version===version).length',expected)==5
        page.locator('#inside').click();downloads();page.screenshot(path=str(output/'preview-assembly.png'))
        checks['assembly_72_placed_27_unplaced_5_current_C41B02']=True
        print('assembly: extracted HTTP complete dependency loading passed',flush=True)
        browser.close()
    assert not errors,errors
    report['browser']=checks


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--browser',action='store_true');args=parser.parse_args();verify(args.output,args.browser)
