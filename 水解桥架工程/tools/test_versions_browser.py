"""Linux Playwright checks for both portable releases and the live entry."""
from pathlib import Path
import json,os,math
from urllib.parse import unquote
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];URL=os.environ.get('ASSEMBLY_TEST_URL','http://127.0.0.1:8765')
errors=[];requests=[];checks=[]
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1600,'height':1000});page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:requests.append(r.url) if r.status>=400 and 'favicon' not in r.url else None)
 for version,relative in [('1.0','版本/1.0/index.html'),('2.0','版本/2.0/index.html'),('2.0','index.html')]:
  page.goto(URL+'/水解桥架工程/'+relative);page.wait_for_function('!!window.ASSEMBLY && document.querySelectorAll("#list button").length===48')
  assert page.evaluate('ASSEMBLY.parts.length')==112
  actual=page.evaluate('ASSEMBLY.version');assert actual==('0.2-direction-and-riser' if version=='1.0' else '2.0-column-contact')
  assert page.locator('img#preview').evaluate('(e)=>e.complete && e.naturalWidth>0')
  width=page.locator('#scene').bounding_box()['width'];page.locator('#toggleLeftPanel').click();assert page.locator('#scene').bounding_box()['width']>width+100
  page.locator('#toggleLeftPanel').click();page.locator('#search').fill('L3-C04');assert page.locator('#list button').count()==1;page.locator('#list button').click();assert page.locator('#partTitle').inner_text()=='L3-C04'
  assert '同侧边线' in page.locator('#partWarnings').inner_text()
  page.locator('#search').fill('');page.locator('#allLayers').click();page.locator('#top').click();assert abs(page.evaluate('pitch')-math.pi/2)<1e-9
  page.locator('#resetDirection').click();assert abs(page.evaluate('yaw')+math.pi/4)<1e-9
  page.locator('#clear').click();page.wait_for_timeout(200)
  if relative=='index.html':page.screenshot(path=str(ROOT/'models/整体/previews/交互模型界面.png'))
  else:page.screenshot(path=str(ROOT/'版本'/version/'浏览验证.png'))
  # Verify the independent GLB download and library, not only the top-level page.
  link=page.locator('a[download]').first.get_attribute('href');absolute=page.evaluate('(href)=>new URL(href,location.href).href',link);response=page.request.get(absolute);assert response.ok and response.body()[:4]==b'glTF'
  page.goto(URL+'/水解桥架工程/'+('' if relative=='index.html' else f'版本/{version}/')+'models/连接件库/index.html');page.wait_for_function('document.querySelectorAll("#list button").length===47')
  assert page.locator('#canvas').bounding_box()['width']>200
  checks.append({'entry':relative,'geometry_version':actual,'parts':112,'search_select_panels_camera_glb_library':'passed'})
 page.goto(URL+'/水解桥架工程/版本/1.0/浏览.html');frame=page.frame_locator('iframe');frame.locator('#scene').wait_for();assert frame.locator('#list button').count()==48
 page.goto(URL+'/水解桥架工程/版本/');page.get_by_role('link',name='查看整改版').click();assert '/版本/2.0/' in unquote(page.url);page.wait_for_function('window.ASSEMBLY?.version==="2.0-column-contact"')
 assert not errors,errors
 assert not requests,requests
 browser.close()
report={'status':'passed','checks':checks,'frozen_wrapper_and_version_links':'passed','errors':errors,'failed_resources':requests}
(ROOT/'models/整体/reports/browser_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
