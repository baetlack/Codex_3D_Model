'use strict';

const byId = id => document.getElementById(id);
const batch = '示图建模_20260521/';
const ledger = window.EQUIPMENT_LEDGER || {};
const overrides=window.EQUIPMENT_VERSION_OVERRIDES||{};
const rows = (ledger.清单 || []).map(row=>({...row,...(overrides.ledger?.[row.位号]||{})}));
const rowsByTag = new Map(rows.map(row=>[row.位号,row]));
const typeModels = window.BATCH_MODELS || {};
const foundationRoot = '../水解桥架工程/models/设备/设备基础_20261106/';
const foundationSourceRoot = '../水解桥架工程/data/原始资料/设备基础/';
const foundations = window.EQUIPMENT_FOUNDATIONS ? JSON.parse(JSON.stringify(window.EQUIPMENT_FOUNDATIONS)) : null;
if (foundations) {
 for (const [key,value] of Object.entries(overrides.equipment||{})) foundations.equipment[key]={...foundations.equipment[key],...value};
 for (const [key,value] of Object.entries(overrides.foundations||{})) foundations.assets[key]={...foundations.assets[key],...value};
}
const foundationDir=key=>foundations.assets[key].dir||(foundationRoot+key+'/');
const archiveImages = {
  C41B02:['搅拌驱动详图','来源_搅拌驱动详图.png'],
  D41B02:['用户侧视图','来源_用户侧视图.png']
};
const list = byId('list'), detail = byId('detail'), views = byId('views');
const search = byId('search'), state = byId('state'), group = byId('group');
const foundationMode = byId('foundation-mode');
const overlay = byId('overlay'), ctx = overlay.getContext('2d');
const meshCache = new Map();
let rowTag=rows[0]?.位号, parts=[], partGroups=new Map(), dimensions, civilDimensions, selection=0, viewer;

function element(tag, text='', className='') {
  const node=document.createElement(tag);
  node.textContent=text;
  node.className=className;
  return node;
}

function link(label, url, download=false) {
  const node=element('a',label);
  node.href=url;
  if (download) node.download='';
  else { node.target='_blank'; node.rel='noopener'; }
  return node;
}

function field(parent, label, value) {
  if (value==null || value==='') return;
  const line=element('div');
  line.append(element('b',label+'　'),document.createTextNode(value));
  parent.append(line);
}

function section(parent, title) {
  const node=element('section','','section');
  node.append(element('div',title,'label'));
  parent.append(node);
  return node;
}

function disclosure(parent, title) {
  const node=element('details');
  node.append(element('summary',title));
  parent.append(node);
  return node;
}

function sources() {
  const target=byId('sources');
  target.append(element('div','2026.5.21 台账 · 工作表「'+(ledger.工作表||'水解')+'」'));
  target.append(link('完整台账对照 JSON',batch+'设备台账对照.json'));
  for (const [title,file] of [['原始 XLS 台账',ledger.台账],['新版 DXF 示图',ledger.图纸],['设备布置 DXF',ledger.布置图]]) {
    if (file) target.append(link(title,batch+'原始资料/'+encodeURIComponent(file),true));
  }
  if (foundations) target.append(link('设备基础 DXF',foundationSourceRoot+foundations.source,true));
  if (foundations?.supplemental_source) target.append(link('烟囱与洗涤塔钢塔架 DXF',foundationSourceRoot+foundations.supplemental_source,true));
  if (foundations) target.append(link('DXF 逐项核对清单',foundationRoot+'DXF逐项核对.md'));
  for (const [key,title] of Object.entries({cool_body:'冷却器本体侧视',cool_stand:'冷却器支架侧视',pump:'共用泵俯视',hoist:'葫芦共用侧视'})) {
    for (const view of Object.values(ledger.补充视图?.[key]||{})) target.append(link(title,batch+view.文件));
  }
  target.append(link('原台账汇总表',batch+'index.html'));
}

function renderList() {
  const keyword=search.value.trim().toLowerCase();
  const buttons=[];
  for (const row of rows) {
    if (state.value && state.value!==row.状态) continue;
    const fields=[row.位号,row.名称,row.台账规格,row.材料,row.建模口径或缺项];
    if (!fields.join(' ').toLowerCase().includes(keyword)) continue;
    const active=row.位号===rowTag;
    const button=element('button','',active?'active':'');
    if (active) button.setAttribute('aria-current','true');
    button.dataset.id=row.位号;
    button.append(element('strong',row.名称),
      element('small',[row.位号,row.数量+row.单位,row.状态].filter(Boolean).join(' · ')));
    button.onclick=()=>select(row.位号);
    buttons.push(button);
  }
  byId('count').textContent='显示 '+buttons.length+' / '+rows.length+' 个位号组';
  list.replaceChildren(...(buttons.length?buttons:[element('p','没有匹配的设备。','note')]));
}

