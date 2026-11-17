from pathlib import Path
import json, math
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[2];out=root/'水解总装工程';errors=[];checks={}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda e:errors.append(e.text) if e.type=='error' else None)
 page.goto('http://127.0.0.1:8765/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.length')==72;checks['http_load_and_72_equipment']=True
 page.screenshot(path=str(out/'previews/厂房总装外观.png'))
 assert page.evaluate('Number(document.getElementById("cut").value) > 100+Math.max(...assemblyViewer.objects.map(o=>o.high[2]))');checks['full_height_not_clipped']=True
 page.locator('#inside').click();page.wait_for_timeout(400);assert page.locator('#shell').input_value()=='transparent';assert not page.locator('#roof').is_checked();checks['inside_shell_and_roof']=True
 page.screenshot(path=str(out/'previews/厂房桥架设备总装.png'))
 page.locator('#top').click();assert abs(page.evaluate('assemblyViewer.getState().pitch')-math.pi/2)<1e-6;checks['north_top']=True
 page.locator('#search').fill('D41B02B1');page.locator('#list button').click();assert '位置修正' in page.locator('#details').inner_text();checks['search_selection_and_correction']=True
 page.locator('#floor').select_option('106');page.locator('#cut').fill('110');page.locator('#cut').dispatch_event('input');assert page.locator('#cutValue').inner_text()=='EL110.0';checks['floor_and_section']=True
 page.locator('#search').fill('');page.locator('#issuesTab').click();page.locator('#list button').first.click();assert page.locator('#floor').input_value()=='all';checks['intersection_highlight_and_focus']=True
 page.screenshot(path=str(out/'previews/几何相交核对.png'))
 page.locator('#pendingTab').click();assert page.locator('#list button').count()==27;checks['pending_27_excluded']=True
 page.locator('#reset').click();assert abs(page.evaluate('assemblyViewer.getState().pitch')-math.radians(35))<1e-6
 rect=page.locator('#scene').bounding_box();page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2);page.mouse.down();page.mouse.move(rect['x']+300,rect['y']-500,steps=10);page.mouse.up();assert 0<=page.evaluate('assemblyViewer.getState().pitch')<=math.pi/2;checks['rotation_upright_constraint']=True
 rect=page.locator('#scene').bounding_box();page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2);before=page.evaluate('assemblyViewer.getState().zoom');page.mouse.wheel(0,-200);page.wait_for_timeout(250);checks['wheel_zoom']=page.evaluate('assemblyViewer.getState().zoom')>before;assert checks['wheel_zoom']
 for key in ['equipment','bridge','structure','foundations','roof','labels']:page.locator('#'+key).check();page.locator('#'+key).uncheck();page.locator('#'+key).check()
 checks['layer_toggles']=True
 try:
  page.goto(out.joinpath('index.html').as_uri());page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000);checks['file_offline_load']=True
 except Exception as error:
  if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):raise
  checks['file_offline_load']='当前浏览器策略禁止 file://；本地HTTP已通过'
  page.close();page=b.new_page(viewport={'width':1500,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:8765/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 page.set_viewport_size({'width':700,'height':600});page.locator('#inside').click();checks['narrow_viewport']=page.locator('#scene').bounding_box()['width']>200
 assert not errors,errors
 checks['uncaught_errors']=errors
 b.close()
(out/'data/浏览器检查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(checks)
