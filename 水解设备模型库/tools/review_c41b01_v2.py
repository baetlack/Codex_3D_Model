"""C41B01 only: revise the two lined outlets; preserve the accepted h lid and placements."""
from pathlib import Path
import copy,json,hashlib,shutil,html
import numpy as np
from build_c41b04_v2 import geo,pipe,export
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent;OUT=ROOT/'版本/2.0/C41B01';HISTORY=OUT/'历史/2.0-C41B01-01_逐类复核前';VERSION='2.0-C41B01-02'
def read(p):return json.loads(p.read_text())
def write(p,d):
    crlf=p.exists() and b'\r\n' in p.read_bytes()
    p.parent.mkdir(parents=True,exist_ok=True)
    value=json.dumps(d,ensure_ascii=False,indent=2)+'\n'
    p.write_bytes(value.replace('\n','\r\n').encode() if crlf else value.encode())
def mesh(p):return json.loads(p.read_text().split('=',1)[1].rstrip(';\n'))
def lined_outlets(old,ports):
    geo.parts.clear();changed={'接口_c1接管','接口_c1法兰','接口_c2接管','接口_c2法兰'}
    for part in old:
        if part['name'] not in changed:geo.add(part['name'],part['color'],part['vertices'],part['faces'])
    for key,od,wall,lining_od,bore in [('c1',159,4.5,136,100),('c2',219,6,165,125)]:
        p=next(x for x in ports if x['id']==key);end=np.array(p['face_center_mm']);axis=np.array(p['normal']);neck=end-axis*p['flange_thickness_mm']
        # Keep original opening location, projection, flange OD and thickness.
        original=next(x for x in old if x['name']=='接口_'+key+'接管');vs=np.array(original['vertices']);start=end-axis*(np.dot(end,axis)-np.min(vs@axis))
        pipe('接口_'+key+'接管',start,neck,od/2,(od-2*wall)/2,original['color'])
        pipe('接口_'+key+'法兰',neck,end,p['flange_OD_mm']/2,lining_od/2)
        # Source calls out a 295 mm sleeve; its outer end protrudes 2 mm.
        pipe('接口_'+key+'_瓷套管',end-axis*293,end+axis*2,lining_od/2,bore/2,'#d6dddd')
        p.update(neck_OD_mm=od,wall_mm=wall,ceramic_sleeve_OD_mm=lining_od,ceramic_bore_mm=bore,ceramic_length_mm=295,ceramic_end_projection_mm=2,
                 role='稀释水出口（衬DN100瓷套管）' if key=='c1' else '底水出口（衬DN125瓷套管）')
    return changed