function figure(label, url) {
  const fig=element('figure'), anchor=link('',url), img=element('img');
  img.alt=label;
  img.loading='lazy';
  img.onerror=()=>fig.remove();
  img.src=url;
  anchor.append(img);
  fig.append(anchor,element('figcaption',label));
  views.append(fig);
}

function typeInfo(row) {
  const entry=row?.模型入口;
  if (!entry) return null;
  const key=new URL(entry,new URL(batch,location.href)).searchParams.get('model');
  if (key && Object.hasOwn(typeModels,key)) {
    const dir=batch+'模型/'+key+'/';
    const model=typeModels[key];
    const extra=model.layout?[-3*Math.PI/4,'泵端轴测']:key==='P41B10'?[Math.PI*.83,'进风侧轴测']:null;
    return {key,dir,stem:key,entry:batch+entry,model,extra};
  }
  const match=entry.match(/^\.\.\/(设备档案\/([^/]+))\/3d\.html$/);
  if (match) return {key:match[2].split('_')[0],dir:match[1]+'/',stem:match[2],entry:match[1]+'/3d.html',archive:true};
  return null;
}

function renderLedger(row, type) {
  const info=section(detail,'台账与建模依据');
  field(info,'台账位号组',row.位号);
  field(info,'数量',row.数量+row.单位);
  field(info,'台账规格',row.台账规格);
  field(info,'材料',row.材料);
  field(info,'备注',row.备注);
  field(info,'台账行',row.台账行);
  field(info,'建模状态',row.状态);
  field(info,'建模依据',row.建模口径或缺项);
  if (type?.key && type.key!==row.位号.slice(0,6)) field(info,'共用类型模型',type.key);
  if (row.附件规格?.length) {
    const panel=disclosure(info,'附件与传动规格');
    const items=element('ul');
    for (const item of row.附件规格) items.append(element('li',[item.名称,item.规格,item.型号].filter(Boolean).join(' · ')));
    panel.append(items);
  }
  const modifications=(ledger.设备图修改表水解段||[]).filter(item=>item.名称===row.名称);
  if (modifications.length) {
    const panel=disclosure(info,'设备图修改表');
    for (const item of modifications) {
      field(panel,'原表位号 / 行',item.原表位号+' / '+item.台账行);
      field(panel,'改造说明',item.改造说明);
      field(panel,'传动参数',item.传动参数);
    }
  }
  const measure=row.尺寸量测;
  if (measure) {
    const panel=disclosure(info,'布置图量测');
    for (const [key,label] of Object.entries({
      来源设备:'来源设备',布置图:'布置图',量测性质:'量测性质',布置图投影长宽_mm:'投影长 × 宽',
      模型长宽高_mm:'模型长 × 宽 × 高',出口中心_xy_mm:'出口中心 X / Y',
      出口法兰外径_mm:'出口法兰外径',进口法兰外径_mm:'进口法兰外径'
    })) {
      if (measure[key]!=null) {
        const value=Array.isArray(measure[key])?measure[key].join(' × '):measure[key];
        field(panel,label,key.endsWith('_mm')?value+' mm':value);
      }
    }
  }
  const refs=new Map();
  const add=(label,url)=>{if(url && !refs.has(url))refs.set(url,label);};
  for (const [label,view] of Object.entries(row.视图||{})) add('DXF '+label,view.文件);
  for (const [label,view] of Object.entries(type?.model?.views||{})) add('模型依据 · '+label,view.文件);
  add('布置图量测轮廓',measure?.布置图量测视图);
  add('共用外形示意',row.外形示意);
  add('外形参考图',type?.model?.reference);
  add('进出口参考图',type?.model?.portsReference);
  add('模型量测轮廓',type?.model?.layout);
  const drawings=element('div','','links');
  for (const [url,label] of refs) drawings.append(link(label,batch+url));
  const archive=archiveImages[type?.key];
  if (archive) drawings.append(link(archive[0],type.dir+archive[1]));
  if (drawings.childElementCount) info.append(drawings);
}

