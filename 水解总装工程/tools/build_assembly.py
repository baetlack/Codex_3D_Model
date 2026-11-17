"""Build an auditable offline assembly without rewriting any source geometry.
Dependencies: numpy, scipy, ezdxf. Coordinates mm Z-up; local Z0 = EL100.
"""
from pathlib import Path
import json, re, math, hashlib
import numpy as np
from scipy.optimize import linear_sum_assignment
import ezdxf
from types import SimpleNamespace
from review_layout import review

OUT=Path(__file__).resolve().parents[1]; ROOT=OUT.parent
LAYOUT='水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf'
BRIDGE='水解桥架工程/models/整体/viewer_data.js'
FOUND='水解桥架工程/models/设备/设备基础_20261106/'
inputs=set()
def read(path):
    inputs.add(path); return (ROOT/path).read_text(encoding='utf-8-sig')
def js(path): return json.loads(read(path).split('=',1)[1].strip().rstrip(';'))
def doc(path): return json.loads(read(path))
def save(name,d):
    p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def mesh(path): return js(path)

def box(name,x,y,z,w,d,h,color='#b8bec2',kind='structure',check=True):
    v=[[x,y,z],[x+w,y,z],[x+w,y+d,z],[x,y+d,z],[x,y,z+h],[x+w,y,z+h],[x+w,y+d,z+h],[x,y+d,z+h]]
    f=[[0,2,1],[0,3,2],[4,5,6],[4,6,7],[0,1,5],[0,5,4],[1,2,6],[1,6,5],[2,3,7],[2,7,6],[3,0,4],[3,4,7]]
    return {'name':name,'vertices':v,'faces':f,'color':color,'kind':kind,'check':check}

