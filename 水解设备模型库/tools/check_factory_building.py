"""Screen changed equipment against the complete building mesh, including holes."""
import json,html
import numpy as np
from build_factory_batch_v2 import ROOT,REPO,BATCH,CLASSES,mesh,save,sha
import check_assembly as ck
from test_l41b02 import volume_witness

def run():
    cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());building=ck.script(REPO/'厂房外观模型/建筑/model_data.js','BUILDING_MODEL')['parts'];environment=[]
    for i,p in enumerate(building):
        t=ck.tri([p])
        if len(t):environment.append(ck.object_mesh(p['name']+' #'+str(i),'building',t))
    hits=[];candidates=0;units=[];cache={};low=np.asarray([q['low'] for q in environment]);high=np.asarray([q['high'] for q in environment])
    for q in cfg['equipment']:
        if q['asset'] not in CLASSES:continue
        if q['asset'] not in cache:cache[q['asset']]=mesh(REPO/cfg['assets'][q['asset']]['source'])
        parts=cache[q['asset']]
        if q['asset']=='D41B02':parts=[p for p in parts if p['name'].startswith('接口_')]
        units.append(q['id']);found=0
        for part in parts:
            t=ck.tri([part],q['position_mm'],q['rotation_deg'],mirror_y=q.get('mirror_y',False))
            if not len(t):continue
            a=ck.object_mesh(q['id'],'equipment',t)
            candidate_ids=np.flatnonzero(np.all(np.minimum(a['high'],high)-np.maximum(a['low'],low)>.1,axis=1))
            for index in candidate_ids:
                b=environment[index];candidates+=1
                touching=np.flatnonzero(np.all(b['th']>=a['low'],axis=1)&np.all(b['tl']<=a['high'],axis=1))
                surface=ck.surface(a,ck.object_mesh(b['id'],b['kind'],b['t'][touching])) if len(touching) else None
                contained=False
                if surface is None:
                    if np.all(a['low']>=b['low']) and np.all(a['high']<=b['high']):contained=ck.inside(a['t'][0,0],b['t'])
                    if not contained and np.all(b['low']>=a['low']) and np.all(b['high']<=a['high']):contained=ck.inside(b['t'][0,0],a['t'])
                if surface is None and not contained:continue
                witness=volume_witness(a,b) or volume_witness(b,a)
                if witness is not None:
                    hits.append({'equipment':q['id'],'equipment_part':part['name'],'building_part':b['id'],'point_inside_both_mm':witness,'z_status':q['z_status'],'orientation_status':q['orientation_status']});found+=1
        print(q['id'],'checked; intersections',found,flush=True)
    result={'status':'checked','checked_units':units,'complete_building_objects':len(environment),'aabb_candidates':candidates,'solid_intersections':hits,'tolerance_mm':.1,'scope':'新增本体/接口逐部件对完整建筑；包围盒候选按部件计；D41B02已锁定主体不重复处理，仅检查新接口；孔洞使用真实网格','limits':['表面接触不作为穿入','楼板厚及部分建筑构件为展示口径，几何相交不等于施工冲突','设备绝对工艺方位、暂用标高及盖面基准待核的项目不因本报告解除','桥架/柱、设备/柱及设备互相另见总装公共相交报告']}
    result['input_sha256']={'building':sha(REPO/'厂房外观模型/建筑/model_data.js'),'assembly':sha(REPO/'水解总装工程/assembly.json'),'models':{key:sha(REPO/cfg['assets'][key]['source']) for key in cfg['assets'] if key in CLASSES}}
    save(BATCH/'建筑空间复核.json',result)
    rows=''.join('<tr><td>'+r['equipment']+'</td><td>'+html.escape(r['building_part'])+'</td><td>'+str(r['point_inside_both_mm'])+'</td><td>'+html.escape(r['z_status'])+'</td></tr>' for r in hits)
    page='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>本批建筑空间复核</title><style>body{max-width:1200px;margin:30px auto;padding:20px;background:#101923;color:#dce8ef;font:15px/1.8 sans-serif}a{color:#7cdce6}td,th{padding:10px;border-bottom:1px solid #405463}</style><h1>新增设备对完整建筑的空间复核</h1><p>检查'+str(len(units))+'台；完整建筑'+str(len(environment))+'个网格对象；包围盒候选'+str(candidates)+'对；有实体内部证据的穿插'+str(len(hits))+'对。</p><p>表面接触正常；楼板展示厚度、未决标高与方位需结合原图判断，不直接认定施工冲突。</p><p><a href="建筑空间复核.json">完整JSON证据</a> · <a href="../../版本/复核总览.html">35类复核总览</a></p><table><tr><th>设备</th><th>建筑构件</th><th>两实体内部见证点/mm</th><th>标高状态</th></tr>'+rows+'</table>'
    (BATCH/'建筑空间复核.html').write_text(page);print('Complete building screening finished:',len(hits),'pairs.',flush=True)
if __name__=='__main__':run()