function tagForRow(row){return row?.位号?.slice(0,6);}
function renderDetail(row, type, foundationIds, civilOnly) {
  detail.replaceChildren();
  views.replaceChildren();
  if (!row) return;
  detail.append(element('div','台账位号组 · 类型模型','label'));
  detail.append(element('h2',row.名称),element('b',row.位号));
  const clean=foundations?.equipment?.[type?.key];
  const bounds=clean?.bounds||type?.model?.bounds;
  if (bounds && !civilOnly) field(detail,'设备包络 X × Y × Z',bounds.join(' × ')+' mm');
  if (type && !civilOnly) {
    const dir=clean?.dir||(clean?foundationRoot+clean.path:type.dir);
    const stem=clean?type.key:type.stem;
    const downloads=element('div','','links');
    downloads.append(link('原类型档案',type.entry),link('设备 GLB',dir+stem+'.glb',true),
      link('设备 OBJ',dir+stem+'.obj',true),link('材质 MTL',dir+stem+'.mtl',true),
      link('设备参数 JSON',dir+'参数.json'));
    detail.append(downloads);
  }
  for (const [label,view] of Object.entries(row.视图||{})) figure((['C41B02','L41B01'].includes(tagForRow(row))&&overrides.version?'1.0旧示图 ':'DXF ')+label,batch+view.文件);
  if (tagForRow(row)==='C41B02'&&overrides.version) {figure('2.0新增总图主视','版本/2.0/C41B02/来源_主视.png');figure('2.0新增总图俯视','版本/2.0/C41B02/来源_俯视.png');}
  if (row.尺寸量测?.布置图量测视图) figure('布置量测',batch+row.尺寸量测.布置图量测视图);
  renderLedger(row,type);
  if (tagForRow(row)==='C41B02' && overrides.version) {
    const info=section(detail,'本类2.0整改与安装');
    field(info,'安装链','楼面EL112.000 → 圆台顶/型钢底EL112.150 → 槽底EL112.310 → 槽顶EL117.310 → 电机顶EL119.495');
    field(info,'待核','新接口绝对方位；POS EL是否指型钢底。m高座、b/j切向共座和g/h直套管已按详图修正；部分未标厚度仍列包络。');
    const links=element('div','','links');links.append(link('1.0冻结原版','版本/1.0/index.html'),link('本类整改说明','版本/2.0/C41B02/整改说明.html'),link('01/02结构对照','版本/2.0/C41B02/修订对比.html'),link('5台安装表','版本/2.0/C41B02/安装表.json'),link('新增设备总图','水解设备图纸/'+encodeURIComponent('钛液预热槽(C41B02A-E).dxf'),true));info.append(links);
  }
  if (tagForRow(row)==='C41B04' && overrides.equipment?.C41B04) {
    const info=section(detail,'本类2.0整改与安装');
    field(info,'尺寸基准','外壳Ø1300 / 换热块Ø1200；端面高4812；四托耳承托EL104.500；底端EL101.888 / 顶端EL106.700。02版已删除推断的大环、外露杆及配套弹簧/螺母。');
    field(info,'图纸整合','保持6台设备布置位置及旋转/镜像，AB钢架随设备调整约200mm；单组梁网4275×1875不变。原台账230㎡与条件图240㎡差异保留。');
    const links=element('div','','links');links.append(link('本类整改说明','版本/2.0/C41B04/整改说明.html'),link('1.0/2.0结构对照','版本/2.0/C41B04/修订对比.html'),link('厂家条件图PDF','水解设备图纸/'+encodeURIComponent('偏钛酸酸冷却器(C41B04A-F).pdf'),true),link('6台安装表','版本/2.0/C41B04/安装表.json'));info.append(links);
    figure('厂家条件图 · 主视','版本/2.0/C41B04/来源_主视.png');figure('厂家条件图 · 俯视','版本/2.0/C41B04/来源_俯视.png');
  }
  if (tagForRow(row)==='D41B01' && overrides.equipment?.D41B01) {
    const info=section(detail,'本类2.0整改与安装');
    field(info,'尺寸与安装','钢壳内径1800/外径1816，保温60；四托耳底EL111.000，槽顶EL111.600，电机顶EL113.103。5台统一新本体。');
    field(info,'支架与待核','B/C、D/E成对支架，平面中心距2600、承托高2500；截面沿用示意。平面2600与剖面水平2500差100待核。A支架及标高适用性待核；新接口绝对方位待工艺方位图。');
    const links=element('div','','links');links.append(link('本类整改说明','版本/2.0/D41B01/整改说明.html'),link('1.0/2.0结构对照','版本/2.0/D41B01/修订对比.html'),link('新增设备总图','水解设备图纸/'+encodeURIComponent('晶种制备槽(D41B01A-E).dxf'),true),link('5台安装表','版本/2.0/D41B01/安装表.json'));info.append(links);
    figure('新增总图 · 主视','版本/2.0/D41B01/依据_主视.png');figure('新增总图 · 俯视','版本/2.0/D41B01/依据_俯视.png');figure('刚性环耳式支座详图','版本/2.0/D41B01/依据_托耳.png');
  }
  if (tagForRow(row)==='L41B01' && overrides.equipment?.L41B01) {
    const info=section(detail,'本类2.0整改与支承');
    field(info,'本体','内径1200/外径1216；上下筒体、锥斗与中心排渣。盖顶距底口约1446，顶口至1566；5管口、3耳、24M20连接。');
    field(info,'安装待核','按用户选择保留6台X/Y和暂用Z。A/C/E按INSERT负比例纠正镜像；三耳承托EL及承托梁/支墩未明确，不与旧圆台组合。新接口绝对方位待工艺图。');
    const links=element('div','','links');links.append(link('本类整改说明','版本/2.0/L41B01/整改说明.html'),link('1.0/2.0结构对照','版本/2.0/L41B01/修订对比.html'),link('新增设备总图','水解设备图纸/'+encodeURIComponent('水解过滤器.dxf'),true),link('6台安装表','版本/2.0/L41B01/安装表.json'),link('1.0旧库（搜索L41B01查看圆台）','版本/1.0/快照/水解设备模型库/index.html'));info.append(links);
    figure('新总图 · 主剖视','版本/2.0/L41B01/依据_主视.png');figure('新总图 · 俯视','版本/2.0/L41B01/依据_俯视.png');
  }
  if (tagForRow(row)==='F41B03' && overrides.equipment?.F41B03) {
    const info=section(detail,'本类2.0校核与支承差异');
    field(info,'显示范围','仅Ø1000×1000直筒段及四耳底板；未提供完整侧视/总图，不推断封头、盖板和管口。');
    field(info,'本次修正','Ø1100是四孔分度圆，已撤下误作实体的两端圈；补四个Ø16.5安装孔。壁厚12、耳板厚24及耳底高度仍是显示暂用值。');
    field(info,'支承未闭合','托耳外端距支墩内缘8.75mm，孔心与预埋板心相差200mm，平面搭接面积0。过渡件、托耳高度、承托EL及共同方位待核，未向总装新增本类支墩。');
    const links=element('div','','links');links.append(link('本类校核说明','版本/2.0/F41B03/整改说明.html'),link('四耳/四墩诊断对照','版本/2.0/F41B03/支承对照.html'),link('1.0/2.0模型对照','版本/2.0/F41B03/修订对比.html'),link('安装待核表','版本/2.0/F41B03/安装表.json'));info.append(links);
    figure('设备原俯视','版本/2.0/F41B03/依据_设备俯视.png');figure('四墩基础图','版本/2.0/F41B03/依据_基础.png');
  }
  if (tagForRow(row)==='L41B02' && overrides.equipment?.L41B02) {
    const info=section(detail,'本类2.0侧视修正与定位');
    field(info,'本次修正','侧口中心250/800/1500/5000/7000/8900；底部改为环形锚板和立边表达，撤下四托座。内部喷淋不展开。');
    field(info,'图纸差异','顶法兰侧视955/俯视1182.5，底锚圈2600/2750；当前外形按侧视。壁厚、孔径及底部立边环向连续性为显示口径，待制造详图。');
    field(info,'位置与钢架','基础和钢塔架原几何保留；局部同心对照，接口与钢架的相交见本类报告。绝对中心/方位未核，不进入厂房总装。');
    const links=element('div','','links');links.append(link('本类整改说明','版本/2.0/L41B02/整改说明.html'),link('1.0/2.0模型对照','版本/2.0/L41B02/修订对比.html'),link('钢架相交校核','版本/2.0/L41B02/支承相交校核.json'),link('安装待核','版本/2.0/L41B02/安装待核.json'));info.append(links);
  }
  if (tagForRow(row)==='F41B04' && overrides.equipment?.F41B04) {
    const info=section(detail,'本类2.0安装基准与高度差异');
    field(info,'本体保持','原Ø1000×15100筒体及导出逐字节保留。台账17000、旧图11000、新塔架背立面约15100，以及新版平面约Ø1100的差异继续待核。');
    field(info,'安装修正','总装筒底由EL123.000改EL123.300，补入300高圆基础；中心X26000/Y31900及零旋转保持。');
    field(info,'锚固与钢架','圆基础/原153件钢架保持。钢架仅作局部对照，绝对方位未核；设备底部连接详图缺失，不补造底法兰或地脚孔，不把几何无相交视为锚固闭合。');
    const links=element('div','','links');links.append(link('本类整改说明','版本/2.0/F41B04/整改说明.html'),link('安装前后对照','版本/2.0/F41B04/安装对照.html'),link('安装表','版本/2.0/F41B04/安装表.json'),link('锚固/限位待核','版本/2.0/F41B04/支承复核.json'));info.append(links);
  }
  if (foundationIds.length) {
    const support=foundationIds.every(id=>foundations.assets[id].kind==='安装支架');
    const civil=section(detail,support?'安装支架与图纸':'基础图与模型');
    for (const id of foundationIds) {
      const data=foundations.assets[id], folder=foundationDir(id);
      const isSupport=data.kind==='安装支架';
      const label=isSupport?'支架':'基础';
      const panel=foundationIds.length>1?disclosure(civil,data.name):civil;
      if (panel===civil) panel.append(element('b',data.name));
      field(panel,label+'尺寸',data.dimensions);
      const {above,below,blinding,label:datumLabel}=data.datum;
      field(panel,'标高基准',datumLabel);
      const segments=datumLabel.startsWith('地面')
        ?'（地上 '+above+' / 地下 '+below+' mm）'
        :'（楼面以上 '+above+' mm）';
      field(panel,'本体高度',(above+below)+' mm '+(isSupport?'':segments));
      if (blinding) field(panel,'垫层厚度',blinding+' mm，单独计量');
      field(panel,'建模与就位',data.note);
      const links=element('div','','links');
      if (data.view) links.append(link('基础图摘录',foundationRoot+data.view));
      if (data.source) links.append(link('钢塔架原图 DXF',foundationSourceRoot+data.source,true));
      if (isSupport) for (const [i,url] of (data.related_views||[]).entries()) links.append(link(i===0?'布置俯视':'布置侧视',url));
      links.append(link(label+'参数',folder+'参数.json'),
        link(label+' GLB',folder+id+'.glb',true),link(label+' OBJ',folder+id+'.obj',true),
        link(label+' MTL',folder+id+'.mtl',true));
      panel.append(links);
    }
  } else if (foundations && !row.名称.endsWith('泵') && !row.位号.startsWith('V')) {
    field(section(detail,'基础图与模型'),'资料状态','现有资料未见对应基础详图');
  }
}

