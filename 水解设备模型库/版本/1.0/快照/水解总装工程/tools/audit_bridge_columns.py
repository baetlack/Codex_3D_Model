"""Read-only expanded bridge/column audit: exact surface clipping, depth and axis separation.
Does not move models or overwrite the original 88-primary-column collision report.
"""
from pathlib import Path
import sys,json,collections,math,csv,hashlib,argparse
import numpy as np
import check_assembly as ck
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parent

def area(poly):return sum(np.linalg.norm(np.cross(poly[i]-poly[0],poly[i+1]-poly[0])) for i in range(1,len(poly)-1))/2 if len(poly)>=3 else 0

def clip(poly,low,high,axes=range(3)):
 for axis in axes:
  poly=ck.clip_polygon(poly,axis,low[axis],True)
  if not poly:return []
  poly=ck.clip_polygon(poly,axis,high[axis],False)
  if not poly:return []
 return poly

def polygons(bridge,column):
 low,high=column['low'],column['high'];mask=np.all(bridge['th']>=low,axis=1)&np.all(bridge['tl']<=high,axis=1)
 result=[]
 for i in np.flatnonzero(mask):
  poly=clip(list(bridge['t'][i]),low,high)
  if area(poly)>1e-6:result.append(poly)
 return result

def max_depth(polys,low,high):
 lo=0.;hi=min(high[:2]-low[:2])/2;best=None
 for i in range(30):
  d=(lo+hi)/2;lower=low.copy();upper=high.copy();lower[:2]+=d;upper[:2]-=d;found=None
  for poly in polys:
   candidate=clip(poly,lower,upper,[0,1])
   if candidate:found=np.mean(candidate,axis=0);break
  if found is not None:lo=d;best=found
  else:hi=d
 return lo,best

def translations(bridge,column):
 result={}
 for axis,label in [(0,'X'),(1,'Y')]:
  axes=[k for k in range(3) if k!=axis];low=column['low'].copy()+1e-7;high=column['high'].copy()-1e-7;intervals=[]
  mask=np.all(bridge['th'][:,axes]>low[axes],axis=1)&np.all(bridge['tl'][:,axes]<high[axes],axis=1)
  for i in np.flatnonzero(mask):
   poly=clip(list(bridge['t'][i]),low,high,axes)
   if area(poly)<1e-6:continue
   xs=[p[axis] for p in poly];intervals.append((column['low'][axis]-max(xs),column['high'][axis]-min(xs)))
  merged=[]
  for a,b in sorted(intervals):
   if merged and a<merged[-1][1]-1e-8:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
   else:merged.append((a,b))
  containing=next((p for p in merged if p[0]<0<p[1]),None)
  assert containing is not None,(bridge['id'],column['id'],label)
  result[label+'-']=-containing[0];result[label+'+']=containing[1]
 return result

