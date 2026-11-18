from pathlib import Path
import json, math, os
from playwright.sync_api import sync_playwright
base_url=os.environ.get('ASSEMBLY_TEST_URL','http://127.0.0.1:8765')
root=Path(__file__).resolve().parents[2];out=root/'水解总装工程';errors=[];checks={}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda e:errors.append(e.text) if e.type=='error' else None)
 page.goto(base_url+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.length')==72;checks['http_load_and_72_equipment']=True
 page.screenshot(path=str(out/'previews/厂房总装外观.png'))
 assert page.evaluate('Number(document.getElementById("cut").value) > 100+Math.max(...assemblyViewer.objects.map(o=>o.high[2]))');checks['full_height_not_clipped']=True
 page.locator('#inside').click();page.wait_for_timeout(400);assert page.locator('#shell').input_value()=='transparent';assert not page.locator('#roof').is_checked();checks['inside_shell_and_roof']=True
 page.screenshot(path=str(out/'previews/厂房桥架设备总装.png'))
 assert page.evaluate('assemblyViewer.objects.filter(o=>o.kind==="structure").length')==88
 assert page.evaluate('assemblyViewer.objects.filter(o=>o.kind==="floor").length')==4
 page.locator('#floorAlpha').fill('3');page.locator('#floorAlpha').dispatch_event('input');assert page.locator('#floorAlphaValue').inner_text()=='3%'
 page.locator('#floors').uncheck();page.locator('#floors').check();page.locator('#floorAlpha').fill('7');page.locator('#floorAlpha').dispatch_event('input')
 checks['88_columns_4_faint_floors_and_opacity']=True
 assert page.evaluate('assemblyViewer.objects.find(o=>o.id==="D41B02D1").mirror')==-1
 checks['dxf_mirror_instancing']=True
 page.locator('#top').click();assert abs(page.evaluate('assemblyViewer.getState().pitch')-math.pi/2)<1e-6;checks['north_top']=True
 page.locator('#search').fill('D41B02B1');page.locator('#list button').click();assert '位置修正' in page.locator('#details').inner_text();checks['search_selection_and_correction']=True
 page.locator('#floor').select_option('106');page.locator('#cut').fill('110');page.locator('#cut').dispatch_event('input');assert page.locator('#cutValue').inner_text()=='EL110.0';checks['floor_and_section']=True
 page.locator('#search').fill('');page.locator('#issuesTab').click()
 assert page.locator('#list button').count()==0;checks['v2_zero_primary_column_penetrations']=True
 page.screenshot(path=str(out/'previews/几何相交核对.png'))
 page.locator('#issueScope').select_option('bridge-contact');assert page.locator('#list button').count()==18
 page.locator('#list button').first.click();assert '表面接触（正常）' in page.locator('#details').inner_text()
 page.screenshot(path=str(out/'previews/正常表面接触.png'))
 assert page.locator('#isolate').get_attribute('aria-pressed')=='true';page.locator('#isolate').click();page.locator('#isolate').click();checks['pair_isolation']=True
 checks['0_penetrations_18_normal_contacts']=True
 page.locator('#pendingTab').click();assert page.locator('#list button').count()==27;checks['pending_27_excluded']=True
 page.locator('#reset').click();assert abs(page.evaluate('assemblyViewer.getState().pitch')-math.radians(3))<1e-6
 rect=page.locator('#scene').bounding_box();page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2);page.mouse.down();page.mouse.move(rect['x']+300,rect['y']-500,steps=10);page.mouse.up();assert 0<=page.evaluate('assemblyViewer.getState().pitch')<=math.pi/2;checks['rotation_upright_constraint']=True
 rect=page.locator('#scene').bounding_box();page.mouse.move(rect['x']+rect['width']/2,rect['y']+rect['height']/2);before=page.evaluate('assemblyViewer.getState().zoom');page.mouse.wheel(0,-200);page.wait_for_timeout(250);checks['wheel_zoom']=page.evaluate('assemblyViewer.getState().zoom')>before;assert checks['wheel_zoom']
 for key in ['equipment','bridge','structure','foundations','roof','labels','floors']:page.locator('#'+key).check();page.locator('#'+key).uncheck();page.locator('#'+key).check()
 checks['layer_toggles']=True
 try:
  page.goto(out.joinpath('index.html').as_uri());page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000);checks['file_offline_load']=True
 except Exception as error:
  if 'ERR_BLOCKED_BY_ADMINISTRATOR' not in str(error):raise
  checks['file_offline_load']='当前浏览器策略禁止 file://；本地HTTP已通过'
  page.close();page=b.new_page(viewport={'width':1500,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto(base_url+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 page.set_viewport_size({'width':700,'height':600});page.locator('#inside').click();checks['narrow_viewport']=page.locator('#scene').bounding_box()['width']>200
 assert not errors,errors
 checks['uncaught_errors']=errors
 b.close()
(out/'data/浏览器检查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(checks)