function loadParts(dir) {
  if (meshCache.has(dir)) return meshCache.get(dir);
  const request=new Promise((resolve,reject)=>{
    const script=document.createElement('script');
    script.src=dir+'model_data.js';
    script.onload=()=>{
      const mesh=window.MODEL_PARTS;
      delete window.MODEL_PARTS;
      script.remove();
      if (mesh?.length) resolve(mesh);
      else reject(new Error('Missing mesh parts'));
    };
    script.onerror=()=>{script.remove();reject(new Error('Model script failed'));};
    document.head.append(script);
  });
  meshCache.set(dir,request);
  request.catch(()=>meshCache.delete(dir));
  return request;
}

function setMessage(text) {
  const node=byId('preview-message');
  node.textContent=text;
  node.hidden=!text;
}

function changeParts() {
  viewer?.setParts(partGroups.get(group.value)??parts);
}

function collectPartGroups(mesh, archive) {
  const groups=new Map();
  if (archive) {
    // Match the Chinese categories and component scopes of the tank archives.
    const categories=[
      ['基础与支脚',/^(Leg|Pad)_/],
      ['槽体',/^Tank_(shell|flat)/],
      ['槽盖与安装框',/^(Tank_cover|Lid_|盖面_)/],
      ['底部型钢支撑',/^设备支撑_/],
      ['槽顶搅拌总成',/^(01_|02_|03_Intermediate_shaft$|06_)/],
      ['开窗支架与轴座',/^06_/],
      ['驱动组件',/^(01|02)_/],
      ['双端对称中间轴',/^03_Intermediate_shaft$/],
      ['接口',/^接口_/],
      ['盖面高座与盖板',/^盖面_m_/],
      ['侧口g',/^接口_g_/],
      ['侧口h',/^接口_h_/]
    ];
    if (mesh.some(part=>/^Impeller_/.test(part.name))) {
      categories.splice(6,0,['轴与叶轮',/^(Agitator_|Impeller_|03_Intermediate_shaft$)/]);
    }
    for (const [label,pattern] of categories) {
      const matched=mesh.filter(part=>pattern.test(part.name));
      if (matched.length) groups.set(label,matched);
    }
  } else {
    for (const part of mesh) {
      const label=part.name==='支撑_换热器托耳'||part.name.startsWith('托耳_')?(typeInfo(rowsByTag.get(rowTag))?.key==='D41B01'?'晶种槽托耳':typeInfo(rowsByTag.get(rowTag))?.key==='L41B01'?'过滤器托耳':typeInfo(rowsByTag.get(rowTag))?.key==='F41B03'?'分汽器托耳':'换热器托耳'):part.name.split('_')[0];
      if (!groups.has(label)) groups.set(label,[]);
      groups.get(label).push(part);
    }
  }
  return groups;
}

