import {spawn} from 'node:child_process';
import {readFile,writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
import assert from 'node:assert/strict';
const root=process.cwd(),out=path.join(root,'三层桥架模型'),profile=path.join(root,`.assembly-check-profile-v02-${process.pid}`);
const proc=spawn('C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',['--headless','--disable-gpu','--no-first-run','--no-default-browser-check','--remote-debugging-port=0',`--user-data-dir=${profile}`,'--window-size=1600,1000','about:blank'],{windowsHide:true,stdio:'ignore'});
let ws,seq=0;const pending=new Map(),errors=[],checks=[];
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
try{
 let port;for(let i=0;i<100;i++){try{port=(await readFile(path.join(profile,'DevToolsActivePort'),'utf8')).split('\n')[0];break;}catch{await pause(100);}}assert(port,'No DevTools port');
 const response=await fetch(`http://127.0.0.1:${port}/json/new?${encodeURIComponent(pathToFileURL(path.join(out,'index.html')).href)}`,{method:'PUT'});assert(response.ok);const target=await response.json();
 ws=new WebSocket(target.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
 ws.onmessage=event=>{const msg=JSON.parse(event.data);if(msg.id){const p=pending.get(msg.id);if(p){pending.delete(msg.id);msg.error?p.reject(new Error(JSON.stringify(msg.error))):p.resolve(msg.result);}}if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails.text+': '+(msg.params.exceptionDetails.exception?.description||''));};
 async function call(method,params={}){const id=++seq;const result=new Promise((resolve,reject)=>pending.set(id,{resolve,reject}));ws.send(JSON.stringify({id,method,params}));return await result;}
 async function evaluate(expression){const result=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;}
 await call('Runtime.enable');await call('Page.enable');
 for(let i=0;i<100;i++){if(await evaluate('document.readyState === "complete" && !!window.ASSEMBLY && document.querySelectorAll("#list button").length===48'))break;await pause(100);}
 assert.equal(await evaluate('window.ASSEMBLY.parts.length'),112);checks.push('112 parts loaded');
 await pause(150);const initial=await call('Page.captureScreenshot',{format:'png'});await writeFile(path.join(out,'previews','交互模型界面.png'),Buffer.from(initial.data,'base64'));
 await evaluate(`select('L1-C02'); $('onlyLayer').click()`);assert.equal(await evaluate('layers.size'),1);assert.equal(await evaluate("$('partTitle').textContent"),'L1-C02');checks.push('Select fitting and isolate floor');
 await evaluate(`$('search').value='L1-C02';$('search').dispatchEvent(new Event('input'))`);assert.equal(await evaluate('document.querySelectorAll("#list button").length'),1);checks.push('Search fitting');
 await evaluate(`$('search').value='';$('search').dispatchEvent(new Event('input'));$('showStraights').checked=false;$('showStraights').dispatchEvent(new Event('change'))`);assert.equal(await evaluate('visible().length'),9);checks.push('Hide straight trays');
 await evaluate(`$('showStraights').checked=true;$('allLayers').click();$('spread').click();$('top').click()`);assert.equal(await evaluate('spread'),true);assert.equal(await evaluate('layers.size'),3);checks.push('Show three floors and spread/top view');
 assert((await evaluate('rotate([1,0,0])[0]'))>0);assert((await evaluate('rotate([0,1,0])[1]'))<0);checks.push('North-up / east-right plan projection');
 await evaluate(`$('spread').click();$('resetDirection').click();$('reviewIssues').click()`);assert.equal(await evaluate('document.querySelectorAll("#list button").length'),4);assert.equal(await evaluate("$('partTitle').textContent"),'L3-X01');assert((await evaluate("$('partInfo').textContent")).includes('45°'));checks.push('Locate new 45-degree riser offset');
 // Exercise camera input through actual browser mouse and wheel events.
 const rect=await evaluate(`(()=>{const r=canvas.getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2};})()`);
 const oldYaw=await evaluate('yaw');await call('Input.dispatchMouseEvent',{type:'mousePressed',x:rect.x,y:rect.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:rect.x+40,y:rect.y+20,button:'left',buttons:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:rect.x+40,y:rect.y+20,button:'left',clickCount:1});assert.notEqual(await evaluate('yaw'),oldYaw);
 const oldZoom=await evaluate('zoom');await call('Input.dispatchMouseEvent',{type:'mouseWheel',x:rect.x,y:rect.y,deltaX:0,deltaY:-120});await pause(150);assert((await evaluate('zoom'))>oldZoom);checks.push('Pointer rotation and wheel zoom');
 for(const deltaY of [-350,350]){await call('Input.dispatchMouseEvent',{type:'mousePressed',x:rect.x,y:rect.y,button:'left',clickCount:1});await call('Input.dispatchMouseEvent',{type:'mouseMoved',x:rect.x,y:rect.y+deltaY,button:'left',buttons:1});await call('Input.dispatchMouseEvent',{type:'mouseReleased',x:rect.x,y:rect.y+deltaY,button:'left',clickCount:1});assert((await evaluate('pitch'))>=3*Math.PI/180-1e-10);assert((await evaluate('pitch'))<=Math.PI/2+1e-10);}
 await evaluate(`$('resetDirection').click()`);assert(Math.abs((await evaluate('yaw'))+Math.PI/4)<1e-10);assert(Math.abs((await evaluate('pitch'))-35*Math.PI/180)<1e-10);checks.push('Upright orbit limits and southeast direction reset');
 await evaluate(`select('L3-C04');$('detailFocus').click()`);assert((await evaluate("$('partWarnings').textContent")).includes('同侧边线'));await pause(200);const png=await call('Page.captureScreenshot',{format:'png'});await writeFile(path.join(out,'previews','接口核对示例.png'),Buffer.from(png.data,'base64'));
 await evaluate(`select('L3-C03');`);assert((await evaluate("$('partWarnings').textContent")).includes('底板对齐'));checks.push('Bottom and side-edge alignment details');
 await evaluate(`select('L3-S-37C11',false)`);assert((await evaluate("$('portLinks').textContent")).includes('L2-S-37C18'));assert((await evaluate("$('portLinks').textContent")).includes('L3-X01'));checks.push('Cross-floor riser adjacency');
 await evaluate(`select('L3-X01',false);layers=new Set([2,3]);syncLayers();refreshList();(()=>{const group=['L2-S-37C18','L3-S-37C11','L3-X01','L3-S-37C12'].map(id=>parts.get(id));const lo=[0,1,2].map(k=>Math.min(...group.map(p=>p.bbox_mm[0][k]))/1000),hi=[0,1,2].map(k=>Math.max(...group.map(p=>p.bbox_mm[1][k]))/1000);center=lo.map((v,i)=>(v+hi[i])/2);radius=Math.max(...lo.map((v,i)=>(hi[i]-v)/2))*1.1;zoom=1;pan=[0,0];requestDraw();})()`);await pause(200);const riser=await call('Page.captureScreenshot',{format:'png'});await writeFile(path.join(out,'previews','东南立管连接.png'),Buffer.from(riser.data,'base64'));
 assert.equal(errors.length,0,errors.join('\n'));const report={status:'passed',browser:'Chrome headless',checks,uncaught_exceptions:errors};await writeFile(path.join(out,'reports','browser_check.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 await call('Browser.close').catch(()=>{});
}finally{if(ws)ws.close();proc.kill();}