def main():
    if not HISTORY.exists():
        HISTORY.mkdir(parents=True)
        for name in ['设备','安装表.json','来源量测.json','整改说明.md','整改说明.html','预览_设备.png','预览_基础配合.png','H口盖位置修正.json']:
            src=OUT/name
            if src.is_dir():shutil.copytree(src,HISTORY/name)
            elif src.exists():shutil.copy2(src,HISTORY/name)
        write(HISTORY/'归档清单.json',{str(p.relative_to(HISTORY)):hashlib.sha256(p.read_bytes()).hexdigest() for p in HISTORY.rglob('*') if p.is_file()})
    old=mesh(HISTORY/'设备/model_data.js');params=read(HISTORY/'设备/参数.json');ports=params['ports'];changed=lined_outlets(old,ports);bounds=export(OUT/'设备','C41B01')
    new=mesh(OUT/'设备/model_data.js');after={p['name']:p for p in new}
    for p in old:
        if p['name'] not in changed:assert after[p['name']]==p,p['name']
    assert np.allclose(bounds,np.array(params['bounds_mm'])+[0,2,0])
    installation=read(HISTORY/'安装表.json')
    for instance in installation:instance['equipment_version']=VERSION
    write(OUT/'安装表.json',installation)
    roles={'a':'工艺水进口','b1/k1':'蒸汽进口 / 插入导管安装口','b2/k2':'蒸汽冷凝液进口 / 插入导管安装口','d':'溢流口','e':'液位计口','f':'测温口','g':'备用口','h':'简易人孔','m':'排气口'}
    for p in ports:
        if p['id'] in roles:p['role']=roles[p['id']]
    limits=['h侧视接管Ø530与俯视内圈Ø490的差异保留；本轮保留已修正的盖面/法兰/提手同心关系。','其他管口的未标法兰厚度和伸出细部仍为展示值；未逐项升级为制造确认。','c1/c2瓷套管按详图长度295、外端2表达；保留原接口中心、朝向和法兰外廓，不为配合挪动接口。','两台中心与原点EL112.200沿用现布置；新接口绝对工艺方位待核，定位不等于全部接口已确认。','不展开槽内导管、衬砖和加固件；不增加本类图纸未列的搅拌器。']
    params.update(version=VERSION,bounds_mm=bounds,ports=ports,limits=limits,review_status='逐类复核完成，待用户确认后进入下一类')
    write(OUT/'设备/参数.json',params);top=read(ROOT/'parameters/C41B01.json');top.update(params);write(ROOT/'parameters/C41B01.json',top)
    evidence={'version':VERSION,'reference_standard':['L41B02','F41B04','L41B03'],'source':params['source_drawing'],'source_sha256':params['source_sha256'],
      'adopted':['保留内径3500、钢壳外径3520、罐高4000及原底板/盖面','c1钢接管Ø159×4.5，瓷套管Ø136/Ø100×295','c2钢接管Ø219×6，瓷套管Ø165/Ø125×295','h盖位置已修好，保持；两台安装与原Ø3600×200基础保持'],
      'handles':{'c1_role':'289CC','c1_pipe':'29227','c1_detail_pipe':'31FA2','c1_ceramic_bore':'30BFD','c1_ceramic_OD':'30C06','c1_ceramic_BOM':'341B7','c2_role':'289D2','c2_pipe':'28A2A','c2_ceramic_BOM':'341B0'},
      'changed_existing_parts':sorted(changed),'added_parts':['接口_c1_瓷套管','接口_c2_瓷套管'],'unchanged_existing_parts':len(old)-len(changed),'before_parts':len(old),'after_parts':len(new),'installation_changed':False,'foundation_changed':False,'pending':limits}
    write(OUT/'逐类复核.json',evidence)
    text='C41B01A/B 热水预热槽 · '+VERSION+'\n\n本轮按L41B02/F41B04/L41B03逐类标准：明确尺寸与显示假设分开、本体与基础独立、原位置不为消碰撞而移动。\n\n'+ '\n\n'.join(evidence['adopted'])+'\n\n待核：\n'+ '\n'.join(limits)
    (OUT/'整改说明.md').write_text(text)
    rows=''.join('<tr><td>'+html.escape(p['id'])+'</td><td>'+html.escape(p.get('role','待核'))+'</td><td>DN'+str(p['DN'])+'</td></tr>' for p in ports)
    markup='<html lang="zh-CN"><meta charset="utf-8"><title>C41B01逐类复核</title><style>body{max-width:1100px;margin:30px auto;padding:20px;background:#101923;color:#dce8ef;font:15px/1.8 sans-serif}a{color:#7cdce6}td,th{border-bottom:1px solid #425561;padding:8px}img{width:49%;vertical-align:top}</style><h1>热水预热槽 · 逐类复核02版</h1><p><a href="index.html?v=c1-review02">查看模型</a> · <a href="历史/2.0-C41B01-01_逐类复核前/设备/C41B01.glb" download>下载本轮前模型</a></p><h2>本轮修正</h2>'+''.join('<p>'+html.escape(s)+'</p>' for s in evidence['adopted'])+'<h2>管口用途</h2><table><tr><th>口号</th><th>名称/用途</th><th>公称口径</th></tr>'+rows+'</table><h2>基础与安装</h2><p>原圆基础Ø3600×200，含50二次浇筑；A：X9.500/Y39.5998，B：X29.500/Y17.9998 m；两台原点EL112.200、旋转0°保持，绝对工艺方位继续待核。</p><h2>保留的待核项</h2>'+''.join('<p>'+html.escape(s)+'</p>' for s in limits)+'<h2>本轮前 / 本轮后</h2><img src="历史/2.0-C41B01-01_逐类复核前/预览_设备.png"><img src="预览_设备.png?v=c1-review02"></html>'
    (OUT/'整改说明.html').write_text(markup)
    project=read(ROOT/'project.json');project['revisions']['C41B01'].update(version=VERSION,status='逐类复核02：修正c1/c2瓷衬出口；h盖、原基础和位置保持，待用户确认');project['review_workflow']={'mode':'逐类确认','current':'C41B01','status':'待用户确认','reference':['L41B02','F41B04','L41B03']};write(ROOT/'project.json',project)
    cat=read(ROOT/'catalog.json')
    for q in cat['models']:
        if q['id'].startswith('C41B01'):q['model_version']=VERSION
    write(ROOT/'catalog.json',cat)
    path=ROOT/'equipment_versions.js';ov=mesh(path) if False else json.loads(path.read_text().split('=',1)[1].rstrip(';\n'));ov['equipment']['C41B01']['bounds']=bounds;ov['review_info']['C41B01'].update(action='逐类复核02：修正c1/c2钢接管和瓷套管；待用户确认',pending=limits);ov['ledger']['C41B01'].update({'状态':'2.0逐类复核02 · 待用户确认','建模口径或缺项':'c1/c2按详图表达瓷套管，h盖和原基础/位置保持；绝对方位及未标细部待核。'});path.write_text('window.EQUIPMENT_VERSION_OVERRIDES='+json.dumps(ov,ensure_ascii=False,separators=(',',':'))+';\n')
    print(json.dumps({'version':VERSION,'preserved':len(old)-len(changed),'changed':4,'added':2,'placement_changes':0},ensure_ascii=False))
if __name__=='__main__':main()