function meshBounds(mesh) {
  const min=[Infinity,Infinity,Infinity], max=[-Infinity,-Infinity,-Infinity];
  for (const part of mesh) for (const point of part.vertices) {
    point.forEach((value,i)=>{min[i]=Math.min(min[i],value);max[i]=Math.max(max[i],value);});
  }
  return {min,max};
}

async function select(id) {
  const token=++selection;
  rowTag=id;
  const row=rowsByTag.get(id);
  const type=typeInfo(row);
  const tag=id?.slice(0,6);
  const foundationIds=row?.名称.endsWith('泵')||overrides.foundation_policy?.[tag]?[]:foundations?.tags[tag] || [];
  const civilOnly=foundations?.civilOnly?.includes(tag);
  renderList();
  renderDetail(row,type,foundationIds,civilOnly);
  byId('details').scrollTop=0;
  byId('dimensions').hidden=true;
  byId('extra-view').hidden=true;
  group.hidden=true;
  group.replaceChildren(new Option('全部部件',''));
  foundationMode.hidden=true;
  foundationMode.replaceChildren(...(civilOnly?[]:[new Option('仅设备','')]));
  foundationMode.onchange=null;
  parts=[];
  partGroups.clear();
  dimensions=civilDimensions=null;
  if (!viewer) {setMessage('当前浏览器无法启用 WebGL，可在详情中下载模型。');return;}
  viewer.setParts([]);
  if (!type) {
    setMessage('此位号组的类型模型待补。');
    return;
  }
  setMessage('正在载入类型模型…');
  try {
    const clean=foundations?.equipment?.[type.key];
    const loaded=civilOnly?[]:await loadParts(clean?.dir||(clean?foundationRoot+clean.path:type.dir));
    if (token!==selection) return;
    const shell=loaded.find(part=>/^(Tank_shell(?:_|$)|本体_(筒壳|直筒段|烟囱直筒)$)/.test(part.name));
    const equipmentDimensions=loaded.length?{...meshBounds(shell?[shell]:loaded),cylindrical:Boolean(shell)}:null;
    byId('dimensions').hidden=false;
    if (loaded.length) {
      setDisplay(loaded,collectPartGroups(loaded,type.archive),equipmentDimensions);
      setMessage('');
    }
    if (foundationIds.length) {
      const mountKeys=foundationIds.filter(key=>foundations.assets[key].mount);
      const mounted=mountKeys.find(key=>foundations.assets[key].companion)||mountKeys[0];
      const combinedModes=new Map();
      for (const key of mounted?[mounted,...mountKeys.filter(key=>key!==mounted)]:[]) {
        const asset=foundations.assets[key];
        const mode=key===mounted?'combined':'combined:'+key;
        const label=asset.combined_label||(asset.kind==='安装支架'?'设备与支架':'设备与基础');
        combinedModes.set(mode,key);
        foundationMode.add(new Option(label,mode),combinedModes.size-1);
      }
      for (const key of foundationIds) {
        const asset=foundations.assets[key];
        foundationMode.add(new Option(foundationIds.length>1?asset.name:asset.kind==='安装支架'?'仅支架':'仅基础',key));
      }
      foundationMode.hidden=false;
      let viewRequest=0;
      foundationMode.onchange=async()=>{
        const request=++viewRequest;
        const value=foundationMode.value;
        if (!value) {
          setDisplay(loaded,collectPartGroups(loaded,type.archive),equipmentDimensions);
          setMessage('');
          return;
        }
        const combined=combinedModes.has(value);
        const key=combinedModes.get(value)||value;
        const config=foundations.assets[key];
        try {
          const civil=await loadParts(foundationDir(key));
          const companion=combined&&config.companion?foundations.assets[config.companion]:null;
          const base=companion?placeParts(await loadParts(foundationDir(config.companion)),companion.mount):[];
          const fixtures=combined&&config.fixture_prefix
            ?(await loadParts(type.dir)).filter(part=>part.name.startsWith(config.fixture_prefix)):[];
          if (token!==selection || request!==viewRequest) return;
          if (combined) {
            const placed=placeParts(civil,config.mount);
            const equipment=config.offsets?config.offsets.flatMap((offset,i)=>
              placeParts(loaded,offset,config.mirror_y_indices?.includes(i))):loaded;
            const groups=collectPartGroups(equipment,type.archive);
            groups.set(config.kind==='安装支架'?'安装支架':'图纸基础',placed);
            if (base.length) groups.set('图纸基础',base);
            if (fixtures.length) groups.set('安装鞍座',fixtures);
            const bounds=config.offsets?{
              ...equipmentDimensions,
              min:equipmentDimensions.min.map((value,i)=>value+config.offsets[0][i]),
              max:equipmentDimensions.max.map((value,i)=>value+config.offsets[0][i])
            }:equipmentDimensions;
            setDisplay([...equipment,...fixtures,...placed,...base],groups,bounds,foundationLevels(placed,config,config.mount[2]));
          } else {
            setDisplay(civil,collectPartGroups(civil,false),null,foundationLevels(civil,config));
          }
          setMessage('');
        } catch (error) {
          if (token!==selection || request!==viewRequest) return;
          foundationMode.value='';
          setDisplay(loaded,collectPartGroups(loaded,type.archive),equipmentDimensions);
          setMessage('基础预览加载失败，可在详情中下载基础模型。');
          console.error(error);
        }
      };
      if ((mounted || civilOnly) && !overrides.equipment?.[type.key]?.default_equipment_only) {
        foundationMode.value=mounted?'combined':foundationIds[0];
        await foundationMode.onchange();
        if (token!==selection) return;
      }
    }
    if (type.extra) {
      const [yaw,name]=type.extra;
      const button=byId('extra-view');
      button.textContent=name;
      button.hidden=false;
      button.onclick=()=>viewer.view(yaw,.36,name);
    }
  } catch (error) {
    if (token!==selection) return;
    parts=[];
    viewer.setParts(parts);
    setMessage('模型预览加载失败，可在详情中打开原档案。');
    console.error(error);
  }
}