def build():
    inputs.add(LAYOUT); drawing=ezdxf.readfile(ROOT/LAYOUT); m=drawing.modelspace()
    origins=sorted([e for e in m.query('INSERT') if e.dxf.name=='水解厂房'],key=lambda e:e.dxf.insert.x)
    assert len(origins)==4
    origin=[list(e.dxf.insert)[:2] for e in origins]
    tags=doc('水解设备模型库/catalog.json')['models']; models=js('水解设备模型库/示图建模_20260521/models.js')
    foundation=js(FOUND+'foundation_data.js')
    labels=[]
    for e in m.query('TEXT MTEXT'):
        s=e.dxf.text if e.dxftype()=='TEXT' else e.plain_text()
        s=re.sub(r'[\s^{}]','',s)
        labels.append((s,np.array(list(e.dxf.insert)[:2]),e.dxf.handle))
    mapping={'D41B02':('水解槽',0),'F41B01':('偏钛酸缓冲槽低',0),
             'L41B04':('减温减压器',2),'C41B02':('钛液预热槽',2),'C41B01':('热水预热槽',2),'C41B03':('碱液预热槽',2),
             'D41B01':('水解晶种制备槽',2),'P41B01':('水解料中转泵',0),
             'P41B02':('一洗压滤供料泵',0),'P41B08':('一洗压滤供料泵',0),
             'L41B01':('*U562',0),'F41B02':('钛液事故槽',0),'F41B05':('钛液事故槽',0),'F41B06':('钛液事故槽',0)}
    # Shared block names must be assigned together so no physical block is duplicated.
    groups={}
    for tag,(name,floor) in mapping.items():groups.setdefault((name,floor),[]).extend(t for t in tags if t['id'][:6]==tag)
    assignments={}
    for (name,floor),rows in groups.items():
        ox,oy=origin[floor]
        blocks=[e for e in m.query('INSERT') if e.dxf.name==name and ox-1000<e.dxf.insert.x<ox+46000 and oy-1000<e.dxf.insert.y<oy+73500]
        if not blocks:continue
        valid=[]
        for row in rows:
            found=[(pos,h) for s,pos,h in labels if s==row['id'] and ox-2000<pos[0]<ox+48000 and oy-5000<pos[1]<oy+77000]
            if not found:continue
            # Prefer the actual plan label nearest a matching equipment block.
            pos,h=min(found,key=lambda a:min(np.linalg.norm(a[0]-np.array(list(b.dxf.insert)[:2])) for b in blocks))
            valid.append((row,pos,h))
        if not valid:continue
        cost=np.array([[np.linalg.norm(p-np.array(list(b.dxf.insert)[:2])) for b in blocks] for _,p,_ in valid])
        ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):
            if cost[i,j]>6000:continue
            row,pos,label=valid[i];b=blocks[j]
            assignments[row['id']]={'block':b,'floor':floor,'label':label,'distance':round(float(cost[i,j]),2)}
    # Cooler labels identify pairs. Use real single-machine block centers, ordered west/east.
    cool=[e for e in m.query('INSERT') if e.dxf.name=='石墨换热器-底' and origin[0][0]<e.dxf.insert.x<origin[0][0]+44000]
    for pair,y in [('AB',375559),('CD',371559),('EF',368559)]:
        bs=sorted([e for e in cool if abs(e.dxf.insert.y-y)<2],key=lambda e:e.dxf.insert.x)
        if len(bs)==2:
            for suffix,b in zip(pair,bs):assignments['C41B04'+suffix]={'block':b,'floor':0,'label':'3853B/3853E/38541','distance':None}
    # Unblocked circular equipment: retained DXF handles identify their centers.
    for tag,handle,floor in [('F41B04','33EAC',3),('F41B03','D9737',2),('F41B08','113DE7',0)]:
        e=drawing.entitydb[handle]
        b=SimpleNamespace(dxf=SimpleNamespace(insert=e.dxf.center,rotation=0,handle=handle,name='CIRCLE-设备轮廓'))
        assignments[tag]={'block':b,'floor':floor,'label':'平面位号与圆轮廓核对','distance':None}
    placements=[];assets={};pending=[]
    for row in tags:
        tag=row['id'];key=tag[:6];a=assignments.get(tag)
        source_key={'F41B05':'F41B02','F41B06':'F41B02'}.get(key,key)
        if not a:
            pending.append({'id':tag,'name':row['name'],'reason':'未取得可唯一关联的平面设备图块，禁止以文字插入点代替设备中心','legacy_position_mm':row['cad_position_mm']});continue
        if source_key in foundation['equipment']:path=FOUND+foundation['equipment'][source_key]['path']+'model_data.js'
        elif source_key in models:path='水解设备模型库/示图建模_20260521/模型/'+source_key+'/model_data.js'
        else:
            pending.append({'id':tag,'name':row['name'],'reason':'暂无可关联的正式类型净模'});continue
        if not (ROOT/path).exists():raise FileNotFoundError(path)
        parts=mesh(path);assets[key]={'path':'../'+path,'source':path,'units':'mm'}
        floor=a['floor'];b=a['block'];xyz=list(b.dxf.insert);xyz[0]-=origin[floor][0];xyz[1]-=origin[floor][1]
        level='EL100';basis='台账/既有布置 POS EL；安装基准待核';verified=False
        if key=='D41B02':z=1500;basis='基础肋顶 +1.500 m，设备净模槽底 Z0';verified=True
        elif key=='F41B01':z=300;basis='基础顶 +0.300 m，设备净模槽底 Z0';verified=True
        elif key in ('C41B01','C41B02','C41B03'):
            z={'C41B01':12200,'C41B02':12150,'C41B03':12200}[key];level='EL112';basis='EL112 平面 POS EL 与基础顶 +0.200/+0.150 m';verified=True
        elif key=='C41B04':
            z=0;basis='类型模型托耳底 Z4500 与钢框架梁顶 +4.500 m 对齐；POS EL104.5 为承托面而非模型底';verified=True
        elif key=='F41B04':
            z=23000;level='EL123';basis='屋面平面圆轮廓与烟囱基础图：楼面23.000m；基础安装高差待核'
        elif key=='L41B04':
            z=12000;level='EL112';basis='EL112平面图块，精确安装高差待核'
        elif key=='F41B03':
            z=12200;level='EL112';basis='EL112平面POSEL112.200，局部设备原点待核'
        elif key=='D41B01':
            z=9820;level='EL106';basis='支架底 EL108.5，承托面 EL111.0；组合数据 mount Z1180，设备原点=111000-100000-1180';verified=True
        else:z=((row['pos_el'] if row['pos_el'] is not None else 100)-100)*1000
        xyz[2]=z
        # Rotations are applied rigidly; no geometry scaling/deformation.
        yaw=float(b.dxf.rotation)
        record={'id':tag,'name':row['name'],'asset':key,'position_mm':[round(v,4) for v in xyz],'rotation_deg':yaw,'level':level,
            'xy_status':'图块中心定位','z_status':'有安装基准' if verified else '待核','orientation_status':'圆轮廓仅确认中心，管口朝向待核' if b.dxf.name.startswith('CIRCLE') else '图块旋转已记录；类型模型管口朝向待逐项核对',
            'source_insert':b.dxf.handle,'source_block':b.dxf.name,'label_handle':a['label'],'label_distance_mm':a['distance'],
            'source_floor_origin_mm':origin[floor],'z_basis':basis,'source':LAYOUT}
        placements.append(record)
    layout_review=review(drawing,origin,placements,assets,ROOT,read)
    save('data/布置复核.json',layout_review)
    # Building geometry is authored and maintained solely in 厂房外观模型.
    building_path='厂房外观模型/建筑/model_data.js'
    if not (ROOT/building_path).exists():raise SystemExit('先运行 厂房外观模型/建筑/tools/build_building.py')
    buildings=js(building_path)['parts']
    read('厂房外观模型/建筑/building.json')
    civil=[]
    for p in placements:
        key=p['asset']
        if key not in ('D41B02','F41B01','C41B01','C41B02','C41B03') or key not in foundation['assets']:continue
        source=FOUND+key+'/model_data.js';assets['foundation-'+key]={'path':'../'+source,'source':source,'units':'mm'};mesh(source)
        civil.append({'id':'BASE-'+p['id'],'name':foundation['assets'][key]['name'],'asset':'foundation-'+key,'position_mm':p['position_mm'],'rotation_deg':p['rotation_deg'],'mirror_y':p.get('mirror_y',False),'level':p['level'],'support_for':p['id']})
    # Cross-check 23 main vessel centers against the independent architectural plan.
    refs=doc('厂房外观模型/建筑/一层设备基础.json')['items']; checks=[]
    for p in placements:
        if p['asset'] not in ('D41B02','F41B01'):continue
        radius=3050 if p['asset']=='D41B02' else 2600
        circles=[r for r in refs if r['kind']=='circle' and abs(r['r']-radius)<1]
        q=min(circles,key=lambda r:math.hypot(r['cx']-325-p['position_mm'][0],r['cy']-325-p['position_mm'][1]))
        error=math.hypot(q['cx']-325-p['position_mm'][0],q['cy']-325-p['position_mm'][1])
        correction=None
        if error>3:
            assert p['id']=='D41B02B1' and error<201
            correction={'source_position_mm':p['position_mm'][:],'reason':'布置图块偏离建筑基础约200mm，按建筑基础中心就位，源图不改'}
            p['position_mm'][:2]=[q['cx']-325,q['cy']-325];p['position_correction']=correction
        checks.append({'id':p['id'],'source_error_mm':round(error,3),'error_mm':0 if correction else round(error,3),'correction':correction})
    assert len(checks)==23 and max(c['error_mm'] for c in checks)<3,checks
    # Verify bridge grid labels share the same axes, without modifying bridge placements.
    bridge_dxf='水解桥架工程/data/原始资料/0241B_二期水解仪表桥架布局_1031_t3.dxf';inputs.add(bridge_dxf)
    bd=ezdxf.readfile(ROOT/bridge_dxf);grid=bd.blocks['水解一楼'];xs=sorted(round(e.dxf.center.x) for e in grid.query('CIRCLE') if e.dxf.center.y<0 and e.dxf.center.x>=0)
    assert xs==[0,6000,13000,19000,26000,32000,38000,44000],xs
    read(BRIDGE);read('水解桥架工程/models/整体/assembly.json')
    assembly={'version':'0.3','local_z0_EL':100,'units':'mm','axes':{'east':'+X','north':'+Y','up':'+Z'},
        'modules':{'building':{'translation_mm':[0,0,0],'rotation_deg':0,'scale':1,'source':'../厂房外观模型/建筑/model_data.js','basis':'完整建筑源网格已归一到柱轴坐标，直接引用，不重复平移'},'bridge':{'translation_mm':[0,0,0],'rotation_deg':0,'scale':1,'basis':'原水解一楼建筑块轴网，与结构柱轴一致'}},
        'assets':assets,'equipment':placements,'foundations':civil,'unplaced':pending,
        'limits':['上部柱截面沿用源模型，+9.900m以上需结构图复核','墙厚200mm及屋面厚200mm仅显示假设，不参与确认碰撞','建筑统一引用厂房外观模型完整网格；160mm板厚为显示口径，吊装孔按建施图真切孔','图块朝向尚未逐项与类型模型管口方向核对','未定位设备不进入空间场景或碰撞检查；待核安装标高单列']}
    audit={'axis_grid_x_mm':xs,'main_vessel_foundation_checks':checks,'max_error_mm':max(c['error_mm'] for c in checks),'placed':len(placements),'unplaced':len(pending),'z_referenced':sum(p['z_status']=='有安装基准' for p in placements),'limitations':assembly['limits'],'layout_reviewed':layout_review['reviewed'],'layout_pending':layout_review['pending']}
    save('assembly.json',assembly);save('data/设备就位表.json',placements);save('data/待核设备.json',pending);save('data/对齐依据.json',audit)
    (OUT/'data/building.js').write_text('// Compatibility alias only; authoritative mesh lives in 厂房外观模型.\nwindow.ASSEMBLY_BUILDING=window.BUILDING_MODEL.parts;\n',encoding='utf-8')
    (OUT/'data/assembly.js').write_text('window.SITE_ASSEMBLY='+json.dumps(assembly,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    save('data/来源与哈希.json',{'version':'0.3','sources':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(inputs)}})
    print(json.dumps(audit,ensure_ascii=False))
if __name__=='__main__':build()