def load():
 root=ROOT;columns=[]
 for p in ck.script(root/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts']:
  if p['kind'] in ['structure','room_column']:
   col=ck.object_mesh(p['name'],p['kind'],ck.tri([p]));col['source_part']=p['name'];columns.append(col)
  elif p['name'].endswith('-TZ'):
   assert len(p['vertices'])%8==0
   for i in range(len(p['vertices'])//8):
    off=i*8;faces=[[v-off for v in f] for f in p['faces'] if all(off<=v<off+8 for v in f)];assert len(faces)==12
    col=ck.object_mesh(p['name']+'-'+str(i+1),'stair_column',ck.tri([{'vertices':p['vertices'][off:off+8],'faces':faces}]));col['source_part']=p['name'];columns.append(col)
 bridges=[ck.object_mesh(g['id'],'bridge',ck.tri([{'vertices':g['v'],'faces':g['f']}],scale=1000)) for g in ck.script(root/'水解桥架工程/models/整体/viewer_data.js','GEOMETRY')]
 return bridges,columns

BINS=[(0,10,'0.1–10 mm'),(10,30,'>10–30 mm'),(30,60,'>30–60 mm'),(60,100,'>60–100 mm'),(100,float('inf'),'>100 mm')]
def bucket(value):return next(label for low,high,label in BINS if low<value<=high)

def verify_lp(polys,column):
 from scipy.optimize import linprog
 best=0.
 for poly in polys:
  v=np.asarray(poly);n=len(v);a=[];b=[]
  # Convex weights select a point on the actual clipped surface polygon.
  # Maximise t subject to distance to all four horizontal column faces >=t.
  for k in [0,1]:
   a.extend([np.r_[-v[:,k],1.],np.r_[v[:,k],1.]])
   b.extend([-column['low'][k],column['high'][k]])
  obj=np.r_[np.zeros(n),-1.]
  result=linprog(obj,A_ub=np.array(a),b_ub=np.array(b),A_eq=[np.r_[np.ones(n),0]],b_eq=[1.],bounds=[(0,None)]*n+[(0,None)],method='highs')
  if result.success:best=max(best,float(result.x[-1]))
 return best

def audit(lp=False):
 bridges,columns=load();rows=[];contacts=[];box_only=[];verified=0
 # The source assembly JSON carries fitting/straight names, not just render geometry.
 part_data={p['id']:p for p in json.loads((ROOT/'水解桥架工程/models/整体/assembly.json').read_text())['parts']}
 sources=['水解总装工程/tools/audit_bridge_columns.py','水解总装工程/tools/check_assembly.py','厂房外观模型/建筑/model_data.js','厂房外观模型/建筑/结构立柱数据.json','水解桥架工程/models/整体/viewer_data.js','水解桥架工程/models/整体/assembly.json']
 inputs={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in sources}
 for name,digest in json.loads((OUT/'data/来源与哈希.json').read_text())['sources'].items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
 for bridge in bridges:
  for column in columns:
   overlap=np.minimum(bridge['high'],column['high'])-np.maximum(bridge['low'],column['low'])
   if np.any(overlap<0):continue
   source=part_data[bridge['id']];sections=sorted({(v['width_mm'],v['height_mm']) for v in source.get('ports',[])})
   if not sections and 'width_mm' in source:sections=[(source['width_mm'],source['height_mm'])]
   assert np.allclose(bridge['low'],source['bbox_mm'][0],atol=.02) and np.allclose(bridge['high'],source['bbox_mm'][1],atol=.02),bridge['id']
   common={'bridge':bridge['id'],'cad_handle':source.get('handle'),'bridge_sections_mm':sections,'column':column['id'],'column_scope':column['kind'],'source_column_part':column['source_part'],'level':bridge['id'].split('-')[0],
     'bridge_type':part_data[bridge['id']]['label'],'column_section_mm':(column['high']-column['low'])[:2].tolist(),'column_axis_xy_mm':((column['low']+column['high'])/2)[:2].tolist(),
     'column_bounds_mm':[column['low'].tolist(),column['high'].tolist()],'aabb_overlap_mm':overlap.round(6).tolist()}
   proof=ck.column_penetration(bridge,column,.1)
   if not proof:
    if ck.surface(bridge,column) is not None:contacts.append({**common,'status':'表面接触（正常）'})
    else:box_only.append({**common,'status':'仅包围盒候选，未发现实际穿入或接触'})
    continue
   polys=polygons(bridge,column);points=np.vstack(polys);d,witness=max_depth(polys,column['low'],column['high']);moves=translations(bridge,column);direction=min(moves,key=moves.get);value=moves[direction]
   vector=np.zeros(3);vector[0 if direction[0]=='X' else 1]=value*(1 if direction[1]=='+' else -1)
   moved=ck.object_mesh('validation-only','bridge',bridge['t']+vector)
   assert ck.column_penetration(moved,column,.1) is None,(bridge['id'],column['id'],moves)
   if lp:
    independent=verify_lp(polys,column);assert abs(independent-d)<.0001,(bridge['id'],column['id'],d,independent);verified+=1
   row={**common,'status':'实际穿入','depth_band':bucket(d),'max_depth_mm':round(d,6),'depth_witness_mm':witness.round(6).tolist(),'old_sample_depth_mm':proof['interior_sample_depth_mm'],
        'separation_mm':round(value,6),'direction':direction,'moves_mm':{k:round(v,6) for k,v in moves.items()},'separation_rechecked':True,
        'actual_intersection_extent_mm':(points.max(0)-points.min(0)).round(6).tolist(),'intersection_low_mm':points.min(0).round(6).tolist(),'intersection_high_mm':points.max(0).round(6).tolist()}
   if source['kind']=='horizontal_straight':
    axis=np.diff(np.asarray(source['assembled_centerline_mm'])[:,:2],axis=0)[0];normal=np.array([-axis[1],axis[0]])/np.linalg.norm(axis);projection=points[:,:2]@normal
    row['bridge_width_mm']=source['width_mm'];row['overlapped_width_mm']=round(float(projection.max()-projection.min()),6);row['overlapped_width_percent']=round(row['overlapped_width_mm']/source['width_mm']*100,4)
   rows.append(row)
 old=json.loads((OUT/'data/桥架立柱核对.json').read_text())
 assert {(r['bridge'],r['column']) for r in rows if r['column_scope']=='structure'}=={(r['a'],r['b']) for r in old['penetrations']}
 assert {(r['bridge'],r['column']) for r in contacts if r['column_scope']=='structure'}=={(r['a'],r['b']) for r in old['normal_contacts']}
 bands=[{'range':label,'total':sum(r['depth_band']==label for r in rows),**{level:sum(r['depth_band']==label and r['level']==level for r in rows) for level in ['L1','L2','L3']}} for low,high,label in BINS]
 groups=[]
 for id in sorted({r['bridge'] for r in rows}):
  rr=[r for r in rows if r['bridge']==id];groups.append({'bridge':id,'bridge_type':rr[0]['bridge_type'],'pairs':len(rr),'columns':[r['column'] for r in rr],'depths_mm':sorted({r['max_depth_mm'] for r in rr}),'best_directions':sorted({r['direction'] for r in rr})})
 return {'schema_version':1,'assembly_version':json.loads((ROOT/'水解桥架工程/models/整体/assembly.json').read_text())['version'],'units':'mm','source_sha256':inputs,'tolerance_mm':.1,
    'scope':{'bridge_components':len(bridges),'columns':dict(collections.Counter(c['kind'] for c in columns))},
    'definitions':{'max_depth_mm':'实际桥架面进入柱体后，距最近X/Y柱侧面的最大距离；不是包围盒跨度，也不是旧报告三角面采样点深度。',
      'separation_mm':'仅对这一对模型，沿X或Y四个正负方向中，刚好不再穿柱的最小平移距离（允许表面接触）。',
      'direction':'东+X、北+Y；数值只用于比较几何重叠程度，不是可直接应用到整条桥架的整改位移。',
      'depth_band':'为本次统计自定义的比较档位，不是施工规范的合格/不合格阈值。'},
    'summary':{'penetration_pairs':len(rows),'normal_contact_pairs':len(contacts),'aabb_only_pairs':len(box_only),'affected_bridge_components':len(groups),'affected_columns':len({r['column'] for r in rows}),
       'column_level_groups':len({(r['level'],r['column']) for r in rows}),'long_vertical_overlap_pairs':[{'bridge':r['bridge'],'column':r['column'],'max_depth_mm':r['max_depth_mm'],'overlap_height_mm':r['actual_intersection_extent_mm'][2]} for r in rows if r['actual_intersection_extent_mm'][2]>1000],'by_column_scope':dict(collections.Counter(r['column_scope'] for r in rows)),
       'by_level':dict(collections.Counter(r['level'] for r in rows)),'depth_bands':bands,'separation_bands':[{'range':label,'total':int(sum(low<r['separation_mm']<=high for r in rows))} for low,high,label in BINS]},
    'validation':{'independent_linear_program_verified_pairs':verified,'all_axis_separation_results_rechecked':True},
    'limits':['反映当前模型几何，不单凭穿入数值认定成因或施工冲突。','750/650柱截面取自5.970–9.900m柱平面并沿用到23m；上部柱截面仍需原结构图逐段复核。','本统计脚本仅读取当前模型；2.0整改历史与1.0冻结结果见桥架工程/版本目录。'],
    'penetrations':sorted(rows,key=lambda r:(-r['max_depth_mm'],r['bridge'],r['column'])),'normal_contacts':contacts,'aabb_only':box_only,'by_bridge':groups}


def write_reports(report):
 path=OUT/'data/桥架立柱穿入深度统计'
 path.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
 with path.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:
  writer=csv.writer(f);writer.writerow(['状态','层','桥架编号','CAD句柄','类型','立柱编号','柱类别','柱宽mm','柱深mm','柱轴Xmm','柱轴Ymm','最大实际内侵mm','深度分档','单轴平移至不穿柱mm','平移方向','实际占入X跨度mm','实际占入Y跨度mm','实际占入Z跨度mm','交叠最低EL','交叠最高EL','水平直段桥架宽mm','水平直段被柱覆盖宽mm','水平直段被柱覆盖宽度百分比'])
  for r in report['penetrations']+report['normal_contacts']+report['aabb_only']:
   writer.writerow([r['status'],r['level'],r['bridge'],r['cad_handle'],r['bridge_type'],r['column'],r['column_scope'],*r['column_section_mm'],*r['column_axis_xy_mm'],r.get('max_depth_mm',''),r.get('depth_band','正常接触' if r['status'].startswith('表面') else '无实际交叠'),r.get('separation_mm',''),r.get('direction',''),*r.get('actual_intersection_extent_mm',['','','']),
      round(100+r['intersection_low_mm'][2]/1000,6) if 'intersection_low_mm' in r else '',round(100+r['intersection_high_mm'][2]/1000,6) if 'intersection_high_mm' in r else '',r.get('bridge_width_mm',''),r.get('overlapped_width_mm',''),r.get('overlapped_width_percent','')])
 s=report['summary'];scope=report['scope'];bands=s['depth_bands'];rows=report['penetrations'];by_scope=s['by_column_scope']
 lines=['# 桥架与立柱穿入程度完整统计','',f"当前模型：{s['penetration_pairs']}组实际穿入、{s['normal_contact_pairs']}组正常接触；涉及{s['affected_bridge_components']}件桥架、{s['affected_columns']}根柱。按构件—柱配对计数，同一构件或同一柱可能出现多次。",'',
   f"核对范围为{scope['bridge_components']}件桥架，以及{scope['columns']}。原主体柱报告已逐对核验一致；新增附属柱另算，不能将两份报告的数量相加。",'',
   '## 统计口径','',report['definitions']['max_depth_mm'],report['definitions']['separation_mm'],report['definitions']['direction'],report['definitions']['depth_band'],'',
   f"## 全部{s['penetration_pairs']}组的深度分档",'', '| 最大实际内侵深度 | L1 | L2 | L3 | 合计 |','|---|---:|---:|---:|---:|']
 for band in bands:lines.append(f"| {band['range']} | {band['L1']} | {band['L2']} | {band['L3']} | {band['total']} |")
 lines += ['', '## 单轴移至刚好不穿柱的距离分档（不是整改方案）','', '| 单对几何退出距离 | 组数 |','|---|---:|']
 for band in s['separation_bands']:lines.append(f"| {band['range']} | {band['total']} |")
 lines += ['', '## 结论与优先核对位置','',f"- {bands[0]['total']}组在10mm内，{bands[0]['total']+bands[1]['total']}组在30mm内；{bands[2]['total']}组在30–60mm，{bands[3]['total']+bands[4]['total']}组超过60mm。不能把所有几何穿入都直接认定为轻微错位。"]
 priority=[r for r in rows if r['max_depth_mm']>60 or r['separation_mm']>100]
 for bridge in sorted({r['bridge'] for r in priority},key=lambda id:-max(r['max_depth_mm'] for r in priority if r['bridge']==id)):
  rr=[r for r in priority if r['bridge']==bridge]
  cases='；'.join(f"{r['column']}：内侵{r['max_depth_mm']:.3f}mm，沿{r['direction']}退出{r['separation_mm']:.3f}mm"+(f"，被柱覆盖宽度约{r['overlapped_width_percent']:.2f}%" if 'overlapped_width_percent' in r else '') for r in rr)
  lines.append(f"- **{bridge}（{rr[0]['bridge_type']}）**：{cases}。")
 long=s['long_vertical_overlap_pairs']
 for r in long:lines.append(f"- **浅但长的擦入**：{r['bridge']} / {r['column']}深度{r['max_depth_mm']:.3f}mm，但沿柱竖向交叠{r['overlap_height_mm']:.3f}mm。竖向长度不能当成穿入深度。")
 for bridge in sorted({r['bridge'] for r in rows}):
  small=sorted({r['max_depth_mm'] for r in rows if r['bridge']==bridge and np.allclose(r['column_section_mm'],[650,650])})
  big=sorted({r['max_depth_mm'] for r in rows if r['bridge']==bridge and np.allclose(r['column_section_mm'],[750,750])})
  if len(small)==1 and len(big)==1 and abs(big[0]-small[0]-50)<.001:
   lines.append(f"- **截面差值实例**：同一{bridge}与650柱内侵{small[0]:.3f}mm、与750柱内侵{big[0]:.3f}mm，恰差50mm；这支持先核对柱截面，不等于可以将柱改小。")
 large=[r for r in rows if np.allclose(r['column_section_mm'],[750,750])];medium=[r for r in large if 30<r['max_depth_mm']<=60]
 lines += [f"- {len(large)}组发生在750×750柱上，其中{len(medium)}组在30–60mm。750比650柱每侧多50mm，与部分成组差值相符，但不能据此确认错位成因或擅自修改柱截面。",
   '- 同一桥架常连续碰到多根柱，应结合整段走向、接口和柱截面核对，不能把本表平移下限直接逐件套用。',
   '- 最深内侵与退出距离不是同一个量；弯头、三通等角部交叠尤其不能只取旧报告的采样点深度当修补量。','',
   *(['![典型位置的实际相交面](../previews/桥架立柱重叠典型案例.png)',''] if rows else ['当前2.0未发现穿柱；整改前69组的明细与典型图已冻结在桥架工程/版本/1.0。','']),
   '## 所有穿入配对（按深度降序）','', '| 桥架 | 立柱 | 柱截面mm | 最深内侵mm | 单轴退出距离mm | 方向 |','|---|---|---|---:|---:|---|']
 for r in rows:lines.append(f"| {r['bridge']} | {r['column']} | {r['column_section_mm'][0]:g}×{r['column_section_mm'][1]:g} | {r['max_depth_mm']:.3f} | {r['separation_mm']:.3f} | {r['direction']} |")
 lines += ['', '## 按桥架构件归并','', '| 桥架 | 类型 | 穿入配对数 | 涉及立柱 | 深度mm |','|---|---|---:|---|---|']
 for r in report['by_bridge']:lines.append(f"| {r['bridge']} | {r['bridge_type']} | {r['pairs']} | {', '.join(r['columns'])} | {', '.join(f'{d:.3f}' for d in r['depths_mm'])} |")
 lines += ['', '## 正常表面接触（不计入穿入）','', '| 桥架 | 立柱 |','|---|---|']
 for r in report['normal_contacts']:lines.append(f"| {r['bridge']} | {r['column']} |")
 lines += ['', '## 仅包围盒候选，未发现实际交叠','', '| 桥架 | 立柱 |','|---|---|']
 for r in report['aabb_only']:lines.append(f"| {r['bridge']} | {r['column']} |")
 verified=report['validation']['independent_linear_program_verified_pairs']
 lines += ['', '## 验证与边界','',f"最大深度已用独立线性规划复核{verified}组；每组最小单轴平移均重新计算确认退出后不再穿入（0.1mm容差）。"]
 lines += ['- '+v for v in report['limits']]
 lines += ['', '[CSV全量数据（含正常接触与包围盒排除项）](桥架立柱穿入深度统计.csv) · [JSON几何数据、坐标与源文件SHA256](桥架立柱穿入深度统计.json)','']
 path.with_suffix('.md').write_text('\n'.join(lines))

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--verify-lp',action='store_true',help='Use SciPy linear programming as an independent depth verification');args=parser.parse_args()
 report=audit(args.verify_lp);write_reports(report);print(json.dumps(report['summary'],ensure_ascii=False));print(report['validation'])
