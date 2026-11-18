"""Additional labelled floor apertures; no inferred equipment-foundation holes.
Source coordinates are transformed exactly once to axis-local millimetres.
"""
import math


def clean(points):
    out=[]
    for p in points:
        q=[round(float(v),3) for v in p]
        if not out or math.dist(q,out[-1])>.001:out.append(q)
    if len(out)>1 and math.dist(out[0],out[-1])<.001:out.pop()
    return out


def extract_openings(entities,origins):
    by_id={e['handle']:e for e in entities};out=[]
    def local(handle,floor):
        ox,oy=origins[floor]
        return clean([[x-ox-325,y-oy-325] for x,y in by_id[handle]['points']])
    def add(name,floor,poly,sources,labels,paths=None,closed=True,**extra):
        record={'id':'FLOOROPEN-'+str(floor)+'-'+name,'type':'floor_opening','floor':floor,'EL':100+(floor-1)*6,
                'polygon':clean(poly),'source_handles':sources,'label_handles':labels,
                'guard_paths':[] if extra.get('guard_height_mm',1100)==0 else paths or [clean(poly)],'guard_closed':closed,
                'curb_width_mm':200,'curb_height_mm':100,'guard_height_mm':1100,
                'basis':'建施图楼面开孔/留孔内轮廓；结构48211/4C28D要求所有楼面开孔翻边',**extra}
        out.append(record)
    # The HOLE-layer three-point strokes are break symbols, not aperture polygons.
    # Their opposite endpoints identify a rectangle verified against four real edges.
    for name,diag,edges,label in [
        ('NORTH-1','26CE',['2093','2095','209E','209F'],'A38CA'),
        ('NORTH-2','26CD',['2098','2096','209A','209B'],'A38C9'),
        ('NORTH-3','26CF',['2099','2097','209C','209D'],'A38C8')]:
        a,b=local(diag,2)[0],local(diag,2)[-1];x0,x1=sorted([a[0],b[0]]);y0,y1=sorted([a[1],b[1]])
        for handle in edges:
            for x,y in local(handle,2):
                assert min(abs(x-x0),abs(x-x1),abs(y-y0),abs(y-y1))<.1,handle
        poly=[[x0,y0],[x1,y0],[x1,y1],[x0,y1]]
        add(name,2,poly,edges,[label],symbol_handles=[diag],shape='rectangle',clear_size_mm=[round(x1-x0,3),round(y1-y0,3)])
    # Closed inner notched loops from the actual boundary LINE entities.
    for name,lo,hi,label in [('NORTH-1',0x1677,0x1682,'A3C64'),('NORTH-2',0x1685,0x1690,'A3C63')]:
        handles=[format(i,'X') for i in range(lo,hi+1)];poly=[];end=None
        for handle in handles:
            points=local(handle,3)
            if end is not None:
                if math.dist(end,points[0])>.1:points.reverse()
                assert math.dist(end,points[0])<.1,handle
            poly.append(points[0]);end=points[-1]
        assert math.dist(end,poly[0])<.1
        add(name,3,poly,handles,[label],shape='notched')
    for name,handle,label in [('WEST-NORTH','599','A3C65'),('WEST-SOUTH','5AF','A3C78')]:
        poly=local(handle,3)
        # The source outline leaves a steel-stair entrance gap on one straight edge.
        # Close only the slab aperture, and preserve that gap in curb/guard paths.
        add(name,3,poly,[handle],[label],paths=[poly],closed=False,shape='notched',access_gap_preserved=True)
    poly=local('59B',3)
    add('WEST-SMALL',3,poly,['59B'],['A3C66'],shape='rectangle',clear_size_mm=[1000,2000])
    poly=local('665',3)
    add('EAST-SOUTH',3,poly,['665','668'],['A3CB6'],paths=[poly,local('668',3)],closed=False,shape='notched',access_gap_preserved=True)
    # Five Ø500 utility penetrations; the concentric Ø700 line is the curb outer edge.
    # R800/R1800/R2850 circles labelled as equipment foundations are deliberately excluded.
    for handle,outer,label in [('5F6','2080','A3D6C'),('1F9B','2016','A3D71'),('600','2015','A3D77'),('5FC','2014','A3D7D'),('1F9F','2013','A3D82')]:
        e=by_id[handle];outer_e=by_id[outer];r=e['radius'];assert abs(r-250)<.01 and abs(outer_e['radius']-350)<.01
        points=e['points'];cx=(min(p[0] for p in points)+max(p[0] for p in points))/2;cy=(min(p[1] for p in points)+max(p[1] for p in points))/2
        outer_points=outer_e['points'];outer_center=[(min(p[k] for p in outer_points)+max(p[k] for p in outer_points))/2 for k in [0,1]]
        assert math.dist([cx,cy],outer_center)<.1,(handle,outer)
        ox,oy=origins[3];center=[round(cx-ox-325,3),round(cy-oy-325,3)]
        poly=[[center[0]+r*math.cos(i*math.tau/96),center[1]+r*math.sin(i*math.tau/96)] for i in range(96)]
        add('PIPE-'+handle,3,poly,[handle,outer],[label],shape='circle',center_mm=center,radius_mm=r,curb_width_mm=100,guard_height_mm=0,
            basis='建施图φ500楼面开孔及φ700同心翻边外轮廓；小预留孔不增设围栏')
    return out


