"""Pixel regression for coplanar facade/column surfaces in both real viewers."""
from pathlib import Path
import json, os
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get('BUILDING_TEST_URL', 'http://127.0.0.1:8000')
checks = {}
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
        args=['--no-sandbox', '--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':1600, 'height':1100})
    page.set_default_timeout(60000)
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(BASE+'/厂房外观模型/建筑/')
    page.wait_for_function('window.buildingViewer')
    checks['coplanar_fixture'] = page.evaluate('''() => {
        // Use contrasting fixture colors so the theme cannot conceal a depth regression.
        const style=BUILDING_STYLE;window.BUILDING_STYLE={...style,color:p=>p.color};
        const canvas=document.createElement('canvas');
        canvas.style='width:800px;height:800px;position:fixed;left:0;top:0';document.body.append(canvas);
        const column=structuredClone(BUILDING_MODEL.parts.find(p=>p.name==='COL-000'));
        column.vertices.forEach(v=>v[2]*=5000/23000);
        const wall={name:'test_wall',kind:'wall',color:'#788a95',
            vertices:[[-325,-3000,0],[-325,3000,0],[-325,3000,5000],[-325,-3000,5000]],faces:[[0,3,2],[0,2,1]]};
        let pixel;
        const viewer=createBuildingViewer(canvas,{doubleSided:true,onFrame:({project})=>{
            const q=project([-325,70,2500]),gl=canvas.getContext('webgl'),out=new Uint8Array(4);
            gl.readPixels(Math.floor(q[0]),canvas.height-1-Math.floor(q[1]),1,1,gl.RGBA,gl.UNSIGNED_BYTE,out);
            pixel=Array.from(out);
        }});
        const angles=[];
        for(const tilt of [.1,.4,.8])for(let i=0;i<=40;i++)angles.push([Math.PI-.9+i*.045,tilt]);
        const columnFaces=column.faces;column.faces=[];viewer.setParts([wall,column]);
        const expected=angles.map(a=>{viewer.view(...a,'reference');return pixel;});
        column.faces=columnFaces;
        let samples=0,mismatches=0;
        for(const parts of [[wall,column],[column,wall]]){
            viewer.setParts(parts);
            angles.forEach((a,i)=>{viewer.view(...a,'probe');samples++;
                if(pixel.some((v,k)=>Math.abs(v-expected[i][k])>2))mismatches++;});
        }
        canvas.remove();window.BUILDING_STYLE=style;return {samples,mismatches};
    }''')
    assert checks['coplanar_fixture']['mismatches'] == 0, checks
    print('共面墙柱样例246个视角/绘制顺序比对通过', flush=True)
    # Check stable facade coverage at an actual outer column face above the window heads on all four elevations, in shallow and steep views.
    actual_probe = '''(assembly) => {
        const faces=[{yaw:Math.PI,p:[-325,36070,3600]},{yaw:0,p:[44325,36070,3600]},
            {yaw:-Math.PI/2,p:[19070,-325,3600]},{yaw:Math.PI/2,p:[19070,72325,3600]}];
        const cases=[];
        for(const f of faces)for(const tilt of [.15,.7])for(let i=0;i<=4;i++)cases.push({...f,yaw:f.yaw-.8+i*.4,tilt});
        let canvas,viewer,pixel,current;
        if(!assembly){
            canvas=document.createElement('canvas');canvas.style='width:1100px;height:1000px;position:fixed;left:0;top:0';document.body.append(canvas);
            viewer=createBuildingViewer(canvas,{doubleSided:true,onFrame:({project})=>{
                if(!current)return;const q=project(current.p),gl=canvas.getContext('webgl'),out=new Uint8Array(4);
                gl.readPixels(Math.floor(q[0]),canvas.height-1-Math.floor(q[1]),1,1,gl.RGBA,gl.UNSIGNED_BYTE,out);pixel=Array.from(out);
            }});
        }else canvas=document.getElementById('scene');
        const gl=canvas.getContext('webgl');
        function sample(c){
            current=c;
            if(!assembly){viewer.view(c.yaw,c.tilt,'rotation regression');return pixel;}
            assemblyViewer.setView(c.yaw,c.tilt);assemblyViewer.draw();
            const {center,zoom}=assemblyViewer.getState(),w=canvas.clientWidth,h=canvas.clientHeight,
                ppm=.89*zoom*Math.min(w,h)/(2*46),v=c.p.map((x,i)=>x/1000-center[i]),
                right=[-Math.sin(c.yaw),Math.cos(c.yaw),0],
                up=[-Math.sin(c.tilt)*Math.cos(c.yaw),-Math.sin(c.tilt)*Math.sin(c.yaw),Math.cos(c.tilt)],
                dot=(a,b)=>a.reduce((s,x,i)=>s+x*b[i],0),
                x=w/2+dot(v,right)*ppm,y=h/2-dot(v,up)*ppm,out=new Uint8Array(4);
            gl.readPixels(Math.floor(x),canvas.height-1-Math.floor(y),1,1,gl.RGBA,gl.UNSIGNED_BYTE,out);return Array.from(out);
        }
        function columns(show){
            if(assembly){document.getElementById('structure').checked=show;document.getElementById('frame').checked=show;}
            else viewer.setParts(BUILDING_MODEL.parts.map(p=>!show&&['structure','frame'].includes(p.kind)?{...p,faces:[]}:p));
        }
        columns(false);const expected=cases.map(sample);columns(true);const actual=cases.map(sample);
        const mismatches=actual.flatMap((x,i)=>x.some((v,k)=>Math.abs(v-expected[i][k])>2)?[{view:cases[i],actual:x,expected:expected[i]}]:[]);
        if(!assembly)canvas.remove();return {samples:cases.length,mismatches,depth_bits:gl.getParameter(gl.DEPTH_BITS)};
    }'''
    checks['standalone_four_elevations'] = page.evaluate(actual_probe, False)
    assert not checks['standalone_four_elevations']['mismatches'], checks['standalone_four_elevations']
    print('独立建筑四立面40个视角比对通过', flush=True)
    page.evaluate('buildingViewer.viewer.view(-Math.PI/2,.25,"南立面大门")')
    page.screenshot(path=str(ROOT/'previews/南侧大门与立柱.png'))
    page.evaluate('buildingViewer.viewer.focusBounds([18000,-1000,0],[27000,1000,6000])')
    page.screenshot(path=str(ROOT/'previews/南侧大门细节.png'))
    page.goto(BASE+'/水解总装工程/')
    page.wait_for_function('window.assemblyViewer?.getState().ready', timeout=120000)
    # Isolate architecture for the column pixel probe; full equipment/tray views are
    # covered by the assembly browser test, and do not affect these exterior points.
    for layer in ['equipment','bridge','foundations']:
        page.locator('#'+layer).uncheck()
    checks['assembly_probe_scope'] = '完整建筑；设备、桥架、基础隐藏'
    checks['assembly_four_elevations'] = page.evaluate(actual_probe, True)
    assert not checks['assembly_four_elevations']['mismatches'], checks['assembly_four_elevations']
    print('总装建筑四立面40个视角比对通过', flush=True)
    page.evaluate('assemblyViewer.setView(-Math.PI/4,.25);assemblyViewer.draw()')
    page.screenshot(path=str(ROOT/'previews/总装外墙立柱稳定显示.png'))
    checks['uncaught_errors'] = errors
    assert not errors, errors
    browser.close()
(ROOT/'data/立面显示检查.json').write_text(json.dumps(checks, ensure_ascii=False, indent=2)+'\n')
print(json.dumps(checks, ensure_ascii=False))
