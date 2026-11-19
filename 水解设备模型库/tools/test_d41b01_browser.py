"""Exercise standalone/pair support, downloads, frozen version and total D41B01."""
from pathlib import Path
import json,os
import atexit
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from threading import Thread
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/D41B01'
if 'ASSEMBLY_TEST_URL' not in os.environ:
 class QuietHandler(SimpleHTTPRequestHandler):
  def log_message(self,*args):pass
 server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT.parent)))
 Thread(target=server.serve_forever,daemon=True).start();atexit.register(server.shutdown)
URL=os.environ.get('ASSEMBLY_TEST_URL',f'http://127.0.0.1:{server.server_port}' if 'server' in globals() else '');errors=[];failed=[];checks={}
def mesh(path):return json.loads(path.read_text().split('=',1)[1].strip().rstrip(';'))
expected=len(mesh(OUT/'设备/model_data.js'));steel=len(mesh(OUT/'支架/model_data.js'))
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1560,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:failed.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
 page.goto(URL+'/水解设备模型库/?type=D41B01');page.wait_for_function('rowTag==="D41B01A-E" && document.getElementById("preview-message").hidden')
 assert page.locator('#list button').count()==35 and page.evaluate('parts.length')==2*expected+steel
 assert 'A支架及标高适用性待核' in page.locator('#detail').inner_text()
 page.screenshot(path=str(OUT/'预览_双槽支架.png'));checks['pair_preview_2600_and_A_support_pending']=True
 page.locator('#foundation-mode').select_option('');page.wait_for_function(f'parts.length==={expected}');page.wait_for_timeout(150)
 page.screenshot(path=str(OUT/'预览_设备.png'))
 page.locator('#top').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_盖面.png'))
 assert page.evaluate('parts.filter(p=>p.name.startsWith("接口_顶盖法兰")).length')==6
 page.locator('#group').select_option(label='晶种槽托耳');page.locator('#iso').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_托耳.png'))
 checks['seven_top_positions_and_separate_four_ear_structure']=True
 page.locator('#foundation-mode').select_option('D41B01');page.wait_for_function(f'parts.length==={steel}');checks['support_independent']=True
 for label,magic in [('设备 GLB',b'glTF'),('支架 GLB',b'glTF')]:
  href=page.get_by_role('link',name=label,exact=True).get_attribute('href');absolute=page.evaluate('(href)=>new URL(href,location.href).href',href);r=page.request.get(absolute);assert r.ok and r.body()[:4]==magic
 checks['current_equipment_and_support_downloads']=True
 page.goto(URL+'/水解设备模型库/版本/2.0/D41B01/修订对比.html')
 for f in page.frames[1:]:f.wait_for_function('window.compareReady===true')
 assert len(page.frames)==3
 page.screenshot(path=str(OUT/'预览_新旧对照.png'))
 for mode in ['top','lugs']:page.locator(f'button[data-view="{mode}"]').click();page.wait_for_timeout(100)
 checks['old_1_0_and_new_at_common_bearing_datum']=True
 page.goto(URL+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.filter(p=>p.asset==="D41B01"&&p.equipment_version==="2.0-D41B01-01"&&p.position_mm[2]===11000).length')==5
 assert page.evaluate('assemblyViewer.cfg.foundations.filter(p=>p.asset==="foundation-D41B01").length')==2
 assert page.evaluate('assemblyViewer.cfg.equipment.find(p=>p.id==="D41B01A").z_status')=='待核'
 page.locator('#inside').click();page.locator('#search').fill('D41B01B');page.locator('#list button').first.click();page.locator('#focus').click();page.wait_for_timeout(200);page.screenshot(path=str(OUT/'预览_总装定位.png'))
 checks['total_five_devices_two_pairs_no_A_support']=True
 assert not errors,errors;assert not failed,failed
 browser.close()
report={'status':'passed','checks':checks,'page_errors':errors,'failed_resources':failed}
(OUT/'浏览器检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
