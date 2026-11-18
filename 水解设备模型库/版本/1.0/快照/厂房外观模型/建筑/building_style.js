// Display-only reference theme. Never write back to the canonical mesh or transforms.
window.BUILDING_STYLE = Object.freeze({
  version: 'reference-matte-1',
  view: Object.freeze({yaw: -Math.PI / 3, tilt: 3 * Math.PI / 180}),
  fitZoom(canvas, points, radius, fill, yaw, tilt) {
    const right=[-Math.sin(yaw),Math.cos(yaw),0];
    const up=[-Math.sin(tilt)*Math.cos(yaw),-Math.sin(tilt)*Math.sin(yaw),Math.cos(tilt)];
    const low=[Infinity,Infinity],high=[-Infinity,-Infinity];
    for(const p of points)for(const [i,axis] of [right,up].entries()){
      const value=p.reduce((sum,x,k)=>sum+x*axis[k],0);
      low[i]=Math.min(low[i],value);high[i]=Math.max(high[i],value);
    }
    const {width,height}=canvas.getBoundingClientRect();
    if(!points.length||!width||!height)return 1;
    const ppm=Math.min(.90*width/Math.max(1,high[0]-low[0]),.78*height/Math.max(1,high[1]-low[1]));
    return ppm*2*radius/(fill*Math.min(width,height));
  },
  // Exported facade strokes are rectangular prisms: six quads / 24 vertices.
  // Reuse their end-cap centers for a one-pixel display pass, without changing the mesh.
  strokes(part) {
    if(part.kind!=='opening'||!['#e5edef','#70c7c5','#c4d3d8'].includes(part.color))return [];
    const lines=[];
    for(let i=0;i+23<part.vertices.length;i+=24){
      for(const start of [i,i+4]){
        const point=[0,1,2].map(k=>part.vertices.slice(start,start+4).reduce((s,v)=>s+v[k],0)/4);
        lines.push(...point,0,0,1,...[1,3,5].map(k=>parseInt(this.color(part).slice(k,k+2),16)/255));
      }
    }
    return lines;
  },
  color(part) {
    if (['wall', 'structure', 'frame', 'floor'].includes(part.kind)) return '#8a9fa8';
    if (part.kind === 'roof') return part.name.startsWith('ROOF-DOOR-') ? '#354b55' : '#8399a2';
    if (part.kind !== 'opening') return part.color;
    return ({
      '#91a6b1': '#354b55', // Dark door leaves, with clear cyan frames.
      '#e5edef': '#76cfcd',
      '#70c7c5': '#76cfcd',
      '#c4d3d8': '#c1d7d8',
      '#438395': '#497b89'
    })[part.color] || part.color;
  },
  // Identical matte building lighting in the standalone and assembly viewers.
  shader: `vec3 buildingShade(vec3 color, vec3 normal) {
    float key=max(0.0,dot(normal,normalize(vec3(.2,-.65,.75))));
    float fill=max(0.0,dot(normal,normalize(vec3(-.7,.3,.55))));
    float shade=.86+.13*key+.05*fill;
    if(color.g>color.r*1.25 && color.b>color.r*1.15)shade=1.0;
    return color*shade;
  }`
});
