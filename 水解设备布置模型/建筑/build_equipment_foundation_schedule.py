from pathlib import Path
from collections import Counter
import json, hashlib

ROOT=Path(__file__).resolve().parent
SRC=ROOT/'原始资料'/'20251027 B系列结晶冷却厂房建施图_t3.dxf'
FLOORS={
 1:('CH202511DE-5J-41B-04',4388240.0,171772.0,4432890.0,244422.0),
 2:('CH202511DE-5J-41B-05',4528663.5,167930.4,4573313.5,240580.4),
 3:('CH202511DE-5J-41B-06',4684213.0,163771.5,4728863.0,236421.5),
}
lines=SRC.read_bytes().decode('cp936',errors='replace').splitlines()
pairs=list(zip(lines[::2],lines[1::2]));entities=[];cur=None;inside=False
for code,value in pairs:
    code=code.strip();value=value.strip()
    if code=='2' and value=='ENTITIES':inside=True;continue
    if inside and code=='0' and value=='ENDSEC':break
    if not inside:continue
    if code=='0':
        if cur:entities.append(cur)
        cur={'type':value,'data':[]}
    elif cur:cur['data'].append((code,value))
if cur:entities.append(cur)

def poly_points(d):
    pts=[];x=None
    for c,v in d:
        if c=='10':x=float(v)
        elif c=='20' and x is not None:pts.append((x,float(v)));x=None
    return pts

def plan_texts(bounds):
    x0,y0,x1,y1=bounds;out=[]
    for e in entities:
        if e['type'] not in ('TEXT','MTEXT','ATTRIB'):continue
        d=e['data'];x=next((float(v) for c,v in d if c=='10'),-1);y=next((float(v) for c,v in d if c=='20'),-1)
        if x0<=x<=x1 and y0<=y<=y1:
            s=''.join(v for c,v in d if c in ('1','3')).replace('%%P','±')
            if s.strip():out.append({'x':x-x0,'y':y-y0,'text':s,'layer':next((v for c,v in d if c=='8'),'')})
    return out