def union_intervals(intervals,x_at,ym):
    result=[]
    for a,b in sorted(intervals,key=lambda v:x_at(v[0],ym)):
        if result and x_at(a,ym)<=x_at(result[-1][1],ym)+1e-7:
            if x_at(b,ym)>x_at(result[-1][1],ym):result[-1]=(result[-1][0],b)
        else:result.append((a,b))
    return result


def edge_paths(hole):
    for path in hole['guard_paths']:
        yield path,list(zip(path,path[1:]+(path[:1] if hole['guard_closed'] else [])))


def curb_mesh(hole,make_part,rectangle,interval_at,x_at):
    """Union of border bands minus the true hole; scanline cells need no new dependency."""
    poly=hole['polygon'];width=hole['curb_width_mm'];regions=[]
    if hole['shape']=='circle':
        x,y=hole['center_mm'];r=hole['radius_mm']+width
        regions=[[[x+r*math.cos(i*math.tau/96),y+r*math.sin(i*math.tau/96)] for i in range(96)]]
    else:
        for path,edges in edge_paths(hole):
            for a,b in edges:
                x0,x1=sorted([a[0],b[0]]);y0,y1=sorted([a[1],b[1]])
                if abs(a[0]-b[0])<.1:regions.append(rectangle(x0-width,y0,x1+width,y1))
                elif abs(a[1]-b[1])<.1:regions.append(rectangle(x0,y0-width,x1,y1+width))
                else:raise ValueError('Expected orthogonal aperture edge: '+hole['id'])
            joins=path if hole['guard_closed'] else path[1:-1]
            for x,y in joins:regions.append(rectangle(x-width,y-width,x+width,y+width))
    ys=sorted(set(round(y,5) for shape in regions+[poly] for x,y in shape if -325<=y<=72325))
    ys=sorted(set(ys+[-325.,72325.]));z=(hole['EL']-100)*1000;p=make_part(hole['id']+'-CURB','guard','#b5c0c5')
    def emit(left,right,ya,yb):
        points=[[max(-325,min(44325,x_at(left,y))),y] for y in [ya,yb]]
        other=[[max(-325,min(44325,x_at(right,y))),y] for y in [ya,yb]]
        q=[points[0],other[0],other[1],points[1]]
        if sum(q[(i+1)%4][0]*q[i][1]-q[i][0]*q[(i+1)%4][1] for i in range(4))> -1e-6:return
        start=len(p['vertices']);p['vertices'] += [[x,y,h] for h in [z,z+hole['curb_height_mm']] for x,y in q]
        for f in [[0,3,2,1],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]]:
            p['faces'] += [[start+f[0],start+f[i],start+f[i+1]] for i in [1,2]]
    for ya,yb in zip(ys,ys[1:]):
        ym=(ya+yb)/2;allowed=union_intervals([v for r in regions for v in interval_at(r,ym)],x_at,ym);blocked=interval_at(poly,ym)
        for left,right in allowed:
            current=left
            for a,b in blocked:
                if x_at(b,ym)<=x_at(current,ym) or x_at(a,ym)>=x_at(right,ym):continue
                if x_at(a,ym)>x_at(current,ym):emit(current,a,ya,yb)
                if x_at(b,ym)>x_at(current,ym):current=b
                if x_at(current,ym)>=x_at(right,ym):break
            if x_at(current,ym)<x_at(right,ym):emit(current,right,ya,yb)
    p['opening_id']=hole['id'];return p


def guard_mesh(hole,make_part,rod):
    p=make_part(hole['id']+'-GUARD','guard','#a7bdc0');poly=hole['polygon'];area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]));sign=1 if area>0 else -1;z=(hole['EL']-100)*1000
    def normal(a,b):
        dx,dy=b[0]-a[0],b[1]-a[1];size=math.hypot(dx,dy)
        return [sign*dy/size,-sign*dx/size] if size>.001 else [0,0]
    for path,edges in edge_paths(hole):
        shifted=[]
        for i,q in enumerate(path):
            before=normal(path[i-1],q) if i or hole['guard_closed'] else None
            after=normal(q,path[(i+1)%len(path)]) if i<len(path)-1 or hole['guard_closed'] else None
            n=before or after
            if before and after:
                n=[before[k]+after[k] for k in [0,1]];den=sum(n[k]*after[k] for k in [0,1]);n=[v/den for v in n] if abs(den)>.01 else after
            shifted.append([q[k]+100*n[k] for k in [0,1]])
        for a,b in zip(shifted,shifted[1:]+(shifted[:1] if hole['guard_closed'] else [])):
            if math.dist(a,b)<.01:continue
            for h in [650,1100]:rod(p,[*a,z+h],[*b,z+h],32)
            count=math.ceil(math.dist(a,b)/110)
            for i in range(count+1):
                q=[a[k]+(b[k]-a[k])*i/count for k in [0,1]];rod(p,[*q,z+100],[*q,z+1100],16)
    p['opening_id']=hole['id'];return p
