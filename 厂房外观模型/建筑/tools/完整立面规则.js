// Preserved complete facade details from the original standalone building viewer.
function outline(side,u0,u1,z0,z1,color='#70c7c5',width=1){line(worldSide(side,u0,z0),worldSide(side,u1,z0),color,width);line(worldSide(side,u1,z0),worldSide(side,u1,z1),color,width);line(worldSide(side,u1,z1),worldSide(side,u0,z1),color,width);line(worldSide(side,u0,z1),worldSide(side,u0,z0),color,width)}
function worldSide(side,u,z){return side==='south'?[u,0,z]:side==='north'?[u,72650,z]:side==='west'?[0,u,z]:[44650,u,z]}
function facade(side){const endWall=side==='south'||side==='north';
 const length=endWall?W:D,wallColor=endWall?'#81929c':'#788a95',open=[];
 for(const o of FACADE.openings.filter(v=>v.side===side)){const u0=Math.max(0,o.center-o.width/2),u1=Math.min(length,o.center+o.width/2);if(o.kind==='door'){const z0=o.sill||0;open.push({u0,u1,z0,z1:z0+o.height,kind:'door'})}else open.push({u0,u1,z0:o.sill,z1:o.head,kind:'window'})}
 const cuts=[0,length,...open.flatMap(o=>[o.u0,o.u1])].sort((a,b)=>a-b).filter((v,i,a)=>i===0||v-a[i-1]>.5);
 for(let i=0;i<cuts.length-1;i++){const u0=cuts[i],u1=cuts[i+1],mid=(u0+u1)/2,holes=open.filter(o=>mid>o.u0&&mid<o.u1).map(o=>[o.z0,o.z1]).sort((a,b)=>a[0]-b[0]);let cursor=0;for(const [a,b] of holes){if(a>cursor+1)face([worldSide(side,u0,cursor),worldSide(side,u1,cursor),worldSide(side,u1,a),worldSide(side,u0,a)],wallColor,.99);cursor=Math.max(cursor,b)}if(cursor<ROOF)face([worldSide(side,u0,cursor),worldSide(side,u1,cursor),worldSide(side,u1,ROOF),worldSide(side,u0,ROOF)],wallColor,.99)}
 for(const o of open){const a=worldSide(side,o.u0,o.z0),b=worldSide(side,o.u1,o.z0),cc=worldSide(side,o.u1,o.z1),d=worldSide(side,o.u0,o.z1),frame=o.kind==='door'?'#e5edef':'#70c7c5',leaf='#c4d3d8';if(o.kind==='window'){
  face([a,b,cc,d],'#438395',.78,false);const midU=(o.u0+o.u1)/2,midZ=(o.z0+o.z1)/2;
  if(side==='west'&&o.u1-o.u0>=2800&&o.z1-o.z0>=800){outline(side,o.u0,o.u1,o.z0,o.z1,frame,2);for(let i=1;i<5;i++){const u=o.u0+(o.u1-o.u0)*i/5;line(worldSide(side,u,o.z0),worldSide(side,u,o.z1),frame,1.2)}for(let j=1;j<3;j++){const z=o.z0+(o.z1-o.z0)*j/3;line(worldSide(side,o.u0,z),worldSide(side,o.u1,z),frame,1.2)}}
  else{line(a,b,frame,2);line(b,cc,frame,2);line(cc,d,frame,2);line(d,a,frame,2);line(worldSide(side,midU,o.z0),worldSide(side,midU,o.z1),frame,1.5);line(worldSide(side,o.u0,midZ),worldSide(side,o.u1,midZ),frame,1.5)}
 }else{
  face([a,b,cc,d],'#91a6b1',1,false);line(a,b,frame,2.2);line(b,cc,frame,2.2);line(cc,d,frame,2.2);line(d,a,frame,2.2);
  const span=o.u1-o.u0,mid=(o.u0+o.u1)/2,sections=span>1700?[[o.u0,mid],[mid,o.u1]]:[[o.u0,o.u1]],band=Math.min(900,(o.z1-o.z0)*.30),cell=520;
  if(side==='west'&&span>=2800){
   // West m3036 gate: 3.0 x 3.6 m, 300 mm sill, with an 800 mm mesh band.
   // Reflect the asymmetric personnel panel with the west elevation's L-to-A orientation.
   const z0=o.z0,z1=o.z1,mesh0=z0+50,mesh1=z1-2800,upper0=z1-2750,upper1=z1-50;
   outline(side,o.u0+50,o.u0+1450,upper0,upper1,frame,1.4);outline(side,o.u0+1550,o.u0+2950,upper0,upper1,frame,1.4);
   line(worldSide(side,o.u0+1500,z0),worldSide(side,o.u0+1500,z1),frame,1.7);
   const panels=[[50,725],[775,1450],[1550,2250],[2300,2950]],step=260;
   for(const [a0,a1] of panels){const x0=o.u0+a0,x1=o.u0+a1;outline(side,x0,x1,mesh0,mesh1,frame,1.1);for(let u=x0;u<x1;u+=step)for(let z=mesh0;z<mesh1;z+=step){const v=Math.min(u+step,x1),w=Math.min(z+step,mesh1);line(worldSide(side,u,z),worldSide(side,v,w),leaf,.65);line(worldSide(side,u,w),worldSide(side,v,z),leaf,.65)}}
   // Personnel-door frame is on the source block's right leaf; west-view normalization mirrors it toward the center seam.
   outline(side,o.u0+700,o.u0+1450,mesh0,z1-1600,frame,1.2);outline(side,o.u0+800,o.u0+1400,z1-2750,z1-1650,leaf,.8);
  }else if(side==='south'&&span>=4500){
   // South M4848 double gate copied from the drawing block proportions.
   const z0=o.z0,z1=o.z1;
   for(const [x0,x1] of [[o.u0+50,mid-50],[mid+50,o.u1-50]]){line(worldSide(side,x0,z0+50),worldSide(side,x1,z0+50),frame,1.4);line(worldSide(side,x1,z0+50),worldSide(side,x1,z1-50),frame,1.4);line(worldSide(side,x1,z1-50),worldSide(side,x0,z1-50),frame,1.4);line(worldSide(side,x0,z1-50),worldSide(side,x0,z0+50),frame,1.4)}
   line(worldSide(side,mid,z0),worldSide(side,mid,z1),frame,1.7);
   const wz0=z1-1470,wz1=z1-1170;
   for(const [a0,a1] of [[300,900],[1200,1800],[3000,3600],[3900,4500]]){const x0=o.u0+a0,x1=o.u0+a1;line(worldSide(side,x0,wz0),worldSide(side,x1,wz0),frame,1.4);line(worldSide(side,x1,wz0),worldSide(side,x1,wz1),frame,1.4);line(worldSide(side,x1,wz1),worldSide(side,x0,wz1),frame,1.4);line(worldSide(side,x0,wz1),worldSide(side,x0,wz0),frame,1.4);line(worldSide(side,x0+30,wz0+30),worldSide(side,x1-30,wz0+30),leaf,.7);line(worldSide(side,x1-30,wz0+30),worldSide(side,x1-30,wz1-30),leaf,.7);line(worldSide(side,x1-30,wz1-30),worldSide(side,x0+30,wz1-30),leaf,.7);line(worldSide(side,x0+30,wz1-30),worldSide(side,x0+30,wz0+30),leaf,.7)}
   const px0=o.u0+1025,px1=o.u0+2075,pz0=z0,pz1=z0+2200;line(worldSide(side,px0,pz0),worldSide(side,px1,pz0),leaf,1);line(worldSide(side,px1,pz0),worldSide(side,px1,pz1),leaf,1);line(worldSide(side,px1,pz1),worldSide(side,px0,pz1),leaf,1);line(worldSide(side,px0,pz1),worldSide(side,px0,pz0),leaf,1);line(worldSide(side,px0+50,pz0+50),worldSide(side,px1-50,pz0+50),leaf,.7);line(worldSide(side,px1-50,pz0+50),worldSide(side,px1-50,pz1-50),leaf,.7);line(worldSide(side,px1-50,pz1-50),worldSide(side,px0+50,pz1-50),leaf,.7);line(worldSide(side,px0+50,pz1-50),worldSide(side,px0+50,pz0+50),leaf,.7)
  }else{
   // Other industrial doors keep the simpler restrained panel and kick-plate style.
   for(const [x0,x1] of sections){line(worldSide(side,x0+50,o.z0+40),worldSide(side,x0+50,o.z1-40),frame,1.4);line(worldSide(side,x1-50,o.z0+40),worldSide(side,x1-50,o.z1-40),frame,1.4)}
   if(sections.length===2)line(worldSide(side,mid,o.z0),worldSide(side,mid,o.z1),frame,1.7);
   line(worldSide(side,o.u0,o.z0+band),worldSide(side,o.u1,o.z0+band),frame,1.2);
   for(let u=o.u0;u<o.u1;u+=cell)for(let z=o.z0;z<o.z0+band;z+=cell){const u1=Math.min(u+cell,o.u1),z1=Math.min(z+cell,o.z0+band);line(worldSide(side,u,z),worldSide(side,u1,z1),leaf,.7);line(worldSide(side,u,z1),worldSide(side,u1,z),leaf,.7)}
  }
 }}
}