function placeParts(mesh, [dx,dy,dz], mirrorY=false) {
  const sign=mirrorY?-1:1;
  return mesh.map(part=>{
    const vertices=part.vertices.map(([x,y,z])=>[x+dx,sign*y+dy,z+dz]);
    if (!mirrorY) return {...part,vertices};
    const faces=part.faces.map(face=>face.slice().reverse());
    const normals=part.normals?.map(face=>face.slice().reverse().map(([x,y,z])=>[x,-y,z]));
    return {...part,vertices,faces,normals};
  });
}

function foundationLevels(mesh, config, dz=0) {
  const body=mesh.filter(part=>!part.name.includes('垫层') && !part.name.startsWith('地脚螺栓_'));
  const round=config.kind!=='安装支架'&&(mesh.some(part=>part.name==='基础_混凝土肋1')||config.dimensions.includes('Ø'));
  const {datum}=config;
  return {...meshBounds(body),cylindrical:round,datum,
    z:datum.z+dz,top:datum.top+dz,bottom:datum.bottom+dz};
}

function setDisplay(mesh, groups, bounds, civil=null) {
  parts=mesh;
  partGroups=groups;
  dimensions=bounds;
  civilDimensions=civil;
  group.replaceChildren(new Option('全部部件',''));
  for (const label of partGroups.keys()) group.add(new Option(label,label));
  group.hidden=partGroups.size<=1;
  changeParts();
}

