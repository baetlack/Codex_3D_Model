"""Publish a complete, honest first-pass register without clearing open items."""
from pathlib import Path
import html,json,urllib.parse
from build_factory_batch_v2 import ROOT,REPO,BATCH,CLASSES,save,sha
from check_assembly import script

def publish():
    project=json.loads((ROOT/'project.json').read_text());catalog=json.loads((ROOT/'catalog.json').read_text())['models'];cfg=json.loads((REPO/'水解总装工程/assembly.json').read_text());overrides=script(ROOT/'equipment_versions.js','EQUIPMENT_VERSION_OVERRIDES')
    installed={p['id']:p for p in cfg['equipment']};unplaced={p['id']:p for p in cfg['unplaced']};unit_rows=[];classes=[]
    for key in sorted(set(project['revisions'])|set(project.get('reviews',{}))):
        out=ROOT/'版本/2.0'/key;units=[q for q in catalog if q['id'][:6]==key];name=units[0]['name'];new=key in CLASSES
        if key in project['reviews']:
            record=json.loads((out/'复核记录.json').read_text());pending=record['pending'];action=record['action'];version=record['version'];kind='retain';source='台账、原示图、布置和基础资料'
        else:
            params=json.loads((out/'设备/参数.json').read_text());version=project['revisions'][key]['version'];action=project['revisions'][key]['status'];kind='new' if new else 'previous';source=params.get('source_drawing','前批来源记录')
            limits=params.get('limits',[]);pending=[str(s) for s in limits if isinstance(s,str) and any(w in s for w in ['待','未','不一致','差异','不能','缺','不符','暂'])]
            if not pending:pending=[project['revisions'][key]['status']]
            if new:
                info=overrides['review_info'][key];info['pending']=pending;info['drawing']=str(Path(source).relative_to(ROOT.name)) if source.startswith(ROOT.name+'/') else None
                dimensions=params['dimensions_mm']
                if 'nominal_inner_diameter_mm' in dimensions:info['sizing']=f'公称内径{dimensions["nominal_inner_diameter_mm"]}；钢壳外径{dimensions["steel_outer_diameter_mm"]}；公称罐高{dimensions["nominal_body_height_mm"]}mm。'
                elif key=='L41B05':info['sizing']='筒段Ø1000×3800；两端封头各275，总长4350；轴高700、鞍座中心距2000mm。'
                else:info['sizing']='保持已确认Ø5900×4700及3076搅拌总高；接口口高仍受旧盖面基准限制。'
                path=out/'整改说明.html';text=path.read_text();link='../../../'+urllib.parse.quote(info['drawing'],safe='/') if info['drawing'] else None
                if link:text=text.replace('<p>来源完整图纸见设备库详情下载。</p>','<p><a download href="'+link+'">新增原始总图 DXF</a></p>')
                if key in ['F41B02','F41B05','F41B06'] and '三槽主低口与模型轴系依据' not in text:
                    text=text.replace('</h1>','</h1><p><a href="三槽方位依据.json">三槽主低口与模型轴系依据</a> · <a href="../../../data/连续整改_20261120/来源_三槽布置方向.png">布置图方向摘录</a></p>',1)
                path.write_text(text)
        for unit in units:
            tag=unit['id'];p=installed.get(tag);unit_rows.append({'id':tag,'class':key,'name':name,'version':version,'disposition':kind,'action':action,'position_mm':p['position_mm'] if p else None,'rotation_deg':p.get('rotation_deg') if p else None,'mirror_y':p.get('mirror_y',False) if p else None,'origin_EL':100+p['position_mm'][2]/1000 if p else None,'xy_status':p.get('xy_status','待定位') if p else '待定位','z_status':p.get('z_status','待核') if p else '待定位','orientation_status':p.get('orientation_status','待核') if p else '待定位','source':source,'pending':pending,'model_entry':f'版本/2.0/{key}/index.html'})
        classes.append({'id':key,'name':name,'kind':kind,'version':version,'action':action,'units':[u['id'] for u in units],'pending':pending,'unplaced':sum(u['id'] in unplaced for u in units)})
    assert len(unit_rows)==len({p['id'] for p in unit_rows})==99 and len(classes)==35
    save(BATCH/'99台复核清单.json',{'scope':'首轮证据复核和可实施的模型修正；未决项未被清除','counts':{'classes':35,'items':99,'versioned_items':58,'retained_items':41,'placed':72,'unplaced':27},'classes':classes,'units':unit_rows})
    (ROOT/'equipment_versions.js').write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(overrides,ensure_ascii=False,separators=(',',':'))+';\n')
    rows=[]
    for q in classes:
        label={'new':'本轮模型更新','previous':'前批工作版','retain':'保留原几何 / 待核'}[q['kind']];details=''.join('<li>'+html.escape(s)+'</li>' for s in q['pending'])
        rows.append('<tr data-kind="'+q['kind']+'" data-unplaced="'+str(q['unplaced'])+'"><td><b>'+q['id']+'</b><br>'+html.escape(q['name'])+'</td><td>'+label+'<br>'+html.escape(q['action'])+'</td><td><details><summary>'+str(len(q['units']))+'台 / '+str(q['unplaced'])+'台待定位</summary>'+html.escape('、'.join(q['units']))+'</details></td><td><ul>'+details+'</ul></td><td><a href="2.0/'+q['id']+'/index.html">模型</a><br><a href="2.0/'+q['id']+'/整改说明.html">依据</a></td></tr>')
    css='body{margin:28px auto;max-width:1500px;padding:0 24px;background:#101923;color:#dce8ef;font:14px/1.7 sans-serif}a{color:#7cdce6}button{background:#1c303d;border:1px solid #49616e;color:#dce8ef;padding:8px 12px;margin:4px;cursor:pointer}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #344957;padding:12px;vertical-align:top;text-align:left}td:first-child{width:160px}td:nth-child(2){width:290px}ul{padding-left:18px;margin:0}.stats{font-size:18px;padding:16px;background:#182a36}'
    controls='<button data-filter="all">全部35类</button><button data-filter="new">本轮8类模型更新</button><button data-filter="retain">保留待核19类</button><button data-filter="unplaced">含待定位设备</button>'
    script_filter="<script>for(const b of document.querySelectorAll('button[data-filter]'))b.onclick=()=>{let v=b.dataset.filter;for(const r of document.querySelectorAll('tr[data-kind]'))r.hidden=!(v==='all'||r.dataset.kind===v||v==='unplaced'&&Number(r.dataset.unplaced)>0)};</script>"
    text='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>35类99台设备首轮复核</title><style>'+css+'</style><h1>设备首轮复核总览</h1><div class="stats">35类 · 99项已覆盖　｜　58项进入逐类2.0　｜　41项保留原几何</div><p>首轮覆盖表示每一项都有处置记录；制造详图、安装支承和工艺绝对方位仍按下表保留。72台在场景、27台待定位，原XYZ/旋转及土建/桥架保持。立式泵型式不符、葫芦尺寸缺依据等项目未标作整改通过。</p><p><a href="index.html">版本目录</a> · <a href="../data/连续整改_20261120/99台复核清单.json">99台完整JSON</a> · <a href="../../水解总装工程/index.html">当前总装</a> · <a href="1.0/index.html">冻结1.0</a></p>'+controls+'<table><thead><tr><th>位号组</th><th>本体处置</th><th>单台位号</th><th>保留的待核项</th><th>查看</th></tr></thead><tbody>'+''.join(rows)+'</tbody></table>'+script_filter
    spatial=BATCH/'建筑空间复核.json'
    if spatial.exists():
        b=json.loads(spatial.read_text());inputs=b.get('input_sha256',{});valid=inputs.get('assembly')==sha(REPO/'水解总装工程/assembly.json') and inputs.get('building')==sha(REPO/'厂房外观模型/建筑/model_data.js') and all(digest==sha(REPO/cfg['assets'][key]['source']) for key,digest in inputs.get('models',{}).items())
        if valid:
            total=json.loads((REPO/'水解总装工程/data/碰撞报告.json').read_text());summary=f'<p>总装已检查范围：{len(total["intersections"])}处实体穿插、{len(total["normal_contacts"])}处正常表面接触；本批{len(b["checked_units"])}台对完整建筑补充检查：{len(b["solid_intersections"])}处实体穿插。'
            text=text.replace('<table>',summary+'<a href="../data/连续整改_20261120/建筑空间复核.html">范围、限制及证据</a></p><table>',1)
    (ROOT/'版本/复核总览.html').write_text(text)
    print('Published first-pass records for 35 classes / 99 items.')

if __name__=='__main__':publish()
