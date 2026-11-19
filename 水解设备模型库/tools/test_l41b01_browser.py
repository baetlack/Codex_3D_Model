"""L41B01 current/frozen viewers, downloads and provisional assembly transforms."""
from pathlib import Path
import atexit,json,os
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/L41B01'
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT.parent)));Thread(target=server.serve_forever,daemon=True).start();atexit.register(server.shutdown)
URL=os.environ.get('ASSEMBLY_TEST_URL',f'http://127.0.0.1:{server.server_port}');errors=[];failed=[];checks={}
expected=len(json.loads((OUT/'设备/model_data.js').read_text().split('=',1)[1].strip().rstrip(';')))
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1560,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:failed.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
 page.goto(URL+'/水解设备模型库/?type=L41B01');page.wait_for_function('rowTag==="L41B01A-F" && document.getElementById("preview-message").hidden')
 assert page.locator('#list button').count()==35 and page.evaluate('parts.length')==expected
 assert page.locator('#foundation-mode').is_hidden()
 assert '不与旧圆台组合' in page.locator('#detail').inner_text() and '承托EL' in page.locator('#detail').inner_text()
 assert page.evaluate('parts.some(p=>p.name==="本体_锥斗") && parts.some(p=>p.name==="接口_c_密封面")')
 page.screenshot(path=str(OUT/'预览_设备.png'));checks['current_new_cone_three_ears_no_round_base_combination']=True
 page.locator('#top').click();page.wait_for_timeout(120);page.screenshot(path=str(OUT/'预览_俯视.png'))
 assert page.evaluate('parts.filter(p=>p.name.startsWith("接口_顶盖法兰_")).length')==2
 page.locator('#showDim').uncheck();page.locator('#group').select_option(label='过滤器托耳');page.locator('#iso').click();page.wait_for_timeout(120);page.screenshot(path=str(OUT/'预览_三耳.png'))
 assert page.evaluate('partGroups.get("过滤器托耳").filter(p=>p.name.includes("承托底板")).length')==3
 checks['top_ports_and_separate_three_ear_parts']=True
 for label,magic in [('设备 GLB',b'glTF')]:
  href=page.get_by_role('link',name=label,exact=True).get_attribute('href');absolute=page.evaluate('(href)=>new URL(href,location.href).href',href);r=page.request.get(absolute);assert r.ok and r.body()[:4]==magic
 checks['current_download_and_pending_labels']=True
 page.goto(URL+'/水解设备模型库/版本/2.0/L41B01/修订对比.html')
 for f in page.frames[1:]:f.wait_for_function('window.compareReady===true')
 assert len(page.frames)==3
 page.screenshot(path=str(OUT/'预览_新旧对照.png'))
 for mode in ['top','ears','bottom']:
  page.locator(f'button[data-view="{mode}"]').click()
  for f in page.frames[1:]:f.wait_for_function('(mode)=>window.previewMode===mode',arg=mode)
 checks['frozen_1_0_and_new_comparison']=True
 page.goto(URL+'/水解设备模型库/版本/1.0/快照/水解设备模型库/');page.wait_for_function('document.querySelectorAll("#list button").length===35');page.locator('#search').fill('L41B01');page.locator('#list button').click();page.wait_for_function('rowTag==="L41B01A-F" && document.getElementById("preview-message").hidden')
 assert page.locator('#foundation-mode').is_visible() and page.locator('#foundation-mode option[value="combined"]').count()==1
 checks['frozen_round_base_preview_preserved']=True
 page.goto(URL+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.filter(p=>p.asset==="L41B01"&&p.equipment_version==="2.0-L41B01-01"&&p.z_status==="待核").length')==6
 assert page.evaluate('assemblyViewer.cfg.equipment.filter(p=>p.asset==="L41B01"&&p.mirror_y).length')==3
 assert page.evaluate('assemblyViewer.cfg.foundations.some(p=>p.asset==="foundation-L41B01")') is False
 page.locator('#inside').click();page.locator('#shell').select_option('hidden');page.locator('#search').fill('L41B01A');page.locator('#list button').first.click();page.locator('#focus').click();page.locator('#isolate').click();page.wait_for_timeout(160);page.screenshot(path=str(OUT/'预览_总装定位.png'))
 assert '待核' in page.locator('#details').inner_text()
 checks['six_current_instances_three_reflections_no_invented_supports']=True
 assert not errors,errors;assert not failed,failed
 browser.close()
report={'status':'passed','checks':checks,'page_errors':errors,'failed_resources':failed}
(OUT/'浏览器检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
