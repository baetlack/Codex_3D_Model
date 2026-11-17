// Export the same door/window/frame rules used by the complete standalone facade.
const fs=require('fs'),vm=require('vm');const root=process.argv[2];
const FACADE=JSON.parse(fs.readFileSync(root+'/立面门窗数据.json','utf8'));
const groups=new Map();let side='';
function add(points,color,kind){const key=side+'-'+kind+'-'+color;let p=groups.get(key);if(!p){p={name:'FACADE-'+key,kind,color,vertices:[],faces:[]};groups.set(key,p);}const start=p.vertices.length;p.vertices.push(...points.map(v=>[v[0]-325,v[1]-325,v[2]]));for(let i=1;i<points.length-1;i++)p.faces.push([start,start+i,start+i+1]);}
function face(points,color){add(points,color,['#81929c','#788a95'].includes(color)?'wall':'opening');}
function line(a,b,color,width=1){const d=b.map((v,i)=>v-a[i]),length=Math.hypot(...d);if(length<.01)return;let u=Math.abs(d[2])<length*.9?[-d[1],d[0],0]:[1,0,0];let l=Math.hypot(...u);u=u.map(x=>x/l);const v=[d[1]*u[2]-d[2]*u[1],d[2]*u[0]-d[0]*u[2],d[0]*u[1]-d[1]*u[0]].map(x=>x/length);const r=Math.max(3,width*4);let pts=[];for(const p of [a,b])for(const [i,j] of [[-1,-1],[1,-1],[1,1],[-1,1]])pts.push(p.map((x,k)=>x+r*(i*u[k]+j*v[k])));for(const f of [[0,1,2,3],[4,7,6,5],[0,4,5,1],[1,5,6,2],[2,6,7,3],[3,7,4,0]])add(f.map(i=>pts[i]),color,'opening');}
const ctx={FACADE,W:44650,D:72650,ROOF:23000,face,line};vm.createContext(ctx);vm.runInContext(fs.readFileSync(root+'/tools/完整立面规则.js','utf8'),ctx);for(side of ['east','west','south','north'])ctx.facade(side);process.stdout.write(JSON.stringify([...groups.values()]));
