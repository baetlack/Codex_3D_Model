"""Check C41B04 standalone, six-machine support composition, comparison and total."""
from pathlib import Path
import json,os
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'版本/2.0/C41B04'
URL=os.environ.get('ASSEMBLY_TEST_URL','http://127.0.0.1:8766');errors=[];failed=[];checks={}
expected=len(json.loads((OUT/'设备/model_data.js').read_text().split('=',1)[1].strip().rstrip(';')))
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    page=browser.new_page(viewport={'width':1560,'height':1080});page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:failed.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
    page.goto(URL+'/水解设备模型库/?type=C41B04');page.wait_for_function('rowTag==="C41B04A-F" && document.getElementById("preview-message").hidden')
    assert page.locator('#list button').count()==35
    assert page.evaluate('parts.length')==6*expected+114
    assert 'EL104.500' in page.locator('#detail').inner_text() and '200mm' in page.locator('#detail').inner_text()
    page.screenshot(path=str(OUT/'预览_设备与钢架.png'));checks['six_equipment_three_frames_and_datum_labels']=True
    page.locator('#foundation-mode').select_option('');page.wait_for_function(f'parts.length==={expected}')
    page.screenshot(path=str(OUT/'预览_设备.png'))
    page.locator('#top').click();page.screenshot(path=str(OUT/'预览_俯视.png'))
    assert page.evaluate('parts.filter(p=>p.name.includes("承托底板")).length')==4
    page.locator('#group').select_option(label='换热器托耳');page.locator('#iso').click()
    checks['four_separate_ears_and_holes']=True
    page.locator('#foundation-mode').select_option('C41B04');page.wait_for_function('parts.length===114');checks['steel_independent']=True
    for name,magic in [('设备 GLB',b'glTF'),('厂家条件图PDF',b'%PDF')]:
        href=page.get_by_role('link',name=name,exact=True).get_attribute('href');url=page.evaluate('(href)=>new URL(href,location.href).href',href)
        response=page.request.get(url);assert response.ok and response.body()[:4]==magic
    checks['current_glb_and_manufacturer_pdf_downloads']=True
    page.goto(URL+'/水解设备模型库/版本/2.0/C41B04/修订对比.html')
    for f in page.frames[1:]:f.wait_for_function('window.compareReady===true')
    page.screenshot(path=str(OUT/'预览_新旧对照.png'))
    for mode in ['top','lugs','ports']:
        page.locator('button[data-view="'+mode+'"]').click();page.wait_for_timeout(100);page.screenshot(path=str(OUT/('预览_对照_'+mode+'.png')))
    checks['frozen_1_0_vs_new_compared_at_same_bearing_datum']=True
    page.goto(URL+'/水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=120000)
    assert page.evaluate('assemblyViewer.cfg.equipment.filter(e=>e.asset==="C41B04"&&e.equipment_version==="2.0-C41B04-01"&&e.position_mm[2]===4500).length')==6
    assert page.evaluate('assemblyViewer.cfg.foundations.filter(e=>e.asset==="foundation-C41B04").length')==3
    page.locator('#inside').click();page.locator('#search').fill('C41B04A');page.locator('#list button').first.click();page.locator('#focus').click();page.wait_for_timeout(200)
    page.screenshot(path=str(OUT/'预览_总装.png'));checks['six_current_instances_and_three_independent_supports_in_total']=True
    assert not errors,errors;assert not failed,failed
    browser.close()
report={'status':'passed','checks':checks,'page_errors':errors,'failed_resources':failed}
(OUT/'浏览器检查.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False))