rows=[];top_rows=[];top_by_floor={}; id_counters=Counter()
for floor,(drawing_id,x0,y0,x1,y1) in FLOORS.items():
    bound=(x0,y0,x1,y1);labels=plan_texts(bound)
    feats=[]
    for e in entities:
        d=e['data'];layer=next((v for c,v in d if c=='8'),'')
        if layer!='基础线':continue
        if e['type']=='CIRCLE':
            x=float(next(v for c,v in d if c=='10'));y=float(next(v for c,v in d if c=='20'));r=float(next(v for c,v in d if c=='40'))
            if x0<=x<=x1 and y0<=y<=y1:feats.append({'kind':'circle','x':x-x0,'y':y-y0,'r':r,'srcx':x,'srcy':y})
        elif e['type']=='LWPOLYLINE' and int(next((v for c,v in d if c=='70'),'0'))&1:
            pts=poly_points(d)
            if len(pts)<4 or not all(x0-100<=x<=x1+100 and y0-100<=y<=y1+100 for x,y in pts):continue
            width=max(x for x,y in pts)-min(x for x,y in pts);depth=max(y for x,y in pts)-min(y for x,y in pts)
            if width<500 or depth<500:continue
            feats.append({'kind':'polygon','pts':[(x-x0,y-y0) for x,y in pts],'srcpts':pts,'width':width,'depth':depth})
    # Exact duplicate circles occur in the CAD entities; retain each physical footprint once.
    clean=[];seen=set()
    for f in feats:
        if f['kind']=='circle':
            key=(round(f['srcx'],2),round(f['srcy'],2),round(f['r'],2))
            if key in seen:continue
            seen.add(key)
        clean.append(f)
    feats=clean
    circles=[f for f in feats if f['kind']=='circle']
    # Name foundations only where the plan has a nearby explicit foundation label.
    for f in circles:
        nearest=min((t for t in labels if '基础' in t['text']),key=lambda t:((t['x']-f['x'])**2+(t['y']-f['y'])**2),default=None)
        name=nearest['text'] if nearest and (nearest['x']-f['x'])**2+(nearest['y']-f['y'])**2<2500**2 else ''
        f['label']=name
    # Stable order: north-to-south, then west-to-east.
    circles.sort(key=lambda f:(-round(f['y']),round(f['x'])))
    polys=[f for f in feats if f['kind']=='polygon']
    polys.sort(key=lambda f:(-round(sum(y for x,y in (p for p in f['pts']))/len(f['pts'])),round(min(x for x,y in f['pts']))))
    for f in circles+polys:
        if floor==2: continue  # floor 2 is the top-contour reference sheet, not a foundation schedule
        if f['kind']=='circle':cx,cy=f['x'],f['y'];r=f['r'];name=f['label']
        else:
            cx=sum(x for x,y in f['pts'])/len(f['pts']);cy=sum(y for x,y in f['pts'])/len(f['pts']);r=None;name=''
        if floor==1 and r and name=='水解槽基础':category='水解槽';
        elif floor==1 and r and name=='偏钛酸缓冲槽基础':category='钛液缓冲槽';
        elif floor==3 and r and name:category=name.replace('基础','')
        elif r:category='圆形设备基础（名称待确认）'
        else:category='多边形基础轮廓（归属待确认）'
        key=(floor,f['kind']); id_counters[key]+=1
        fid=f'{floor}F-{"C" if f["kind"]=="circle" else "P"}{id_counters[key]:02d}'
        axis=f'X+{cx/1000:.3f}m / Y+{cy/1000:.3f}m'
        if floor==1 and category=='钛液缓冲槽':axis+= '；东侧'
        row={'基础编号':fid,'楼层':f'{floor}层','图号':drawing_id,'设备/基础名称':category,
             '设备位号':'','基础几何类型':'圆形' if f['kind']=='circle' else '多边形',
             '局部X（东+，mm）':round(cx,1),'局部Y（北+，mm）':round(cy,1),
             'CAD_X（mm）':round(x0+cx,1),'CAD_Y（mm）':round(y0+cy,1),
             '图示轮廓直径（mm）':round(2*r,1) if r else '',
             '图示轮廓X向范围（mm）':round(f['width'],1) if r is None else '',
             '图示轮廓Y向范围（mm）':round(f['depth'],1) if r is None else '',
             '基础形式（待填）':'','基础规格（待填）':'','基础长/直径（待填，mm）':'',
             '基础宽（待填，mm）':'','基础厚/高（待填，mm）':'','基础顶标高（待填）':'',
             '轴网位置参考':axis,'图纸标注':' '.join(name.split()) if name else '该轮廓附近无明确基础名称文字；请核对设备归属'}
        rows.append(row)
    top_by_floor[floor]=circles

# 2F circles are tops of 1F tanks, not separate foundation items.
bottom=top_by_floor[1];tops=top_by_floor[2]
for i,f in enumerate(tops,1):
    nearest=min(bottom,key=lambda b:(b['x']-f['x'])**2+(b['y']-f['y'])**2)
    dist=((nearest['x']-f['x'])**2+(nearest['y']-f['y'])**2)**.5
    top_rows.append({'顶部轮廓编号':f'2F-T{i:02d}','图号':FLOORS[2][0],
                     '顶部名称':'一层槽罐顶部轮廓','局部X（东+，mm）':round(f['x'],1),'局部Y（北+，mm）':round(f['y'],1),
                     'CAD_X（mm）':round(FLOORS[2][1]+f['x'],1),'CAD_Y（mm）':round(FLOORS[2][2]+f['y'],1),
                     '顶部轮廓直径（mm）':round(2*f['r'],1),
                     '匹配的一层基础编号':next((r['基础编号'] for r in rows if r['楼层']=='1层' and abs(r['局部X（东+，mm）']-nearest['x'])<.1 and abs(r['局部Y（北+，mm）']-nearest['y'])<.1),'') if dist<100 else '',
                     '中心距（mm）':round(dist,1),'基础备注':'二层此轮廓为一层槽罐顶部，不单列二层底座。'})

doc={'source':SRC.name,'source_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest(),'axis_note':'局部坐标以每层平面图西南角外包原点起算；东+X、北+Y。','rows':rows,'top_rows':top_rows,
     'summary':{f'{k[0]} {k[1]}':v for k,v in Counter((r['楼层'],r['基础几何类型']) for r in rows).items()}}
(ROOT/'设备基础规格填写表.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('foundations',len(rows),'2F top references',len(top_rows),'matching top centers',sum(bool(r['匹配的一层基础编号']) for r in top_rows))


