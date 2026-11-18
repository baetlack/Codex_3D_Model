from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];BASE=os.environ.get('BUILDING_TEST_URL','http://127.0.0.1:8000');checks={};errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/厂房外观模型/建筑/');page.wait_for_function('window.buildingViewer')
 assert page.evaluate('BUILDING_MODEL.metadata.holes.filter(h=>h.type==="floor_opening").length')==14
 for floor in [2,3]:
  page.locator('#focus').select_option('flooropens'+str(floor))
  assert page.evaluate('buildingViewer.getVisible().some(p=>p.name.startsWith("FLOOROPEN-'+str(floor)+'-"))')
  assert page.evaluate('buildingViewer.getVisible().filter(p=>p.kind==="floor").length')==1
  page.screenshot(path=str(ROOT/f'previews/{"二" if floor==2 else "三"}层楼板新增开孔.png'))
 checks['new_opening_focus_views_2_and_3']=True
 page.evaluate('buildingViewer.viewer.view(-Math.PI/3,.85,"三层楼板开孔")')
 page.screenshot(path=str(ROOT/'previews/三层楼板开孔立体.png'))
 # A ray through the center of the 1000x2000 opening must not hit a painted slab.
 page.locator('#focus').select_option('flooropens3');page.locator('#measureToggle').click();page.locator('#measureMode').select_option('bounds')
 point=page.evaluate('buildingViewer.measure.project([500,30100,12000])');box=page.locator('#view').bounding_box();page.mouse.click(box['x']+point[0],box['y']+point[1])
 assert page.evaluate('buildingViewer.measure.getState().info') is None
 checks['actual_ray_through_small_rectangular_opening']=True
 page.goto(BASE+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('ASSEMBLY_BUILDING===BUILDING_MODEL.parts')
 assert page.evaluate('assemblyViewer.objects.filter(o=>o.id.startsWith("FLOOROPEN-")).length')==23
 checks['assembly_shared_mesh_and_23_new_curb_guard_parts']=True
 for id in ['equipment','bridge','rooms','structure','frame','roof','foundations']:page.locator('#'+id).uncheck()
 page.locator('#shell').select_option('hidden');page.locator('#floor').select_option('106');page.locator('#cut').fill('107.2');page.locator('#cut').dispatch_event('input');page.locator('#floorAlpha').fill('22');page.locator('#floorAlpha').dispatch_event('input')
 page.evaluate('assemblyViewer.select(assemblyViewer.objects.find(o=>o.id==="FLOOROPEN-2-NORTH-1-CURB"));assemblyViewer.focus();assemblyViewer.setView(-Math.PI/2,Math.PI/2);assemblyViewer.draw()')
 page.screenshot(path=str(ROOT/'previews/总装二层楼板新增开孔.png'))
 assert not errors,errors;checks['uncaught_errors']=errors;b.close()
(ROOT/'data/楼板开孔浏览检查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False))
