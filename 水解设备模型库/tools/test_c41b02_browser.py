"""Exercise both equipment versions, part separation, downloads and current assembly."""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B02';URL=os.environ.get('ASSEMBLY_TEST_URL','http://127.0.0.1:8765');errors=[];failed=[];checks={}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=browser.new_page(viewport={'width':1560,'height':1050});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:failed.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
 page.goto(URL+'/水解设备模型库/?type=C41B02');page.wait_for_function('parts.length>=150 && document.getElementById("preview-message").hidden')
 assert page.locator('#list button').count()==35
 assert '新接口绝对方位' in page.locator('#detail').inner_text();assert 'EL112.310' in page.locator('#detail').inner_text()
 checks['35_groups_and_new_datum_pending_labels']=True
 page.locator('#foundation-mode').select_option('');page.wait_for_function('parts.length===150');page.screenshot(path=str(OUT/'预览_设备.png'))
 page.locator('#foundation-mode').select_option('combined');page.wait_for_function('parts.length===152');page.wait_for_timeout(300);page.screenshot(path=str(OUT/'预览_设备与基础.png'))
 checks['combined_equipment_and_unchanged_foundation']=True
 page.locator('#top').click();page.wait_for_timeout(200);page.screenshot(path=str(OUT/'预览_盖面.png'))
 page.locator('#group').select_option(label='接口');page.wait_for_timeout(100);assert page.evaluate('partGroups.get("接口").filter(p=>p.name.includes("盘管检修盖")).length')==8
 checks['eight_covers_and_nozzle_parts']=True
 page.locator('#foundation-mode').select_option('');page.wait_for_function('parts.length===150')
 page.locator('#group').select_option(label='底部型钢支撑');assert page.evaluate('partGroups.get("底部型钢支撑").length')==27
 page.locator('#front').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/'预览_型钢.png'))
 page.locator('#foundation-mode').select_option('C41B02');page.wait_for_function('parts.length===2');checks['support_and_civil_separate']=True
 width=page.locator('#scene').bounding_box()['width'];page.locator('#toggle-detail').click();assert page.locator('#scene').bounding_box()['width']>width+100;page.locator('#toggle-detail').click();checks['panel_controls']=True
 link=page.get_by_role('link',name='设备 GLB',exact=True);href=link.get_attribute('href');absolute=page.evaluate('(href)=>new URL(href,location.href).href',href);r=page.request.get(absolute);assert r.ok and r.body()[:4]==b'glTF';checks['new_glb_download']=True
 page.locator('#search').fill('C41B01');page.locator('#list button').click();page.wait_for_function('rowTag==="C41B01A/B" && document.getElementById("preview-message").hidden');assert '8组' not in page.locator('#detail').inner_text();checks['other_type_unaffected']=True
 page.goto(URL+'/水解设备模型库/版本/1.0/快照/水解设备模型库/');page.wait_for_function('document.querySelectorAll("#list button").length===35');page.locator('#search').fill('C41B02');page.locator('#list button').click();page.wait_for_function('rowTag==="C41B02A-E" && document.getElementById("preview-message").hidden');assert page.evaluate('parts.filter(p=>p.name.startsWith("接口_顶盖法兰")).length')==6
 page.screenshot(path=str(OUT/'预览_1.0对比.png'));checks['frozen_1_0_six_port_geometry']=True
 page.goto(URL+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
 assert page.evaluate('assemblyViewer.cfg.equipment.length')==72
 assert page.evaluate('assemblyViewer.cfg.equipment.filter(p=>p.asset==="C41B02"&&p.equipment_version==="2.0-C41B02-01"&&p.orientation_status.includes("待核")).length')==5
 page.locator('#inside').click();page.locator('#search').fill('C41B02A');page.locator('#list button').click();page.locator('#focus').click();page.wait_for_timeout(300);page.screenshot(path=str(OUT/'预览_总装定位.png'))
 checks['current_assembly_5_revised_72_placed']=True
 page.goto(URL+'/水解设备模型库/版本/1.0/快照/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000);assert not page.evaluate('assemblyViewer.cfg.equipment_versions?.C41B02');assert page.evaluate('assemblyViewer.cfg.equipment.filter(p=>p.asset==="C41B02"&&p.z_status==="有安装基准").length')==5;checks['frozen_1_0_installation']=True
 page.goto(URL+'/水解设备模型库/版本/2.0/');page.frame_locator('iframe').locator('#scene').wait_for();checks['version_2_wrapper']=True
 assert not errors,errors
 assert not failed,failed
 browser.close()
report={'status':'passed','checks':checks,'page_errors':errors,'failed_resources':failed}
(OUT/'浏览器检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
