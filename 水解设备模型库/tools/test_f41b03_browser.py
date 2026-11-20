"""F41B03 standalone models, non-bearing diagnostics, history and total scene."""
from pathlib import Path
import atexit,json
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/F41B03'
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT.parent)));Thread(target=server.serve_forever,daemon=True).start();atexit.register(server.shutdown)
URL=f'http://127.0.0.1:{server.server_port}';errors=[];failed=[];checks={}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1560,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:failed.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
 page.goto(URL+'/水解设备模型库/?type=F41B03');page.wait_for_function('rowTag==="F41B03" && document.getElementById("preview-message").hidden')
 assert page.locator('#list button').count()==35 and page.evaluate('parts.length')==5
 assert page.locator('#foundation-mode option[value="combined"]').count()==0
 assert '仅Ø1000×1000直筒段' in page.locator('#detail').inner_text() and '8.75' in page.locator('#detail').inner_text()
 page.screenshot(path=str(OUT/'预览_设备.png'));checks['five_parts_no_unsupported_end_rings_and_scope_label']=True
 page.locator('#top').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_俯视.png'))
 page.locator('#showDim').uncheck();page.locator('#group').select_option(label='分汽器托耳');page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_四孔.png'))
 assert page.evaluate('partGroups.get("分汽器托耳").length')==4
 page.locator('#foundation-mode').select_option('F41B03');page.wait_for_function('parts.length===8');checks['independent_four_pedestals_no_installation_combination']=True
 for label in ['设备 GLB','基础 GLB']:
  href=page.get_by_role('link',name=label,exact=True).get_attribute('href');absolute=page.evaluate('(href)=>new URL(href,location.href).href',href);r=page.request.get(absolute);assert r.ok and r.body()[:4]==b'glTF'
 checks['current_equipment_and_preserved_foundation_downloads']=True
 page.goto(URL+'/水解设备模型库/版本/2.0/F41B03/支承对照.html');page.wait_for_function('window.diagReady===true')
 assert page.evaluate('diagnosticParts')==13 and '不是厂房安装方案' in page.locator('.pending').inner_text()
 page.screenshot(path=str(OUT/'预览_支承俯视.png'));page.locator('button[data-view="east"]').click();page.wait_for_function('diagnosticMode==="east" && diagnosticParts===3');page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_支承局部.png'))
 page.locator('button[data-view="iso"]').click();page.wait_for_function('diagnosticMode==="iso"');checks['diagnostic_overlay_and_local_gap_are_explicitly_not_installation']=True
 page.goto(URL+'/水解设备模型库/版本/2.0/F41B03/修订对比.html')
 for f in page.frames[1:]:f.wait_for_function('window.compareReady===true')
 assert len(page.frames)==3 and page.frames[1].evaluate('MODEL_PARTS.filter(p=>p.name==="本体_端缘").length')==2 and page.frames[2].evaluate('MODEL_PARTS.filter(p=>p.name==="本体_端缘").length')==0
 page.screenshot(path=str(OUT/'预览_新旧对照.png'));page.locator('button[data-view="top"]').click()
 for f in page.frames[1:]:f.wait_for_function('window.previewMode==="top"')
 checks['frozen_two_rings_vs_corrected_hole_plan']=True
 page.goto(URL+'/水解设备模型库/版本/1.0/快照/水解设备模型库/');page.wait_for_function('document.querySelectorAll("#list button").length===35');page.locator('#search').fill('F41B03');page.locator('#list button').click();page.wait_for_function('rowTag==="F41B03" && document.getElementById("preview-message").hidden')
 assert page.evaluate('parts.length')==7;checks['full_frozen_library_geometry_preserved']=True
 page.goto(URL+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.find(p=>p.id==="F41B03").equipment_version')=='2.0-F41B03-01'
 assert page.evaluate('assemblyViewer.cfg.equipment.find(p=>p.id==="F41B03").z_status')=='待核'
 assert not page.evaluate('assemblyViewer.cfg.foundations.some(p=>p.asset==="foundation-F41B03")')
 page.locator('#inside').click();page.locator('#search').fill('F41B03');page.locator('#list button').first.click();page.locator('#focus').click();page.locator('#isolate').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_总装待核.png'))
 checks['assembly_keeps_provisional_position_and_no_new_foundation']=True
 assert not errors,errors;assert not failed,failed
 browser.close()
report={'status':'passed','checks':checks,'page_errors':errors,'failed_resources':failed}
(OUT/'浏览器检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
