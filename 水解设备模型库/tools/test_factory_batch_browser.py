"""Exercise every class once; package smoke tests reuse the same narrow checks."""
from pathlib import Path
import argparse,json,urllib.parse,urllib.request
from playwright.sync_api import sync_playwright
from test_l41b02_browser import server
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
NEW=['C41B01','C41B03','F41B01','F41B02','F41B05','F41B06','D41B02','L41B05']

def verify(equipment_base,assembly_base,output,full=True):
    output.mkdir(parents=True,exist_ok=True);errors=[];checks={};rendered=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--use-gl=angle','--use-angle=swiftshader','--enable-unsafe-swiftshader'])
        page=browser.new_page(viewport={'width':1560,'height':1050});page.set_default_timeout(90000)
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:errors.append(r.url+' '+str(r.status)) if r.status>=400 and 'favicon' not in r.url else None)
        def visit(base,path):page.goto(base+urllib.parse.quote(path,safe='/?=&'),wait_until='load',timeout=90000)
        visit(equipment_base,'水解设备模型库/?type=C41B01');page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0')
        choices=page.evaluate('rows.map(r=>({id:r.位号,key:tagForRow(r)}))');assert len(choices)==35
        chosen=choices if full else [r for r in choices if r['key'] in ['C41B01','F41B05','L41B05','P41B07','C41B02','F41B08']]
        for item in chosen:
            key=item['key'];page.evaluate('async id=>await select(id)',item['id'])
            page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0')
            count=page.evaluate('parts.length');assert count>0;rendered.append(key)
            text=page.locator('#details').inner_text()
            if key in NEW:
                assert page.locator('#foundation-mode').input_value()==''
                assert '本类首轮处理与待核' in text
                links=page.locator('a[download]').evaluate_all('(els)=>els.map(e=>new URL(e.getAttribute("href"),location.href).href)')
                body_glb=[u for u in links if urllib.parse.unquote(u).endswith('/设备/'+key+'.glb')];assert body_glb,key
                with urllib.request.urlopen(body_glb[0],timeout=30) as r:assert r.read(4)==b'glTF'
                if full:
                    folder=ROOT/'版本/2.0'/key;page.screenshot(path=str(folder/'预览_设备.png'))
                    options=page.locator('#foundation-mode option').evaluate_all('(els)=>els.map(e=>e.value)')
                    if 'combined' in options:
                        page.evaluate('async ()=>{const e=document.getElementById("foundation-mode");e.value="combined";await e.onchange()}')
                        page.wait_for_function('document.getElementById("preview-message").hidden && parts.length>0')
                        page.screenshot(path=str(folder/'预览_基础配合.png'))
            if key in ['P41B07','P41B09']:assert '立式' in text and '未整改通过' in text
            if key=='C41B02':assert page.locator('#foundation-mode').input_value()=='combined'
            if key=='F41B08':
                page.evaluate('async ()=>{const e=document.getElementById("foundation-mode");if([...e.options].some(o=>o.value==="")&&e.onchange){e.value="";await e.onchange()}}')
                assert page.evaluate('parts.length')==1,page.evaluate('parts.map(p=>p.name)')
            print('Viewer checked',key,count,flush=True)
        checks['rendered_classes']=rendered
        checks['new_model_downloads_and_separate_foundations']=True
        checks['known_vertical_pump_issue_visible']=True
        visit(equipment_base,'水解设备模型库/版本/复核总览.html');assert page.locator('tbody tr').count()==35
        page.locator('button[data-filter="new"]').click();assert page.locator('tbody tr:visible').count()==8
        page.locator('button[data-filter="retain"]').click();assert page.locator('tbody tr:visible').count()==19
        checks['35_class_overview_filters']=True
        with urllib.request.urlopen(equipment_base+urllib.parse.quote('水解设备模型库/data/连续整改_20261120/99台复核清单.json',safe='/'),timeout=30) as r:data=json.load(r)
        assert len(data['units'])==len({q['id'] for q in data['units']})==99;checks['all_99_unique_unit_records']=True
        visit(assembly_base,'水解总装工程/');page.wait_for_function('window.assemblyViewer?.getState().ready',timeout=180000)
        assert page.evaluate('assemblyViewer.cfg.equipment.length')==72 and page.evaluate('assemblyViewer.cfg.unplaced.length')==27
        assert page.evaluate('assemblyViewer.cfg.equipment.find(q=>q.id==="F41B04").position_mm[2]')==23300
        assert not page.evaluate('assemblyViewer.cfg.equipment.some(q=>q.id==="L41B05"||q.id==="L41B03")')
        if full:page.screenshot(path=str(output/'预览_总装.png'))
        checks['72_placed_27_unplaced_and_prior_chimney_datum']=True
        browser.close()
    assert not errors,errors
    report={'status':'passed','full_library':full,'checks':checks,'errors':errors};(output/'浏览器校验.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'data/连续整改_20261120');p.add_argument('--smoke',action='store_true');args=p.parse_args()
    with server(REPO) as base:result=verify(base,base,args.output,not args.smoke)
    print(json.dumps(result,ensure_ascii=False))
