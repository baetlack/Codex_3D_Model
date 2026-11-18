/* Shared, read-only architectural measurement. All coordinates and calculations use mm. */
(function(global){
'use strict';
const sub=(a,b)=>a.map((v,i)=>v-b[i]);
const add=(a,b)=>a.map((v,i)=>v+b[i]);
const scale=(a,s)=>a.map(v=>v*s);
const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const length=a=>Math.hypot(...a);
function metrics(a,b,mode='distance'){
  const delta=sub(b,a),distance=length(delta),horizontal=Math.hypot(delta[0],delta[1]);
  return {delta,distance,horizontal,value:mode==='height'?Math.abs(delta[2]):mode==='axis'?horizontal:distance};
}
function rayBox(ray,low,high){
  let near=0,far=ray.maxDistance;
  for(let k=0;k<3;k++){
    if(Math.abs(ray.direction[k])<1e-12){if(ray.origin[k]<low[k]-.001||ray.origin[k]>high[k]+.001)return false;}
    else{
      let a=(low[k]-ray.origin[k])/ray.direction[k],b=(high[k]-ray.origin[k])/ray.direction[k];
      if(a>b)[a,b]=[b,a];near=Math.max(near,a);far=Math.min(far,b);if(near>far+.001)return false;
    }
  }
  return true;
}
function rayTriangle(ray,triangle){
  const {a,e1,e2}=triangle,p=cross(ray.direction,e2),det=dot(e1,p);
  if(Math.abs(det)<1e-9)return null;
  const v=sub(ray.origin,a),u=dot(v,p)/det;
  if(u< -1e-8||u>1+1e-8)return null;
  const q=cross(v,e1),w=dot(ray.direction,q)/det;
  if(w< -1e-8||u+w>1+1e-8)return null;
  const t=dot(e2,q)/det;
  return t>=-.001&&t<=ray.maxDistance+.001?Math.max(0,t):null;
}
function create({canvas,host,toolbar,model}){
  const panel=document.createElement('section');panel.className='building-measure';panel.hidden=true;
  panel.innerHTML=`<h2>建筑尺寸测量</h2>
    <label>测量方式<select id="measureMode"><option value="distance">两点距离 / 净距</option><option value="height">层高 / 竖向高差</option><option value="axis">立柱轴线间距</option><option value="bounds">构件尺寸</option></select></label>
    <label>显示单位<select id="measureUnit"><option value="mm">毫米 mm</option><option value="m">米 m</option></select></label>
    <div id="measureLevels" hidden><span>也可按楼层标高计算</span><div class="measure-levels"><select id="measureLevelA" aria-label="起始楼层"></select><select id="measureLevelB" aria-label="终止楼层"></select></div><button id="measureHeight" type="button">计算层高</button></div>
    <p id="measureHelp" class="measure-help"></p><p id="measureStatus" role="status" aria-live="polite"></p>
    <div id="measureResult" aria-live="polite"></div>
    <div class="measure-actions"><button id="measureUndo" type="button">撤销一点</button><button id="measureClear" type="button">清空测量</button></div>
    <p class="measure-note">仅拾取当前显示的建筑构件，按模型坐标计算。角点、边线可吸附；拖动仍可旋转，Shift 拖动平移。尺寸精度沿用源模型，示意构件需结合图纸复核。</p>`;
  host.prepend(panel);
  const toggle=document.createElement('button');toggle.id='measureToggle';toggle.type='button';toggle.textContent='测量尺寸';toggle.setAttribute('aria-pressed','false');toolbar.append(toggle);
  const layer=document.createElement('canvas');layer.className='measure-overlay';layer.setAttribute('aria-hidden','true');canvas.parentElement.append(layer);
  const ctx=layer.getContext('2d'),$=id=>panel.querySelector('#'+id),cache=new WeakMap();
  let active=false,mode='distance',unit='mm',points=[],info=null,hover=null,frame=null,start=null,hoverFrame=0,lastPointer=null;
  const floors=model.parts.filter(p=>p.kind==='floor'&&Number.isFinite(p.el)).sort((a,b)=>a.el-b.el);
  for(const id of ['measureLevelA','measureLevelB'])for(const p of floors){const option=document.createElement('option');option.value=p.el;option.textContent='EL'+p.el;$(id).append(option);}
  if(floors.length>1)$('measureLevelB').selectedIndex=1;
  function data(part){
    let entry=cache.get(part);if(entry)return entry;
    const low=[Infinity,Infinity,Infinity],high=[-Infinity,-Infinity,-Infinity];
    for(const p of part.vertices)for(let k=0;k<3;k++){low[k]=Math.min(low[k],p[k]);high[k]=Math.max(high[k],p[k]);}
    entry={part,low,high};cache.set(part,entry);return entry;
  }
  function mesh(entry){
    if(entry.triangles)return entry;
    const vertices=[],indices=new Map(),mapped=[];
    for(const v of entry.part.vertices){const key=v.join(',');if(!indices.has(key)){indices.set(key,vertices.length);vertices.push(v);}mapped.push(indices.get(key));}
    const triangles=[],edges=new Map();
    for(const face of entry.part.faces)for(let i=1;i<face.length-1;i++){
      const ids=[face[0],face[i],face[i+1]].map(k=>mapped[k]),a=vertices[ids[0]],e1=sub(vertices[ids[1]],a),e2=sub(vertices[ids[2]],a),n=cross(e1,e2),size=length(n);
      if(size<1e-8)continue;const normal=scale(n,1/size);triangles.push({a,e1,e2});
      for(const [a,b] of [[ids[0],ids[1]],[ids[1],ids[2]],[ids[2],ids[0]]]){
        const key=Math.min(a,b)+':'+Math.max(a,b);
        if(!edges.has(key))edges.set(key,{a:vertices[a],b:vertices[b],normals:[]});edges.get(key).normals.push(normal);
      }
    }
    entry.triangles=triangles;entry.vertices=vertices;
    entry.edges=[...edges.values()].filter(e=>e.normals.length===1||e.normals.some(n=>Math.abs(dot(n,e.normals[0]))<.99999));
    return entry;
  }
  function clipped(p){return p[2]<frame.clip[0]-.001||p[2]>frame.clip[1]+.001;}
  function entries(){return frame.parts.filter(p=>!frame.through?.includes(p.kind)||p.kind==='floor'&&mode!=='axis').map(data);}
  function cast(ray){
    let best=null;
    for(const entry of entries()){
      if(entry.high[2]<frame.clip[0]||entry.low[2]>frame.clip[1]||!rayBox(ray,entry.low,entry.high))continue;
      for(const triangle of mesh(entry).triangles){
        const t=rayTriangle(ray,triangle);if(t===null||best&&t>best.t+.01)continue;
        const point=add(ray.origin,scale(ray.direction,t));if(clipped(point))continue;
        // The facade wins coplanar ties, matching the shared visual theme.
        if(!best||t<best.t-.01||Math.abs(t-best.t)<=.01&&entry.part.kind==='wall')best={entry,point,t};
      }
    }
    return best;
  }
  function visiblePoint(point,entry){
    if(clipped(point))return false;
    const q=frame.project(point),ray=frame.ray(...q),t=dot(sub(point,ray.origin),ray.direction);
    if(t<-.001||t>ray.maxDistance+.001)return false;
    const hit=cast(ray);
    return !hit||t<=hit.t+1&&(!entry||hit.entry===entry||t<hit.t-.01);
  }
  function pick(x,y){
    if(!frame)return null;
    const hit=cast(frame.ray(x,y));
    if(mode==='axis'){
      if(!hit)return null;const part=hit.entry.part;
      if(!['structure','room_column'].includes(part.kind))return {blocked:true};
      return {point:[(hit.entry.low[0]+hit.entry.high[0])/2,(hit.entry.low[1]+hit.entry.high[1])/2,hit.point[2]],part:part.name,type:'柱轴线',entry:hit.entry};
    }
    if(mode==='bounds')return hit?{point:hit.point,part:hit.entry.part.name,type:'构件',entry:hit.entry}:null;
    // Search around the pointer as well as on its ray: an exact projected corner
    // may fall just outside a face after browser pixel rounding.
    const nearby=entries().filter(entry=>{
      if(entry.high[2]<frame.clip[0]||entry.low[2]>frame.clip[1])return false;
      const low=[Infinity,Infinity],high=[-Infinity,-Infinity];
      for(const x of [entry.low[0],entry.high[0]])for(const y of [entry.low[1],entry.high[1]])for(const z of [entry.low[2],entry.high[2]]){
        const q=frame.project([x,y,z]);for(let k=0;k<2;k++){low[k]=Math.min(low[k],q[k]);high[k]=Math.max(high[k],q[k]);}
      }
      return x>=low[0]-12&&x<=high[0]+12&&y>=low[1]-12&&y<=high[1]+12;
    });
    const candidates=[];
    function candidate(point,type,entry){
      if(clipped(point))return;const q=frame.project(point),d=Math.hypot(q[0]-x,q[1]-y);
      if(d<=12)candidates.push({point,type,d,entry});
    }
    for(const entry of nearby){
      const m=mesh(entry);for(const v of m.vertices)candidate(v,'角点',entry);
      for(const edge of m.edges)for(const z of frame.clip){
        const dz=edge.b[2]-edge.a[2];if(Math.abs(dz)<1e-8)continue;const t=(z-edge.a[2])/dz;
        if(t>0&&t<1)candidate(add(edge.a,scale(sub(edge.b,edge.a),t)),'剖切交点',entry);
      }
    }
    candidates.sort((a,b)=>a.d-b.d);
    let snap=candidates.find(c=>visiblePoint(c.point,c.entry));
    if(!snap){
      const edgeCandidates=[];
      for(const entry of nearby)for(const edge of mesh(entry).edges){
        const a=frame.project(edge.a),b=frame.project(edge.b),d=sub(b,a),size=dot(d,d);if(size<1e-8)continue;
        const t=Math.max(0,Math.min(1,((x-a[0])*d[0]+(y-a[1])*d[1])/size)),point=add(edge.a,scale(sub(edge.b,edge.a),t)),q=frame.project(point),distance=Math.hypot(q[0]-x,q[1]-y);
        if(distance<=8&&!clipped(point))edgeCandidates.push({point,type:'边线',d:distance,entry});
      }
      edgeCandidates.sort((a,b)=>a.d-b.d);snap=edgeCandidates.find(c=>visiblePoint(c.point,c.entry));
    }
    if(snap)return {point:snap.point,part:snap.entry.part.name,type:snap.type,entry:snap.entry};
    return hit?{point:hit.point,part:hit.entry.part.name,type:'表面',entry:hit.entry}:null;
  }
  const fmt=n=>Number((n/(unit==='m'?1000:1)).toFixed(unit==='m'?3:1)).toLocaleString('zh-CN',{maximumFractionDigits:unit==='m'?3:1})+' '+unit;
  const el=z=>'EL'+(100+z/1000).toFixed(3);
  function text(tag,value,parent=$('measureResult')){const node=document.createElement(tag);node.textContent=value;parent.append(node);return node;}
  function result(){
    const target=$('measureResult');target.replaceChildren();
    if(info){
      const size=sub(info.high,info.low),column=['structure','room_column'].includes(info.part.kind);
      text('strong',column?'柱截面 '+fmt(size[0])+' × '+fmt(size[1]):'构件包络尺寸');
      text('p',info.part.label||info.part.name);text('p','X '+fmt(size[0])+' · Y '+fmt(size[1])+' · 高 '+fmt(size[2]));
      text('p','底 '+el(info.low[2])+' / 顶 '+el(info.high[2]));
      if(info.part.thickness_status)text('small',info.part.thickness_status);
      if(info.part.kind==='wall')text('small','外墙为立面显示面，不代表实体墙厚。');
      if(info.part.kind==='frame')text('small','梁架截面为现有示意模型尺寸。');
      return;
    }
    if(points.length===2){
      const value=metrics(points[0].point,points[1].point,mode);
      text('strong',({distance:'空间距离 ',height:'竖向高差 ',axis:'柱轴中心距 '})[mode]+fmt(value.value));
      text('p','X向 '+fmt(Math.abs(value.delta[0]))+' · Y向 '+fmt(Math.abs(value.delta[1]))+' · Z向 '+fmt(Math.abs(value.delta[2])));
      if(mode==='distance')text('p','水平距离 '+fmt(value.horizontal));
    }
    points.forEach((p,i)=>{text('p',(i?'B':'A')+' · '+p.type+' · '+p.part);text('small','X '+fmt(p.point[0])+' / Y '+fmt(p.point[1])+' / '+el(p.point[2]));});
  }
  function hint(){
    $('measureHelp').textContent=({distance:'依次点击两个建筑表面点。角点优先吸附；X/Y/Z 分量可用于检查净距。',height:'点击两个测点读取竖向高差，或选择两个楼层标高计算层高。',axis:'先隐藏外墙或进入内部查看，再依次点击两根柱。结果为水平轴线中心距。',bounds:'点击柱、梁、板等构件，查看 X/Y/高度包络尺寸；柱截面可直接读取。'})[mode];
    $('measureLevels').hidden=mode!=='height';
    $('measureStatus').textContent=mode==='bounds'?'请选择建筑构件':points.length===1?'已取 A 点，请选择 B 点':points.length===2?'测量完成；再次点击可开始新测量':'请选择 A 点';
  }
  function changeMode(){mode=$('measureMode').value;points=[];info=null;hover=null;hint();result();draw();}
  function clear(){points=[];info=null;hover=null;hint();result();draw();}
  function accept(hit){
    if(!hit){$('measureStatus').textContent='未命中可见建筑，请点击构件表面';return;}
    if(hit.blocked){$('measureStatus').textContent='请点击立柱；可先隐藏外墙或使用内部查看';return;}
    hover=null;
    if(mode==='bounds'){info=hit.entry;points=[];$('measureStatus').textContent='已读取构件尺寸';result();draw();return;}
    info=null;if(points.length===2)points=[];
    if(points.length&&mode==='axis'){
      if(points[0].part===hit.part){$('measureStatus').textContent='请选择另一根柱';return;}
      hit={...hit,point:[hit.point[0],hit.point[1],points[0].point[2]]};
    }
    if(points.length&&length(sub(points[0].point,hit.point))<1e-5){$('measureStatus').textContent='测点重合，请重新选择终点';return;}
    points.push({point:[...hit.point],part:hit.part,type:hit.type});hint();result();draw();
  }
  function marker(point,label,color){
    const q=frame.project(point);ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(q[0],q[1],5,0,Math.PI*2);ctx.stroke();ctx.fillText(label,q[0]+9,q[1]-8);return q;
  }
  function line(a,b,dashed=false){const p=frame.project(a),q=frame.project(b);ctx.setLineDash(dashed?[5,4]:[]);ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();ctx.setLineDash([]);}
  function draw(){
    const {width,height}=canvas.getBoundingClientRect(),dpr=global.devicePixelRatio||1;
    if(layer.width!==Math.round(width*dpr)||layer.height!==Math.round(height*dpr)){layer.width=Math.round(width*dpr);layer.height=Math.round(height*dpr);}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,width,height);if(!active||!frame)return;
    ctx.font='12px system-ui';ctx.lineWidth=1.5;ctx.strokeStyle='#f5cc83';ctx.fillStyle='#f5cc83';
    if(info&&frame.parts.some(p=>p.name===info.part.name)){
      const p=[];for(const x of [info.low[0],info.high[0]])for(const y of [info.low[1],info.high[1]])for(const z of [info.low[2],info.high[2]])p.push([x,y,z]);
      for(let i=0;i<8;i++)for(const bit of [1,2,4])if(!(i&bit))line(p[i],p[i|bit],true);
    }
    const visible=points.every(p=>!clipped(p.point)&&(p.reference||frame.parts.some(part=>part.name===p.part)));
    if(visible&&points.length){
      points.forEach((p,i)=>marker(p.point,i?'B':'A','#f5cc83'));
      if(points.length===2){
        const [a,b]=points.map(p=>p.point),value=metrics(a,b,mode);let end=b;
        if(mode==='height'){end=[a[0],a[1],b[2]];line(end,b,true);}
        line(a,end);const q=frame.project(scale(add(a,end),.5)),label=fmt(value.value),w=ctx.measureText(label).width;
        ctx.fillStyle='#101922ed';ctx.fillRect(q[0]-w/2-7,q[1]-23,w+14,22);ctx.fillStyle='#f5cc83';ctx.fillText(label,q[0]-w/2,q[1]-8);
      }
    }
    if(hover&&!hover.blocked&&points.every(p=>length(sub(frame.project(p.point),frame.project(hover.point)))>8))marker(hover.point,hover.type,'#88e2dc');
  }
  function setActive(value){active=value;toggle.classList.toggle('active',active);toggle.setAttribute('aria-pressed',String(active));panel.hidden=!active;canvas.classList.toggle('measurement-active',active);hover=null;if(active)panel.scrollIntoView({block:'nearest'});hint();result();draw();}
  toggle.onclick=()=>setActive(!active);$('measureMode').onchange=changeMode;
  $('measureUnit').onchange=()=>{unit=$('measureUnit').value;result();draw();};$('measureClear').onclick=clear;
  $('measureUndo').onclick=()=>{if(info)info=null;else points.pop();hover=null;hint();result();draw();};
  $('measureHeight').onclick=()=>{
    const a=floors.find(p=>p.el===Number($('measureLevelA').value)),b=floors.find(p=>p.el===Number($('measureLevelB').value));
    if(!a||!b||a===b){$('measureStatus').textContent='请选择两个不同楼层';return;}
    const anchor=data(a).low;points=[a,b].map(p=>({point:[anchor[0],anchor[1],(p.el-100)*1000],part:p.name,type:'楼层标高基准',reference:true}));info=null;hover=null;hint();$('measureStatus').textContent='按楼层标高计算；可继续点击模型重新测量';result();draw();
  };
  canvas.addEventListener('pointerdown',e=>{if(e.button===0)start={id:e.pointerId,x:e.clientX,y:e.clientY,shift:e.shiftKey};});
  canvas.addEventListener('pointerup',e=>{
    if(active&&start?.id===e.pointerId&&!start.shift&&!e.shiftKey&&Math.hypot(e.clientX-start.x,e.clientY-start.y)<4){const r=canvas.getBoundingClientRect();accept(pick(e.clientX-r.left,e.clientY-r.top));}start=null;
  });
  canvas.addEventListener('pointercancel',()=>{start=null;hover=null;draw();});
  canvas.addEventListener('pointerleave',()=>{hover=null;draw();});
  canvas.addEventListener('pointermove',e=>{
    if(!active||start){hover=null;return;}
    const r=canvas.getBoundingClientRect();lastPointer=[e.clientX-r.left,e.clientY-r.top];
    if(!hoverFrame)hoverFrame=requestAnimationFrame(()=>{hoverFrame=0;if(!active)return;hover=pick(...lastPointer);draw();});
  });
  document.addEventListener('keydown',e=>{
    if(e.key!=='Escape'||!active||e.target.matches('input,select,textarea'))return;
    if(points.length||info)clear();else setActive(false);
  });
  return {get active(){return active;},setFrame(value){frame=value;hover=null;draw();},
    getState:()=>({active,mode,unit,points:points.map(p=>({...p,point:[...p.point]})),info:info?{name:info.part.name,low:[...info.low],high:[...info.high]}:null,result:points.length===2?metrics(points[0].point,points[1].point,mode):null}),
    project:point=>frame?.project(point)};
}
global.BuildingMeasure={create,geometry:{metrics,rayBox,rayTriangle}};
})(typeof window==='undefined'?globalThis:window);