function drawDimension(a,b,label,offset) {
  const dx=b[0]-a[0], dy=b[1]-a[1], length=Math.hypot(dx,dy);
  if (length<18) return;
  const nx=-dy/length, ny=dx/length;
  const x=a[0]+nx*offset, y=a[1]+ny*offset;
  ctx.beginPath();
  ctx.moveTo(x,y);
  ctx.lineTo(x+dx,y+dy);
  for (const [px,py] of [[x,y],[x+dx,y+dy]]) {
    ctx.moveTo(px-4*nx,py-4*ny);
    ctx.lineTo(px+4*nx,py+4*ny);
  }
  ctx.lineWidth=1.2;
  ctx.strokeStyle='#ffcf72';
  ctx.stroke();
  const side=Math.sign(offset)||1;
  const tx=x+dx/2+nx*9*side, ty=y+dy/2+ny*9*side;
  measureText(label,tx,ty,'#ffdf9a');
}

function measureText(label,x,y,color,align='center') {
  ctx.textAlign=align;
  ctx.textBaseline='middle';
  ctx.font='12px sans-serif';
  const d=devicePixelRatio||1;
  const textWidth=ctx.measureText(label).width;
  const leading=align==='left'?0:textWidth/2;
  const trailing=align==='left'?textWidth:textWidth/2;
  x=Math.max(5+leading,Math.min(x,overlay.width/d-5-trailing));
  ctx.lineWidth=3;
  ctx.strokeStyle='#101923';
  ctx.strokeText(label,x,y);
  ctx.fillStyle=color;
  ctx.fillText(label,x,y);
}

function drawFoundationLevels(project,pixelsPerMm,showHeights) {
  const {min:[x0,y0],max:[x1,y1],z,top,bottom,cylindrical,datum}=civilDimensions;
  const cx=(x0+x1)/2, cy=(y0+y1)/2;
  const center=project([cx,cy,z]);
  if (Math.abs(project([cx,cy,z+1000])[1]-center[1])<3) return;
  const half=cylindrical?(x1-x0)/2*pixelsPerMm:
    Math.max(...[[x0,y0],[x0,y1],[x1,y0],[x1,y1]].map(([x,y])=>Math.abs(project([x,y,z])[0]-center[0])));
  const left=center[0]-half, right=center[0]+half;
  const yAt=level=>project([cx,cy,level])[1];
  ctx.save();
  ctx.lineWidth=1.3;
  ctx.strokeStyle='#82d9e6';
  ctx.setLineDash([7,4]);
  ctx.beginPath();
  ctx.moveTo(left-15,center[1]);
  ctx.lineTo(right+15,center[1]);
  ctx.stroke();
  ctx.restore();
  measureText(datum.label,left-13,center[1]-10,'#a8ecf4','left');
  if (!showHeights) return;
  const high=yAt(top), low=yAt(bottom);
  drawDimension([right,low],[right,high],'本体总高 '+(datum.above+datum.below)+' mm',16);
  if (datum.above && datum.below) {
    drawDimension([left,center[1]],[left,high],'地上 '+datum.above+' mm',-16);
    drawDimension([left,low],[left,center[1]],'地下 '+datum.below+' mm',-16);
  }
  if (datum.blinding) {
    const layerY=yAt(bottom-datum.blinding/2);
    ctx.lineWidth=1.2;
    ctx.strokeStyle='#ffcf72';
    ctx.beginPath();
    ctx.moveTo(left,layerY);
    ctx.lineTo(left-12,layerY+12);
    ctx.lineTo(left-30,layerY+12);
    ctx.stroke();
    measureText('垫层 '+datum.blinding+' mm',left-47,layerY+23,'#ffdf9a');
  }
}

