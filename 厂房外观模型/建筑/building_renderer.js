// Independent building renderer; adapted from the existing offline orthographic engine.
// Shared offline orthographic renderer for equipment type models.
function createBuildingViewer(canvas, {doubleSided=false, centerProjection=false, onFrame=()=>{}}={}) {
    const gl = canvas.getContext('webgl', { alpha:true, antialias:true });
    if (!gl) throw new Error('Missing WebGL');
    const vertex = [
      'attribute vec3 p, n, c; uniform vec3 pivot, right, up; uniform mediump vec3 eye;',
      'uniform vec2 scale, offset; uniform float depth; uniform mediump float strokeDepth; varying vec3 normal, color; varying float worldZ;',
      'void main(){vec3 v=p-pivot;normal=n;color=c;',
      'worldZ=p.z;gl_Position=vec4(vec2(dot(v,right),dot(v,up))*scale+offset,-dot(v,eye)/depth-strokeDepth,1.0);}'
    ].join('\n');
    const fragment = [
      'precision mediump float; uniform mediump vec3 eye; varying vec3 normal, color; varying float worldZ;',
      'uniform vec2 section; uniform mediump float strokeDepth;',
      window.BUILDING_STYLE.shader,
      'void main(){if(worldZ<section.x||worldZ>section.y)discard;',
      '  vec3 n=normalize(gl_FrontFacing?normal:-normal);',
      '  gl_FragColor=vec4(strokeDepth>0.0?color:buildingShade(color,n),1.0);',
      '}'
    ].join('\n');
    const program = gl.createProgram();
    for (const [type, source] of [[gl.VERTEX_SHADER,vertex],[gl.FRAGMENT_SHADER,fragment]]) {
      const shader = gl.createShader(type);
      gl.shaderSource(shader,source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(shader));
      gl.attachShader(program,shader);
    }
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    gl.useProgram(program);
    gl.enable(gl.DEPTH_TEST);
    if (!doubleSided) gl.enable(gl.CULL_FACE);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    const attributes=['p','n','c'].map(name=>gl.getAttribLocation(program,name));
    function bindGeometry(target){
      gl.bindBuffer(gl.ARRAY_BUFFER,target);
      attributes.forEach((attribute,i)=>{
        gl.enableVertexAttribArray(attribute);
        gl.vertexAttribPointer(attribute,3,gl.FLOAT,false,36,12*i);
      });
    }
    bindGeometry(buffer);
    const strokeBuffer=gl.createBuffer();let strokeCount=0;
    const uniforms = Object.fromEntries(['pivot','right','up','eye','scale','offset','depth','section','strokeDepth']
      .map(name=>[name,gl.getUniformLocation(program,name)]));
    let yaw=-Math.PI/4, tilt=.36, zoom=1, drag=null, pan=[0,0], aim=[0,0];
    let center=[0,0,0], radius=1, vertexCount=0, points=[];
    let section=[-2000,50000];
    let overlayRanges=[],drawRanges=[];
    let viewName='东南轴测';

    function setParts(parts) {
      const low=[Infinity,Infinity,Infinity], high=[-Infinity,-Infinity,-Infinity];
      const data=[],strokes=[];
      points=[];overlayRanges=[];drawRanges=[];
      for (const part of parts) {
        strokes.push(...BUILDING_STYLE.strokes(part));
        const rangeStart=data.length/9;
        const color=[1,3,5].map(i=>parseInt(window.BUILDING_STYLE.color(part).slice(i,i+2),16)/255);
        for (const point of part.vertices) {
          points.push(point);
          point.forEach((v,k)=>{low[k]=Math.min(low[k],v); high[k]=Math.max(high[k],v);});
        }
        part.faces.forEach((face,j)=>{
          let fallback;
          if (!part.normals?.[j]) {
            const [a,b,c]=face.slice(0,3).map(index=>part.vertices[index]);
            const u=b.map((x,i)=>x-a[i]), v=c.map((x,i)=>x-a[i]);
            const cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
            const length=Math.hypot(...cross)||1;
            fallback=cross.map(value=>value/length);
          }
          for(let i=1;i<face.length-1;i++) for(const corner of [0,i,i+1]) {
            data.push(...part.vertices[face[corner]],...(part.normals?.[j]?.[corner]||fallback),...color);
          }
        });
        drawRanges.push({start:rangeStart,count:data.length/9-rangeStart,wall:part.kind==='wall'});
        if(part.kind==='roof')overlayRanges.push({start:rangeStart,count:data.length/9-rangeStart});
      }
      center=points.length ? low.map((v,i)=>(v+high[i])/2) : [0,0,0];
      radius=1;
      for (const [x,y,z] of points) radius=Math.max(radius,Math.hypot(x-center[0],y-center[1],z-center[2]));
      vertexCount=data.length/9;
      bindGeometry(strokeBuffer);strokeCount=strokes.length/9;
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(strokes),gl.STATIC_DRAW);
      bindGeometry(buffer);
      gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(data),gl.STATIC_DRAW);
      fit();
    }

    function axes() {
      const c=Math.cos(tilt), s=Math.sin(tilt), x=Math.cos(yaw), y=Math.sin(yaw);
      return {right:[-y,x,0],up:[-s*x,-s*y,c],eye:[c*x,c*y,s]};
    }
    const dot = (a,b) => a[0]*b[0]+a[1]*b[1]+a[2]*b[2];
    function recenter() {
      aim=[0,0];
      if (!centerProjection || !points.length) return;
      const {right,up}=axes();
      const low=[Infinity,Infinity], high=[-Infinity,-Infinity];
      for (const point of points) {
        const v=point.map((value,i)=>value-center[i]);
        const xy=[dot(v,right),dot(v,up)];
        xy.forEach((value,i)=>{low[i]=Math.min(low[i],value);high[i]=Math.max(high[i],value);});
      }
      aim=low.map((value,i)=>(value+high[i])/2);
    }
    function fit() {
      zoom=1;
      pan=[0,0];
      recenter();
      zoom=BUILDING_STYLE.fitZoom(canvas,points,radius,centerProjection ? .82 : .92,yaw,tilt);
      draw();
    }
    function draw() {
      const {width,height}=canvas.getBoundingClientRect();
      if (!width || !height) return;
      const d=devicePixelRatio||1;
      const w=Math.max(1,Math.round(width*d)), h=Math.max(1,Math.round(height*d));
      if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h;}
      const {right,up,eye}=axes();
      const fill=centerProjection ? .82 : .92;
      const pixelsPerMm=fill*zoom*Math.min(width,height)/(2*radius);
      const offset=[pan[0]-aim[0]*pixelsPerMm, -pan[1]-aim[1]*pixelsPerMm];
      gl.viewport(0,0,w,h);
      gl.clearColor(0,0,0,0);
      gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
      gl.uniform3fv(uniforms.pivot,center);
      gl.uniform3fv(uniforms.right,right);
      gl.uniform3fv(uniforms.up,up);
      gl.uniform3fv(uniforms.eye,eye);
      gl.uniform2f(uniforms.scale,2*pixelsPerMm/width,2*pixelsPerMm/height);
      gl.uniform2f(uniforms.offset,2*offset[0]/width,2*offset[1]/height);
      gl.uniform1f(uniforms.depth,radius*1.05);
      gl.uniform2fv(uniforms.section,section);
      gl.uniform1f(uniforms.strokeDepth,0);
      // Prefer the continuous facade at coplanar wall/column faces.
      // Raster depth only: columns stay complete for structure and interior views.
      for(const range of drawRanges){
        if(range.wall){gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(-1,-8);}
        else gl.disable(gl.POLYGON_OFFSET_FILL);
        gl.drawArrays(gl.TRIANGLES,range.start,range.count);
      }
      gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(-1,-1);
      for(const range of overlayRanges)gl.drawArrays(gl.TRIANGLES,range.start,range.count);
      gl.disable(gl.POLYGON_OFFSET_FILL);
      if(strokeCount){
        bindGeometry(strokeBuffer);gl.depthMask(false);
        gl.uniform1f(uniforms.strokeDepth,24/(radius*1.05));
        gl.drawArrays(gl.LINES,0,strokeCount);
        gl.depthMask(true);gl.uniform1f(uniforms.strokeDepth,0);bindGeometry(buffer);
      }
      const project = point => {
        const v=point.map((value,i)=>value-center[i]);
        return [width/2+offset[0]+dot(v,right)*pixelsPerMm,
                height/2-offset[1]-dot(v,up)*pixelsPerMm];
      };
      const ray=(x,y)=>{
        const u=(x-width/2-offset[0])/pixelsPerMm,v=(height/2-offset[1]-y)/pixelsPerMm,depth=radius*1.05;
        return {origin:center.map((value,i)=>value+right[i]*u+up[i]*v+eye[i]*depth),direction:eye.map(value=>-value),maxDistance:2*depth};
      };
      onFrame({width,height,project,ray,clip:[...section],viewName,pixelsPerMm,hasModel:vertexCount>0});
    }
    function view(a,b,name){yaw=a;tilt=b;viewName=name;recenter();draw();}
    canvas.onpointerdown=e=>{
      if(e.button!==0 || drag)return;
      drag={id:e.pointerId,x:e.clientX,y:e.clientY,pan:e.shiftKey};
      canvas.setPointerCapture(e.pointerId);
    };
    canvas.onpointermove=e=>{
      if(drag?.id!==e.pointerId)return;
      const dx=e.clientX-drag.x, dy=e.clientY-drag.y;
      drag.x=e.clientX;
      drag.y=e.clientY;
      if (drag.pan || e.shiftKey) {
        pan[0]+=dx;
        pan[1]+=dy;
      } else {
        yaw+=dx*.008;
        tilt=Math.max(0,Math.min(Math.PI/2,tilt+dy*.006));
        viewName='自由旋转';
      }
      draw();
    };
    canvas.onpointerup=canvas.onpointercancel=canvas.onlostpointercapture=e=>{
      if (drag?.id===e.pointerId) drag=null;
    };
    canvas.addEventListener('wheel',e=>{
      e.preventDefault();
      const unit=e.deltaMode===1?16:e.deltaMode===2?canvas.clientHeight:1;
      const delta=Math.max(-140,Math.min(140,e.deltaY*unit));
      zoom=Math.max(.35,Math.min(5,zoom*Math.exp(-delta*.00055)));
      draw();
    },{passive:false});
    new ResizeObserver(draw).observe(canvas);
    return {setParts,view,fit,draw,focusBounds:(low,high)=>{center=low.map((v,i)=>(v+high[i])/2);radius=Math.max(1000,Math.hypot(...high.map((v,i)=>v-low[i]))*.65);points=[];for(const x of [low[0],high[0]])for(const y of [low[1],high[1]])for(const z of [low[2],high[2]])points.push([x,y,z]);fit();},setSection:(low,high)=>{section=[low,high];draw();}};
}
