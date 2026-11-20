"""F41B04 independent views, downloads and the corrected assembly datum."""
from pathlib import Path
import argparse,json,urllib.request,urllib.error,gzip
from playwright.sync_api import sync_playwright
from test_l41b02_browser import server
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent

def verify(equipment_base,assembly_base,output):
    output.mkdir(parents=True,exist_ok=True);errors=[];checks={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1560,'height':1050});page.set_default_timeout(120000)
        if equipment_base.startswith('https:'):
            def system_tls(route):
                try:r=urllib.request.urlopen(urllib.request.Request(route.request.url,headers={'Accept-Encoding':'identity'}),timeout=60)
                except urllib.error.HTTPError as e:r=e
                with r:
                    data=r.read()
                    if r.headers.get('Content-Encoding')=='gzip':data=gzip.decompress(data)
                    headers={k:v for k,v in r.headers.items() if k.lower() not in ['content-length','content-encoding','connection','transfer-encoding']}
                    route.fulfill(status=r.status,headers=headers,body=data)
            page.route('https://baetlack.github.io/**',system_tls)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('requestfailed',lambda r:errors.append(r.url+' '+str(r.failure)))
        page.on('response',lambda r:errors.append(r.url+' '+str(r.status)) if r.status>=400 and 'favicon' not in r.url else None)
        def visit(base,path):page.goto(base+urllib.parse.quote(path,safe='/?=&'),wait_until='load',timeout=120000)
        visit(equipment_base,'水解设备模型库/?type=F41B04')
        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length===1')
        assert page.evaluate('parts[0].name')=='本体_烟囱直筒'
        assert page.locator('#foundation-mode').input_value()==''
        text=page.locator('body').inner_text();assert 'EL123.300' in text and '17000' in text and '11000' in text
        page.screenshot(path=str(output/'预览_设备.png'));checks['original_tube_and_pending_height_labels']=True
        for value,count in [('combined',168),('combined:F41B04',15),('F41B04',14),('F41B04-钢塔架',153),('',1)]:
            page.evaluate('async v=>{let e=document.getElementById("foundation-mode");e.value=v;await e.onchange();}',value)
            page.wait_for_function('(n)=>document.getElementById("preview-message").hidden && parts.length===n',arg=count)
            if value=='combined':page.screenshot(path=str(output/'预览_钢架局部对照.png'))
            if value=='combined:F41B04':page.screenshot(path=str(output/'预览_设备与基础.png'))
        checks['all_five_modes_and_153_preserved_steel_parts']=True
        links=page.locator('a[download]').evaluate_all('(els)=>els.map(e=>new URL(e.getAttribute("href"),location.href).href)')
        for url in links:
            if url.endswith('.glb'):
                with urllib.request.urlopen(url,timeout=60) as r:assert r.read(4)==b'glTF'
        checks['current_GLB_downloads']=True
        visit(equipment_base,'水解设备模型库/版本/2.0/F41B04/安装对照.html')
        assert '23000' in page.locator('body').inner_text() and '23300' in page.locator('body').inner_text();checks['before_after_installation_table']=True
        visit(equipment_base,'水解设备模型库/?type=C41B02')
        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>20')
        assert page.locator('#foundation-mode').input_value()=='combined';checks['accepted_class_default_unchanged']=True
        visit(assembly_base,'水解总装工程/')
        page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=180000)
        assert page.evaluate('assemblyViewer.cfg.equipment.length')==72
        assert page.evaluate('assemblyViewer.cfg.unplaced.length')==27
        assert page.evaluate('assemblyViewer.cfg.equipment.find(p=>p.id==="F41B04").position_mm[2]')==23300
        assert page.evaluate('assemblyViewer.cfg.foundations.find(p=>p.id==="BASE-F41B04").position_mm[2]')==23300
        assert not page.evaluate('assemblyViewer.cfg.foundations.some(p=>p.id!=="BASE-F41B04" && p.support_for==="F41B04")')
        page.locator('#search').fill('F41B04');page.locator('#list button').filter(has_text='尾气烟囱').first.click();page.locator('#focus').click()
        page.screenshot(path=str(output/'预览_总装安装.png'));checks['assembly_EL123300_and_round_base_without_steel_instance']=True
        browser.close()
    assert not errors,errors
    report={'status':'passed','checks':checks,'page_errors_or_failed_resources':errors}
    (output/'浏览器校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False),flush=True);return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base');p.add_argument('--assembly-base');p.add_argument('--root',type=Path,default=REPO);p.add_argument('--output',type=Path,default=ROOT/'版本/2.0/F41B04');a=p.parse_args()
    if a.base:verify(a.base,a.assembly_base or a.base,a.output)
    else:
        with server(a.root) as base:verify(base,base,a.output)
