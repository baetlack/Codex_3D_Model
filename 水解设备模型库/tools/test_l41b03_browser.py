"""L41B03 current body, independent civil frame, downloads and unchanged scene."""
from pathlib import Path
import argparse,json,urllib.parse,urllib.request
from playwright.sync_api import sync_playwright
from test_l41b02_browser import server
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent

def verify(equipment_base,assembly_base,output):
    output.mkdir(parents=True,exist_ok=True);errors=[];checks={}
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1560,'height':1050});page.set_default_timeout(90000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:errors.append(r.url+' '+str(r.status)) if r.status>=400 and 'favicon' not in r.url else None)
        def visit(base,path):page.goto(base+urllib.parse.quote(path,safe='/?=&'),wait_until='load',timeout=90000)
        visit(equipment_base,'水解设备模型库/?type=L41B03')
        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length===23')
        assert page.locator('#foundation-mode').input_value()==''
        text=page.locator('body').inner_text();assert 'Ø1800×3100' in text and '底排接管另计' in text and '绝对定位待核' in text
        assert page.evaluate('parts.every(p=>!p.name.startsWith("支撑_"))')
        assert '除雾器托耳' in page.locator('#group').inner_text()
        page.screenshot(path=str(output/'预览_设备.png'));checks['ledger_size_pure_body_and_pending_labels']=True
        for value,count in [('combined',54),('L41B03',31),('',23)]:
            page.evaluate('async v=>{let e=document.getElementById("foundation-mode");e.value=v;await e.onchange();}',value)
            page.wait_for_function('(n)=>document.getElementById("preview-message").hidden && parts.length===n',arg=count)
            if value=='combined':
                assert page.evaluate('parts.filter(p=>p.name.endsWith("底板")).every(p=>Math.abs(Math.min(...p.vertices.map(v=>v[2]))-2000)<.01)')
                page.screenshot(path=str(output/'预览_本体与钢架.png'))
        checks['three_modes_and_four_ear_bearing_datum']=True
        links=page.locator('a[download]').evaluate_all('(els)=>els.map(e=>new URL(e.getAttribute("href"),location.href).href)')
        glbs=[u for u in links if u.endswith('.glb')];assert len(glbs)>=2
        for url in glbs:
            with urllib.request.urlopen(url,timeout=30) as r:assert r.read(4)==b'glTF'
        checks['current_body_and_steel_GLB_downloads']=True
        visit(equipment_base,'水解设备模型库/版本/2.0/L41B03/修订对比.html')
        assert page.locator('iframe').count()==2
        page.frame_locator('iframe[title="1.0"]').locator('#preview-message').wait_for(state='hidden')
        page.frame_locator('iframe[title="2.0"]').locator('#preview-message').wait_for(state='hidden')
        checks['frozen_and_current_comparison_loaded']=True
        visit(assembly_base,'水解总装工程/index.html')
        page.wait_for_function('window.assemblyViewer?.getState().ready')
        assert page.evaluate('!assemblyViewer.cfg.equipment.some(p=>p.asset==="L41B03") && !assemblyViewer.cfg.foundations.some(p=>p.asset.includes("L41B03")) && assemblyViewer.cfg.unplaced.some(p=>p.id==="L41B03")')
        checks['assembly_72_and_27_without_new_L41B03_instance']=True
        browser.close()
    assert not errors,errors
    report={'status':'passed','checks':checks,'page_errors_or_failed_resources':errors};(output/'浏览器校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'版本/2.0/L41B03');args=parser.parse_args()
    with server(REPO) as base:result=verify(base,base,args.output)
    print(json.dumps(result,ensure_ascii=False))