function drawDimensions({width,height,project,viewName,pixelsPerMm,hasModel}) {
  byId('status').textContent=hasModel?rowTag+' · '+viewName+' · 正交':'';
  const scaleBar=byId('scale-bar');
  scaleBar.hidden=!hasModel;
  if (hasModel) updateEquipmentScale(scaleBar,pixelsPerMm);
  const d=devicePixelRatio||1;
  const w=Math.round(width*d), h=Math.round(height*d);
  if (overlay.width!==w || overlay.height!==h) {overlay.width=w;overlay.height=h;}
  ctx.setTransform(d,0,0,d,0,0);
  ctx.clearRect(0,0,width,height);
  if (!hasModel || group.value || !byId('showDim').checked) return;

  if (civilDimensions) drawFoundationLevels(project,pixelsPerMm,!dimensions);
  const measured=dimensions||civilDimensions;
  if (!measured) return;
  const {min:[x0,y0,z0],max:[x1,y1,z1],cylindrical}=measured;
  const size=value=>String(Math.round(value*10)/10)+' mm';
  if (cylindrical) {
    const cx=(x0+x1)/2, cy=(y0+y1)/2;
    const low=project([cx,cy,z0]), high=project([cx,cy,z1]);
    const radius=(x1-x0)/2, r=radius*pixelsPerMm;
    const rimDepth=Math.hypot(project([cx+radius,cy,z0])[1]-low[1],project([cx,cy+radius,z0])[1]-low[1]);
    drawDimension([low[0]-r,low[1]+rimDepth],[low[0]+r,low[1]+rimDepth],(dimensions?'Ø':'本体外廓 Ø')+size(x1-x0),11);
    if (dimensions) drawDimension([low[0]+r,low[1]],[high[0]+r,high[1]],'筒身 '+size(z1-z0),16);
    return;
  }
  const corners=[[x0,y0],[x1,y0],[x0,y1],[x1,y1]];
  const base=corners.map(([x,y])=>project([x,y,z0]));
  const center=project([(x0+x1)/2,(y0+y1)/2,z0]);
  const near=base.reduce((i,p,j)=>p[1]>base[i][1]?j:i,0);
  for (const [bit,label,span] of [[1,'X ',x1-x0],[2,'Y ',y1-y0]]) {
    const a=base[near], b=base[near^bit];
    const side=(a[1]-b[1])*(center[0]-a[0])+(b[0]-a[0])*(center[1]-a[1]);
    const offset=Math.abs(side)<.001 ? (b[0]>=a[0]?12:-12) : (side>0?-12:12);
    drawDimension(a,b,label+size(span),offset);
  }
  if (dimensions) {
    const right=base.reduce((i,p,j)=>p[0]>base[i][0]?j:i,0);
    drawDimension(base[right],project([...corners[right],z1]),'Z '+size(z1-z0),16);
  }
}

for (const [button,panel,css,label] of [
  ['toggle-list','directory','left-closed','目录'],['toggle-detail','details','right-closed','详情']
]) {
  byId(button).onclick=()=>{
    const hidden=byId(panel).hidden=!byId(panel).hidden;
    document.querySelector('.layout').classList.toggle(css,hidden);
    byId(button).setAttribute('aria-expanded',String(!hidden));
    const action=(hidden?'展开':'收起')+label;
    byId(button).setAttribute('aria-label',action);
    byId(button).title=action;
  };
}

try {
  viewer=createEquipmentViewer(byId('scene'),{doubleSided:true,centerProjection:true,onFrame:drawDimensions});
} catch (error) {
  console.error(error);
}
byId('iso').onclick=()=>{viewer?.view(-Math.PI/4,.36,'东南轴测');viewer?.fit();};
byId('top').onclick=()=>viewer?.view(-Math.PI/2,Math.PI/2,'北向俯视');
byId('front').onclick=()=>viewer?.view(-Math.PI/2,0,'南侧正立');
byId('fit').onclick=()=>viewer?.fit();
byId('showDim').onchange=()=>viewer?.draw();
group.onchange=changeParts;
search.oninput=state.onchange=renderList;
for (const status of new Set(rows.map(row=>row.状态).filter(Boolean))) state.add(new Option(status,status));
byId('library-count').textContent=rows.length+' 组';
sources();
const initialType=new URLSearchParams(location.search).get('type');
if (initialType) rowTag=rows.find(row=>row.位号.startsWith(initialType))?.位号||rowTag;
select(rowTag);

