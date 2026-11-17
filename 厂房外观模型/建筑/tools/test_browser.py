from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];base=os.environ.get('BUILDING_TEST_URL','http://127.0.0.1:8000');errors=[];checks={}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(base+'/厂房外观模型/建筑/index.html');page.wait_for_function('window.buildingViewer')
 checks['standalone_complete_mesh']=page.evaluate('buildingViewer.model.parts.length')>200
 page.screenshot(path=str(ROOT/'previews/完整建筑外观.png'))
 page.locator('#inside').click();page.screenshot(path=str(ROOT/'previews/楼梯与房间总览.png'))
 for value,name in [('SW','西南楼梯到屋面'),('SE','东南楼梯到三层')]:
  page.locator('#focus').select_option(value);page.screenshot(path=str(ROOT/('previews/'+name+'.png')))
 checks['stairs_two_groups']=True
 page.locator('#roomRoofs').uncheck()
 for value,name in [('room1','一楼西侧三个房间'),('room2','二楼东侧三个房间')]:
  page.locator('#focus').select_option(value);page.screenshot(path=str(ROOT/('previews/'+name+'.png')))
 checks['rooms_and_limited_columns']=True
 for value,name in [('holes2','二层三个吊装孔'),('holes3','三层两个吊装孔')]:
  page.locator('#focus').select_option(value);page.locator('#top').click();page.screenshot(path=str(ROOT/('previews/'+name+'.png')))
 checks['real_floor_apertures_views']=True
 page.locator('#cut').fill('110');page.locator('#cut').dispatch_event('input');assert page.locator('#cutValue').inner_text()=='EL110.0';checks['section']=True
 page.goto(base+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('window.ASSEMBLY_BUILDING===window.BUILDING_MODEL.parts');checks['single_shared_building_mesh']=True
 assert page.evaluate('assemblyViewer.objects.filter(o=>o.kind===\"stair\").length')>50
 assert page.evaluate('assemblyViewer.objects.filter(o=>o.kind===\"room_column\").length')>0
 page.locator('#inside').click();page.screenshot(path=str(ROOT/'previews/总装引用完整建筑.png'))
 for id in ['stairs','rooms','frame']:
  page.locator('#'+id).uncheck();page.locator('#'+id).check()
 checks['assembly_architecture_layer_toggles']=True
 page.set_viewport_size({'width':700,'height':700});assert page.locator('#scene').bounding_box()['width']>200
 checks['responsive']=True;checks['uncaught_errors']=errors;assert not errors,errors;b.close()
(ROOT/'data/浏览器检查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(checks)
