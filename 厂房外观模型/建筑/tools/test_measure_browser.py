"""Exercise actual canvas clicks against known building geometry in both viewers."""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get('BUILDING_TEST_URL','http://127.0.0.1:8000')
checks={};errors=[]
def click_point(page,api,point,canvas):
 q=page.evaluate(f'{api}.measure.project({json.dumps(point)})')
 box=page.locator(canvas).bounding_box()
 assert 0<q[0]<box['width'] and 0<q[1]<box['height'],q
 page.mouse.click(box['x']+q[0],box['y']+q[1])
def state(page,api):return page.evaluate(api+'.measure.getState()')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1500,'height':1000});page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(BASE+'/厂房外观模型/建筑/?view=frame');page.wait_for_function('window.buildingViewer?.measure')
 page.locator('#stairs').uncheck();page.locator('#rooms').uncheck()
 page.evaluate("buildingViewer.viewer.view(-Math.PI/2,0,'南向测量');buildingViewer.viewer.focusBounds([-1000,-1000,-500],[8000,1000,6500])")
 page.locator('#measureToggle').click();assert page.locator('#measureToggle').get_attribute('aria-pressed')=='true'
 page.locator('#measureMode').select_option('bounds');click_point(page,'buildingViewer',[0,-325,2000],'#view')
 v=state(page,'buildingViewer')['info'];assert v['name']=='COL-000',v
 assert [round(v['high'][k]-v['low'][k],3) for k in range(3)]==[650,650,23000]
 checks['standalone_column_section_650x650_height_23000']=True
 page.locator('#measureMode').select_option('axis')
 click_point(page,'buildingViewer',[0,-325,2000],'#view');click_point(page,'buildingViewer',[0,-325,2000],'#view')
 assert len(state(page,'buildingViewer')['points'])==1
 click_point(page,'buildingViewer',[6000,-325,2000],'#view');v=state(page,'buildingViewer');assert abs(v['result']['value']-6000)<.001,v
 assert [q['part'] for q in v['points']]==['COL-000','COL-001'];checks['column_axis_spacing_6000_and_duplicate_rejected']=True
 page.screenshot(path=str(ROOT/'previews/测量_柱轴间距.png'))
 page.locator('#measureMode').select_option('distance')
 click_point(page,'buildingViewer',[-325,-325,0],'#view');click_point(page,'buildingViewer',[325,-325,0],'#view')
 v=state(page,'buildingViewer');assert abs(v['result']['distance']-650)<.001,v
 assert [q['type'] for q in v['points']]==['角点','角点'],v
 checks['real_corner_snap_650_mm']=True;page.screenshot(path=str(ROOT/'previews/测量_柱截面.png'))
 page.locator('#measureUndo').click();assert len(state(page,'buildingViewer')['points'])==1
 click_point(page,'buildingViewer',[325,-325,0],'#view');assert len(state(page,'buildingViewer')['points'])==2
 # A drag must rotate rather than create an accidental third measurement.
 box=page.locator('#view').bounding_box();page.mouse.move(box['x']+box['width']*.7,box['y']+box['height']*.5);page.mouse.down();page.mouse.move(box['x']+box['width']*.7+30,box['y']+box['height']*.5+10,steps=4);page.mouse.up()
 assert state(page,'buildingViewer')['points']==v['points'];checks['undo_and_drag_does_not_pick']=True
 page.evaluate("buildingViewer.viewer.view(-Math.PI/2,0,'南向测量')")
 page.locator('#measureClear').click()
 # The projected corner of a wider back-row column lies near the visible front
 # column, but beyond this focused camera's far plane. It must not be snapped.
 click_point(page,'buildingViewer',[-375,14025,0],'#view')
 near=state(page,'buildingViewer');assert len(near['points'])==1 and near['points'][0]['point'][1]<8000,near
 checks['camera_depth_clipped_vertices_cannot_snap']=True
 page.locator('#measureClear').click()
 click_point(page,'buildingViewer',[-325,-325,3000],'#view');click_point(page,'buildingViewer',[325,-325,3000],'#view')
 edge=state(page,'buildingViewer');assert abs(edge['result']['distance']-650)<.001,edge
 assert [q['type'] for q in edge['points']]==['边线','边线'],edge;checks['visible_edge_snap_650_mm']=True
 page.locator('#measureMode').select_option('height');page.locator('#cut').fill('106');page.locator('#cut').dispatch_event('input')
 click_point(page,'buildingViewer',[-325,-325,0],'#view');click_point(page,'buildingViewer',[-325,-325,6000],'#view')
 manual=state(page,'buildingViewer');assert abs(manual['result']['value']-6000)<.001,manual
 checks['manual_height_and_section_edge_snap_6000']=True
 page.locator('#cut').fill('130');page.locator('#cut').dispatch_event('input')
 page.locator('#measureHeight').click()
 assert state(page,'buildingViewer')['result']['value']==6000
 page.locator('#measureUnit').select_option('m');assert '6 m' in page.locator('#measureResult').inner_text()
 page.locator('#measureLevelA').select_option('112');page.locator('#measureLevelB').select_option('123');page.locator('#measureHeight').click();assert state(page,'buildingViewer')['result']['value']==11000
 page.locator('#measureLevelA').select_option('100');page.locator('#measureLevelB').select_option('106');page.locator('#measureHeight').click()
 checks['floor_height_6000_roof_height_11000_and_unit_conversion']=True
 page.evaluate('buildingViewer.viewer.view(BUILDING_STYLE.view.yaw,.3,"层高测量");buildingViewer.viewer.fit()');page.screenshot(path=str(ROOT/'previews/测量_层高.png'))
 page.locator('#measureClear').click();assert not state(page,'buildingViewer')['points']
 page.keyboard.press('Escape');assert not state(page,'buildingViewer')['active'];checks['clear_and_escape_exit']=True
 # An opaque facade must block a hidden column in axis mode.
 page.goto(BASE+'/厂房外观模型/建筑/');page.wait_for_function('window.buildingViewer?.measure');page.locator('#measureToggle').click();page.locator('#measureMode').select_option('axis')
 click_point(page,'buildingViewer',[0,-325,3600],'#view');assert not state(page,'buildingViewer')['points'];assert '请点击立柱' in page.locator('#measureStatus').inner_text()
 checks['opaque_facade_blocks_hidden_column']=True
 # Neither hidden layers nor discarded height ranges may supply a pick.
 page.locator('#exterior').uncheck();page.locator('#stairs').uncheck();page.locator('#rooms').uncheck();page.locator('#roof').uncheck();page.locator('#floors').uncheck();page.locator('#frame').uncheck()
 page.locator('#view').click(position={'x':100,'y':150});assert not state(page,'buildingViewer')['points']
 page.locator('#frame').check();page.locator('#cut').fill('102');page.locator('#cut').dispatch_event('input')
 page.evaluate("buildingViewer.viewer.view(-Math.PI/2,0,'剖切测量');buildingViewer.viewer.focusBounds([-1000,-1000,-500],[8000,1000,6500])")
 click_point(page,'buildingViewer',[0,-325,3600],'#view');assert not state(page,'buildingViewer')['points'];checks['hidden_and_clipped_geometry_cannot_be_picked']=True
 page.goto(BASE+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 for id in ['equipment','bridge','foundations','roof','floors','stairs','rooms','frame']:page.locator('#'+id).uncheck()
 page.locator('#shell').select_option('transparent')
 page.evaluate("assemblyViewer.select(assemblyViewer.objects.find(o=>o.id==='COL-000'));assemblyViewer.focus();assemblyViewer.setView(-Math.PI/2,0);assemblyViewer.draw()")
 page.locator('#measureToggle').click();page.locator('#measureMode').select_option('bounds')
 click_point(page,'assemblyViewer',[0,-325,2000],'#scene');v=state(page,'assemblyViewer')['info'];assert v['name']=='COL-000',v
 assert [round(v['high'][k]-v['low'][k],3) for k in range(3)]==[650,650,23000]
 page.locator('#measureMode').select_option('axis');click_point(page,'assemblyViewer',[0,-325,2000],'#scene');click_point(page,'assemblyViewer',[6000,-325,2000],'#scene')
 assert abs(state(page,'assemblyViewer')['result']['value']-6000)<.001
 checks['assembly_mm_conversion_section_and_axis_spacing_through_transparent_wall']=True;page.screenshot(path=str(ROOT/'previews/测量_总装柱距.png'))
 page.locator('#measureMode').select_option('height');page.locator('#measureHeight').click();assert state(page,'assemblyViewer')['result']['value']==6000
 checks['assembly_floor_height']=True
 page.locator('#measureToggle').click();assert not state(page,'assemblyViewer')['active']
 page.set_viewport_size({'width':720,'height':700});page.locator('#measureToggle').click();assert page.locator('#measureMode').is_visible();checks['responsive_panel']=True
 assert not errors,errors;checks['uncaught_errors']=errors;b.close()
(ROOT/'data/测量功能检查.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False))
