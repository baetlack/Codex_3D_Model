"""Current class, civil modes, frozen comparison and unchanged assembly UI."""
from pathlib import Path
from contextlib import contextmanager
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from urllib.parse import quote
import argparse,json,urllib.request,urllib.error,gzip
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent

@contextmanager
def server(root):
    class Quiet(SimpleHTTPRequestHandler):
        def log_message(self,*a):pass
    s=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(root)))
    t=Thread(target=s.serve_forever,daemon=True);t.start()
    try:yield f'http://127.0.0.1:{s.server_port}/'
    finally:s.shutdown();t.join();s.server_close()

def verify(equipment_base,assembly_base,output):
    output.mkdir(parents=True,exist_ok=True);errors=[];checks={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1560,'height':1050});page.set_default_timeout(120000)
        if equipment_base.startswith('https:'):
            # The isolated Chromium test profile does not inherit the managed
            # environment's CA bundle. Fetch public static assets with system TLS.
            def system_tls(route):
                try:r=urllib.request.urlopen(urllib.request.Request(route.request.url,headers={'Accept-Encoding':'identity'}),timeout=60)
                except urllib.error.HTTPError as e:r=e
                with r:
                    body=r.read()
                    if r.headers.get('Content-Encoding')=='gzip':body=gzip.decompress(body)
                    headers={k:v for k,v in r.headers.items() if k.lower() not in ['content-length','content-encoding','connection','transfer-encoding']}
                    route.fulfill(status=r.status,headers=headers,body=body)
            page.route('https://baetlack.github.io/**',system_tls)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:errors.append(r.url+' '+str(r.failure)))
        page.on('response',lambda r:errors.append(r.url+' '+str(r.status)) if r.status>=400 and 'favicon' not in r.url else None)
        page.goto(equipment_base+quote('水解设备模型库/?type=L41B02',safe='/?='))
        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length===20')
        assert page.evaluate('parts.some(p=>p.name==="支撑_底锚圈12孔")')
        assert page.locator('#foundation-mode').input_value()==''
        assert '不进入厂房总装' in page.locator('body').inner_text()
        page.screenshot(path=str(output/'预览_设备.png'));checks['new_model_and_default_equipment_only']=True
        for value,count in [('combined',94),('combined:L41B02',34),('L41B02',14),('L41B02-钢塔架',60),('',20)]:
            page.evaluate('async v=>{let e=document.getElementById("foundation-mode");e.value=v;await e.onchange();}',value)
            page.wait_for_function('(n)=>document.getElementById("preview-message").hidden && parts.length===n',arg=count)
            if value=='combined':page.screenshot(path=str(output/'预览_局部对照.png'))
        checks['five_equipment_foundation_frame_modes']=True
        page.goto(equipment_base+quote('水解设备模型库/版本/2.0/L41B02/修订对比.html',safe='/'))
        for frame in page.frames[1:]:frame.wait_for_function('window.compareReady===true')
        assert page.frames[1].evaluate('MODEL_PARTS.filter(p=>p.name==="支撑_底部托座").length')==4
        assert page.frames[2].evaluate('MODEL_PARTS.some(p=>p.name==="支撑_底锚圈12孔")')
        page.screenshot(path=str(output/'预览_新旧对照.png'));checks['frozen_old_model_and_new_comparison']=True
        page.goto(equipment_base+quote('水解设备模型库/?type=C41B02',safe='/?='))
        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>20')
        assert page.locator('#foundation-mode').input_value()=='combined';checks['accepted_class_default_mode_unchanged']=True
        page.goto(assembly_base+quote('水解总装工程/',safe='/'))
        page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=180000)
        assert page.evaluate('assemblyViewer.cfg.equipment.length')==72
        assert page.evaluate('assemblyViewer.cfg.unplaced.some(p=>p.id==="L41B02")')
        assert not page.evaluate('assemblyViewer.cfg.equipment.some(p=>p.id==="L41B02")')
        checks['assembly_remains_72_placed_and_L41B02_unplaced']=True
        browser.close()
    assert not errors,errors
    report={'status':'passed','checks':checks,'page_errors_or_failed_resources':errors}
    (output/'浏览器校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base');p.add_argument('--assembly-base');p.add_argument('--root',type=Path,default=REPO);p.add_argument('--output',type=Path,default=ROOT/'版本/2.0/L41B02');a=p.parse_args()
    if a.base:verify(a.base,a.assembly_base or a.base,a.output)
    else:
        with server(a.root) as base:verify(base,base,a.output)
