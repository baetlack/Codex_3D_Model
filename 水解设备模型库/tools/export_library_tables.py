"""Summarize existing library records; never read or remeasure raw CAD/PDF/XLS.

The three tables describe the current display, existing placements, and recorded
source decisions. Repeated mesh pieces are grouped by their purpose. No geometry,
installation record, source decision, or model revision is changed by this tool.
"""
from pathlib import Path
import csv
import hashlib
import html
import json
import re

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
OUT = ROOT / '资料库三表'
CIVIL = REPO / '水解桥架工程/models/设备/设备基础_20261106'
INPUTS = set()


def read(path):
    path = Path(path)
    assert path.suffix not in {'.dxf', '.dwg', '.pdf', '.xls'}, path
    INPUTS.add(path)
    return path.read_text(encoding='utf-8')


def load(path):
    return json.loads(read(path))


def script(path):
    return json.JSONDecoder().raw_decode(read(path).split('=', 1)[1].lstrip())[0]


def parts(path):
    data = script(path)
    return [p['name'] for p in (data.get('parts', []) if isinstance(data, dict) else data)]


def n(value):
    return f'{value:g}' if isinstance(value, (float, int)) else str(value)


def join(values):
    return '；'.join(dict.fromkeys(str(v) for v in values if v))


CHOICES = {
    'C41B01': '外部本体和接口用新增总图；内径3500与钢壳外径3520分开；原基础、位置保持。',
    'C41B02': '按用户确认保留Ø5500×5000和搅拌高2185；盖面改8组检修盖及新外接口，采用已接受的02版。',
    'C41B03': '外形、接口用新增总图；明确标注优先于图形实量，平面按既有8/15换算记录；搅拌高1350保持。',
    'C41B04': '本体、四托耳和11口用厂家条件图；保持6台布置位置，AB组钢架随设备调整约200；按用户要求删除推断的外露大环和杆件。',
    'D41B01': '按用户决定A—E五台统一新本体；B/C、D/E用成对支架，保持槽距2600和既有世界承托面。',
    'D41B02': '确认的Ø5900×4700本体、原盖面和3076搅拌保持；新增总图仅更新外部接口，暂沿用原盖面口高基准。',
    'F41B01': '外壳、接口和150高底型钢用新增总图；保持原基础、设备中心及2310搅拌显示高度。',
    'F41B02': '采用三槽共用总图；整个本体统一转换90°以对应类型轴系，原实例坐标、转角不变；不单独转动次口。',
    'F41B03': '仅表达有依据的Ø1000×1000直筒段、四耳及耳孔；撤销误由孔分度圆生成的实体端圈，四墩独立保留。',
    'F41B04': '保留原Ø1000×15100筒体；按既有300高差记录修正筒底并配置圆基础，钢塔架仅独立对照。',
    'F41B05': '采用与F41B02/F41B06共图的新本体；统一类型轴系，保留原坐标、转角和基础；厂家次口相对位置保持。',
    'F41B06': '采用与F41B02/F41B05共图的新本体；统一类型轴系，保留原坐标、转角和基础；厂家次口相对位置保持。',
    'F41B07': '保留净1500×1500×2000地坑示意；1#、2#土建基础模型独立列示，不把A/B位号强配到坑号。',
    'F41B08': '沿用用户确认的Ø1000×1000一体圆柱；暂定圆基础独立保留，不增加无依据的搅拌器或接口。',
    'L41B01': '采用新过滤器总图的三耳、锥斗和五口；保留原X/Y及暂用Z；A/C/E保留等价镜像姿态，旧暂定圆台不与新本体组合。',
    'L41B02': '侧口和外形暂按原侧视；圆基础及钢塔架保持，不以文字插点作为设备中心，不加入总装。',
    'L41B03': '按用户选择保留台账Ø1800×3100，参照示图修正外形及接口；3100指锥尖至顶法兰，原专用钢架保持。',
    'L41B04': '保留原俯视轮廓建立的主管、变径和附件示意；原两支座基础独立保留。',
    'L41B05': '采用新条件图的Ø1000筒体、275封头、9上口/2下口及2000鞍座距；b口按表DN100；不复制原单墩。',
    'P41A08': '暂复用P41B08外形作展示；保留P41A08独立台账和待定位记录，不据复用判定厂家型号相同。',
    'P41B04': '保留布置俯视对应的管道泵示意；不根据流量、扬程推导立式或卧式制造外形。',
    'P41B07': '暂保留旧示意并标明“台账立式、当前卧式外形不符”；没有用无依据的新尺寸替换。',
    'P41B09': '暂保留旧示意并标明“台账立式、当前卧式外形不符”；没有用无依据的新尺寸替换。',
    'P41B10': '保留已整理的轴向进风、切向出风及传动外形；设备支脚和传动底座属于本体，土建基础分开。',
}
PENDING = {
    'C41B01': '绝对工艺方位；h口盖颈差异及未标法兰、盖板等细部。',
    'C41B02': 'POS定义、绝对方位和内外径定义；未标盖座/法兰细部；缺第2—8张详图。',
    'C41B03': '图名“碱液稀释槽”的适用性；绝对方位、未标接口细部及图形/标注差异。',
    'C41B04': '240/230㎡面积差异；端部过渡、吊耳、法兰未标细部及N5/N6准确口高。',
    'D41B01': 'A槽支架；槽距2600/2500差异；支架截面、新接口绝对方位。',
    'D41B02': '原320高盖面与新接口口高基准；侧口细部、绝对工艺方位。',
    'F41B01': '未标型钢截面、检视窗细部、法兰等显示尺寸；绝对工艺方位。',
    'F41B02': '新旧次低口/人孔相对方位差异；复合套管、呼吸口细部和绝对工艺方位。',
    'F41B03': '完整总图、托耳承托EL及与四墩的过渡连接；当前四耳与四墩无平面搭接。',
    'F41B04': '17000/11000/15100高度口径；底部锚固和钢塔架方位；平面与立面直径差异。',
    'F41B05': '新旧次低口/人孔相对方位差异；复合套管、呼吸口细部和绝对工艺方位。',
    'F41B06': '新旧次低口/人孔相对方位差异；复合套管、呼吸口细部和绝对工艺方位。',
    'F41B07': 'A/B与1#/2#坑号对应；原示意与土建壁厚/缺口差异；绝对位置及楼板接口。',
    'F41B08': '圆基础为暂定尺寸；绝对位置、楼层标高及基础详图。',
    'L41B01': '三耳的承托结构和EL；暂用Z、新管口绝对方位。',
    'L41B02': '绝对位置/方位；顶法兰及底圈视图差异；锚栓露头、钢架与接口配合。',
    'L41B03': '绝对位置/方位及厂家详图；台账与原示图尺寸差异；局部对照标高不作绝对安装确认。',
    'L41B04': '厂家立面、主管标高、附件形状及安装支座。',
    'L41B05': '双鞍座与原单墩基础不匹配；绝对定位/方位；b口图形与DN表差异、未标支座细部。',
    'P41A08': '厂家型号与实际外形、底脚和标高；绝对位置/方位。',
    'P41B04': '厂家立式/卧式型式、真实外形与底脚；安装标高及管口方位。',
    'P41B07': '厂家立式模型及安装详图；入坑深度、真实总高、绝对位置和支承。',
    'P41B09': '厂家立式模型及安装详图；真实总高、支承、绝对位置和管口方向。',
    'P41B10': '厂家外形、锚固尺寸和基础对应；安装标高及工艺朝向。',
}


def summaries(key):
    if key.startswith('V'):
        return ('沿用共用侧视和台账吨位/行程；当前倍率仅用于外形展示，未将起升高度作为机身高度。',
                '厂家型号/外形、轨道及挂装、绝对位置/标高；吨位不能作为制造尺寸缩放依据。')
    return (CHOICES.get(key, '保留原布置俯视对应的泵示意及共用外形参考；不由流量、扬程推造设备尺寸。'),
            PENDING.get(key, '厂家总图、真实高度、底脚/基础配合及管口方位；安装标高按各单台既有状态保留。'))


def port_function(key, port, names):
    if port.get('role'):
        return port['role']
    label = port['id']
    if key == 'C41B02':
        if label.startswith('k'):
            return '盘管检修和盖面封闭'
        if label.startswith(('b', 'j')):
            return '盘管外接管路连接；具体进出介质未登记'
    if key == 'C41B04' and label.startswith('N7'):
        return '底部排净'
    if any('呼吸' in s for s in names):
        return '槽内气体呼吸、通气'
    if any('人孔' in s or '检修盖' in s for s in names):
        return '供人员检查、检修进入并封闭开口'
    if any('取样盖' in s for s in names):
        return '取样、开盖检查'
    if port.get('closure'):
        return '开盖检查、检修并封闭开口'
    return '与外部管路或仪表连接；具体用途未登记'


def dimensions_for(key, params, old, clean, first):
    d = params.get('dimensions_mm', {})
    if 'nominal_inner_diameter_mm' in d:
        return f'公称内径Ø{n(d["nominal_inner_diameter_mm"])}；钢壳外径Ø{n(d["steel_outer_diameter_mm"])}；罐高{n(d["nominal_body_height_mm"])}'
    if key == 'C41B02':
        return '槽体Ø5500×5000；搅拌器高2185（相对壳顶）'
    if key == 'C41B04':
        return '外壳Ø1300；两端面高4812；换热面积图纸240㎡（台账230㎡）'
    if key == 'D41B01':
        return '钢壳内径Ø1800、外径Ø1816；内筒段1600；保温60'
    if key == 'D41B02':
        return '确认槽体Ø5900×4700；搅拌器总高3076'
    if key == 'F41B03':
        return '直筒段Ø1000×1000（不代表完整设备总高）'
    if key == 'F41B04':
        return '显示筒体Ø1000×15100；壁厚16为显示值'
    if key == 'L41B01':
        return '内径Ø1200、外径Ø1216；至盖顶约1446、顶口1566；三耳'
    if key == 'L41B02':
        return '塔身外径Ø2200；名义顶高10300；顶部颈Ø800'
    if key == 'L41B03':
        return 'Ø1800；锥尖至顶法兰3100，底排接管另计'
    if key == 'L41B05':
        return '筒体Ø1000×3800；封头各275；总长4350；轴高700'
    if key == 'F41B07':
        return '原地坑示意净1500×1500×2000；外框1700；底厚100为显示值'
    if key == 'F41B08':
        return '用户确认Ø1000×1000一体圆柱'
    if key.startswith('V'):
        lift = old.get('起升参数', {})
        return f'额定{n(lift.get("额定起重量_t", "未登记"))}t；起升行程{n(lift.get("起升高度_m", "未登记"))}m；本体外形为示意'
    bounds = clean.get('bounds')
    suffix = '；当前净模显示包络' + '×'.join(n(v) for v in bounds) if bounds else ''
    return first['spec'] + suffix


def overall_function(key, name):
    uses = {
        'C41B01': '热水预热、暂存', 'C41B02': '钛液预热、暂存',
        'C41B03': '稀碱预热、暂存', 'C41B04': '偏钛酸物料冷却换热',
        'D41B01': '晶种制备与混合', 'D41B02': '钛液水解反应',
        'F41B01': '偏钛酸物料缓冲、暂存', 'F41B02': '事故状态下收集、暂存钛液',
        'F41B03': '冷凝水分汽（目前模型仅表达直筒段）',
        'F41B04': '尾气排放', 'F41B05': '稀碱配制、混合',
        'F41B06': '稀碱储存', 'F41B07': '收集废水', 'F41B08': '密封水暂存、循环配套',
        'L41B01': '水解工艺物料过滤', 'L41B02': '尾气洗涤处理',
        'L41B03': '分离气流夹带雾滴', 'L41B04': '蒸汽减温、减压',
        'L41B05': '蒸汽汇集、分配', 'P41B10': '输送工艺尾气',
    }
    if key.startswith('V'):
        return '起吊和搬运载荷'
    return uses.get(key, '输送对应工艺介质' if key.startswith('P') else name)


def extract():
    project = load(ROOT / 'project.json')
    catalog = load(ROOT / 'catalog.json')['models']
    cfg = load(REPO / '水解总装工程/assembly.json')
    prior = load(ROOT / 'data/连续整改_20261120/99台复核清单.json')
    base = load(CIVIL / '基础索引.json')
    overrides = script(ROOT / 'equipment_versions.js')
    for key, value in overrides['foundations'].items():
        base['assets'][key] = {**base['assets'].get(key, {}), **value}
    for key, value in overrides['equipment'].items():
        base['equipment'][key] = {**base['equipment'].get(key, {}), **value}
    tables = [[], [], []]
    evidence = {'body_parts': {}, 'ports': {}, 'foundation_parts': {}, 'counts': prior['counts']}
    sources_index = {}
    installed = {q['id']: q for q in cfg['equipment']}
    unplaced = {q['id']: q for q in cfg['unplaced']}
    for key in sorted({q['id'][:6] for q in catalog}):
        units = sorted((q for q in catalog if q['id'][:6] == key), key=lambda q: q['id'])
        name = units[0]['name']
        revision = project['revisions'].get(key)
        clean = base['equipment'].get(key, {})
        old_path = ROOT / f'示图建模_20260521/模型/{key}/参数.json'
        if not old_path.exists() and key in ['C41B02', 'D41B02']:
            old_path = next((ROOT / '设备档案').glob(key + '_*/参数.json'))
        aliases = {'P41A08': 'P41B08', 'F41B05': 'F41B02', 'F41B06': 'F41B02'}
        if not old_path.exists() and key in aliases:
            old_path = ROOT / f'示图建模_20260521/模型/{aliases[key]}/参数.json'
        old = load(old_path)
        if revision:
            body = ROOT / revision['equipment']
        elif clean.get('dir'):
            body = ROOT / clean['dir'] / 'model_data.js'
        elif clean.get('path'):
            body = CIVIL / clean['path'] / 'model_data.js'
        else:
            body = old_path.with_name('model_data.js')
            if not body.exists():
                body = ROOT / '示图建模_20260521/模型/P41B08/model_data.js'
        params = load(body.with_name('参数.json')) if body.with_name('参数.json').exists() else old
        # Cleaned exports embed the original parameter record.
        params = params.get('原档案参数', params)
        names = parts(body)
        remaining = list(range(len(names)))
        assignments = {}
        class_label = key

        def row(label, spec, purpose, indices=None):
            tables[0].append([class_label, name, label, spec or '分件尺寸未登记', purpose])
            if indices is not None:
                for i in indices:
                    assert i not in assignments
                    assignments[i] = len(tables[0])
                    remaining.remove(i)

        def group(pattern, label, spec, purpose):
            matched = [i for i in remaining if re.search(pattern, names[i], re.I)]
            if matched:
                row(label, spec, purpose, matched)

        d = params.get('dimensions_mm', {})
        whole = dimensions_for(key, params, old, clean, units[0])
        row('整机 / 总体外形', whole, overall_function(key, name))
        evidence['ports'][key] = [p['id'] for p in params.get('ports', [])]
        for port in params.get('ports', []):
            label = port['id']
            escaped = re.escape(label)
            pattern = rf'^(?:接口_(?:顶盖法兰_)?|紧固_|盖面_){escaped}(?=$|_|接管|法兰|外套|内接管|直管|呼吸|开口|盖|提手)'
            if key == 'D41B01' and label == 'k':
                pattern = r'^搅拌_k_'
            ids = [i for i in remaining if re.search(pattern, names[i])]
            matched = [names[i] for i in ids]
            dn = port.get('dn', port.get('DN'))
            size = f'DN{dn}' if dn is not None else ''
            if port.get('outer_DN'):
                size = f'内接管{size}；外套安装口DN{port["outer_DN"]}'
            if port.get('mount_dn'):
                size += f'；安装口DN{port["mount_dn"]}'
            if port.get('size_mm'):
                size = '×'.join(n(v) for v in port['size_mm'])
            if not size and port.get('neck_OD_mm'):
                size = f'接管外径Ø{n(port["neck_OD_mm"])}（显示/量测）'
            flange = port.get('flange_OD_mm', port.get('cover_OD_mm'))
            if flange:
                size += f'；法兰/盖外廓Ø{n(flange)}'
            bits = []
            for token, title in [('接管', '接管'), ('外套', '外套'), ('法兰', '法兰'), ('垫片', '垫片'), ('密封面', '密封面'), ('瓷衬', '瓷衬'), ('提手', '提手')]:
                if any(token in s for s in matched):
                    bits.append(title)
            if any(any(t in s for t in ['人孔盖', '检修盖', '取样盖', '共盖板', '带柄盖']) or re.search(r'盖面_.+盖$', s) for s in matched):
                bits.append('盖板')
            if any(s.startswith('紧固_') for s in matched):
                bits.append('紧固件')
            title = label + '口' + ('（' + '、'.join(bits) + '）' if bits else '')
            row(title, size or '口径未登记', port_function(key, port, matched), ids)

        group(r'设备底型钢|设备支撑_I', '槽底型钢（翼缘、腹板）',
              (f'高{n(d["bottom_member_height_mm"])}；间距500' if d.get('bottom_member_height_mm') else ('I16；9排；高160；间距650' if key == 'C41B02' else '显示截面')), '承托槽底并传递至基础')
        shell_spec = whole.split('；搅拌')[0]
        group(r'Tank_shell|本体_(?:钢壳|外壳|塔身|直筒|卧式筒体|烟囱直筒|下筒体|上筒体)', '筒体 / 壳体', shell_spec, '构成设备容纳或流通介质的主体')
        group(r'Tank_flat_bottom|本体_底板|本体_封底', '底板 / 封底及底部转角',
              f'Ø{n(d["bottom_plate_diameter_mm"])}×{n(d["bottom_plate_thickness_mm"])}' if d.get('bottom_plate_diameter_mm') else '按现有本体；分件尺寸未单列', '封闭底部、承载介质')
        group(r'本体_(?:锥|下锥|塔顶锥|椭圆|.*端收口|.*端集流)', '锥段 / 封头及端部收口',
              '两端封头各深275' if key == 'L41B05' else ('锥底10°' if key == 'D41B01' else '按现有外形；未单列尺寸'), '封闭或过渡壳体，形成集流、排料外形')
        group(r'保温_', '筒体及锥底保温外包络', '厚60' if key == 'D41B01' else '显示外包络', '表达保温层外形')
        group(r'Tank_cover_lid|盖面_开孔盖板|槽盖_外盖|顶盖_平盖', '顶盖 / 开孔盖板',
              f'Ø{n(d["cover_diameter_mm"])}×{n(d["cover_thickness_mm"])}' if d.get('cover_diameter_mm') else ('外径Ø5724；钢板12、垫片3' if key == 'C41B02' else ('Ø1256×8' if key == 'L41B01' else '现有盖面，分件尺寸见已登记口径')), '封闭顶部并布置接口或搅拌安装口')
        group(r'Lid_edge|Lid_gasket|槽盖_角钢|本体_.*端连接圈', '盖缘 / 连接圈、密封垫片', None, '连接端盖和壳体、表达密封部位')
        group(r'盖面_m_', 'm搅拌高座、对开顶板、踏步板及补强肋', '座高280；顶板30；开口2900×1020；座外廓3064×1150', '安装搅拌器，提供盖面封闭及局部踏步')
        group(r'接口_cd_', 'c/d接口共座', '两口共座；分件尺寸未单列', '共同承托蒸汽/冷凝液接口')
        group(r'^连接_', '分筒连接法兰、上下垫片及PP筛板外露边缘', '法兰Ø1375；垫片各5；筛板外露边厚20', '连接上下筒段，密封并表达筛板安装层')
        group(r'顶盖_立筋', '顶盖立筋', '2条；按现有模型', '加强顶盖')
        group(r'托耳_.*(?:刚性环|补强圈)', '贴身补强圈及上下刚性环', '刚性环外/内径2072/1832，厚12' if key == 'D41B01' else None, '加强托耳与壳体连接区域')
        group(r'^托耳_', '托耳（承托板、补强板/筋板及孔）',
              ('3耳；底板125×160×10；孔Ø30' if key == 'L41B01' else
               '4耳；底板250×400×12；孔Ø36' if key == 'D41B01' else
               '4耳；外跨2055、孔跨1875；孔Ø30' if key == 'C41B04' else
               '4耳；孔Ø16.5；孔分度圆Ø1100；板厚24为显示值' if key == 'F41B03' else '4耳；未标细部按现有显示尺寸'), '将设备承托在梁、钢架或支墩上')
        group(r'^吊耳_', '带孔吊耳', '按现有外形，准确细部待核', '吊运连接点的外形表达')
        group(r'^支撑_底|^支承_鞍座', '底部支承 / 锚圈' if key == 'L41B02' else '两只鞍座（底板、腹板）',
              '底锚圈Ø2600；12孔分度圆Ø2400；孔Ø30为显示值' if key == 'L41B02' else '中心距2000；轴高700；底板/腹板截面为显示值', '把设备重量传至基础或支承结构')
        group(r'接口_顶部', '顶部接管、法兰', f'接管Ø{n(d.get("top_neck_OD", "未登记"))}；法兰Ø{n(d.get("top_flange_OD", "未登记"))}' if key == 'L41B02' else '按现有模型量测外形；DN未登记', '顶部外接管路连接；具体用途未登记')
        group(r'^(?:搅拌_)?\d+_(?:Motor|Fin)|^驱动_电机|^驱动_Y', '搅拌电机（机壳、散热筋、顶帽/底座）', '含于本类既有搅拌总高；电机独立型号/尺寸见已有记录', '驱动搅拌轴')
        group(r'^(?:搅拌_)?\d+_(?:Upper_|Middle_|Lower_|Base_)|^驱动_(?:减速|BLD)', '搅拌减速/传动壳体及连接法兰', None, '传递电机动力并连接传动部分')
        group(r'Frame|圆筒开窗|搅拌_(?:机架|DJ|外露|联接)|^(?:搅拌_)?\d+_(?:Drive_|Output_|Intermediate_)', '搅拌机架、安装法兰、联轴套及外露传动轴',
              '搅拌总高2185；高座以上架体按现有记录' if key == 'C41B02' else (f'搅拌显示总高{n(d["mixer_display_height_mm"])}' if d.get('mixer_display_height_mm') else '按现有搅拌/机架尺寸'), '支承驱动装置并传递至槽内轴系')
        group(r'Agitator_shaft|Impeller', '槽内搅拌轴、叶轮及轮毂', '沿用现有模型，分件尺寸未单列', '搅动物料；仅列现有已建部件')
        group(r'^紧固_', '其余盖面/分筒连接紧固件', '24套M20×130（含头、杆、螺母、垫圈）' if key == 'L41B01' else '按现有显示数量；未标尺寸不另补', '紧固连接部位')
        group(r'^土建_坑底', '地坑底板（原设备示意）', '净坑1500×1500；底厚100为显示值', '构成坑底')
        group(r'^土建_.*坑壁', '地坑四壁（原设备示意）', '净深2000；外框1700、内框1500', '围护收集空间')
        group(r'^泵体_', '泵壳及轴向进液口',
              f'进液法兰外径Ø{n(old.get("尺寸量测", {}).get("进口法兰外径_mm", "未登记"))}', '介质进入泵体并形成输送流道')
        group(r'^接口_偏置|^接口_朝上', '出液接管及朝上法兰',
              f'出口法兰外径Ø{n(old.get("尺寸量测", {}).get("出口法兰外径_mm", "未登记"))}', '连接泵出口管线')
        group(r'^连接座_', '泵壳连接环及短连接段', None, '连接泵壳与电机安装部分')
        group(r'^电机_', '泵电机（机壳、散热筋、尾罩、接线盒及连接法兰）', None, '驱动泵；散热及电气连接外形表达')
        group(r'^支脚_', '电机底脚', '仅列当前净模中保留的底脚', '设备自身支承与安装连接')
        group(r'^本体_.*蜗壳', '风机蜗壳及两侧壳板', None, '容纳叶轮并汇集、导出气流')
        group(r'^接口_上出风', '风机切向出风管及圆法兰', None, '连接出风管线')
        group(r'^接口_中空喇叭', '风机轴向喇叭口及进风法兰', None, '连接进风管线')
        group(r'^内部示意_', '风机叶轮（背盘、轴毂、叶片）', '内部示意外形', '向气流传递动力')
        group(r'^蜗壳支架_', '蜗壳支脚及脚底板', None, '支承风机壳体')
        group(r'^驱动_|^护罩_', '风机电机、轴、轴承座、联轴器及护罩', None, '传递驱动力；护罩遮护旋转连接部位')
        group(r'^传动底座_', '风机传动底座、安装板及电机/轴承底脚', None, '安装和支承驱动部件，属于设备本体')
        group(r'^紧固件_', '进出口法兰螺栓', '按当前模型显示；规格未登记', '紧固外接法兰')
        group(r'^主管_', '主管直段、变径段及短接', '俯视总外廓5250×639；立面为示意', '构成蒸汽主管及变径连接')
        group(r'^法兰_', '首端、中间及末端法兰', '未标细部按现有显示', '连接主管及外部管路')
        group(r'^附件_', '调节阀示意接颈、附件法兰及小接管', '当前仅为附件连接外形示意', '表达调节/减温附件的连接位置')
        group(r'^葫芦_', '卷筒外壳、电机端罩、减速端盖及环箍', '吨位、行程见本类整机行；外形为示意', '起升机构及其外壳表达')
        group(r'^小车_', '行走小车（悬挂座、侧板、车轮及传动）', '共用侧视示意外形；轨道型号未登记', '将葫芦悬挂在轨道上并沿轨道行走')
        group(r'^吊具_', '示意钢丝绳及吊钩', '当前为短悬绳状态；不是额定全行程长度', '连接、起吊载荷')
        # Any uncommon piece remains visible by its own recorded name; no silently
        # omitted pieces and no new dimensions are inferred from vertex geometry.
        for i in list(remaining):
            row(names[i].replace('_', ' '), '按现有模型；分件规格未单列', '现有组成件；具体用途未登记', [i])
        evidence['body_parts'][key] = {'source': body.relative_to(REPO).as_posix(), 'parts': len(names), 'covered': len(assignments), 'unmatched': []}
        assert not remaining and len(assignments) == len(names)

        fids = [] if key in overrides.get('foundation_policy', {}) else base['tags'].get(key, [])
        foundation_info = []
        for fid in fids:
            meta = base['assets'][fid]
            fpath = ROOT / meta['dir'] / 'model_data.js' if meta.get('dir') else CIVIL / fid / 'model_data.js'
            fparts = parts(fpath)
            titles = []
            if any('混凝土' in t for t in fparts):
                titles.append('混凝土基础/支墩')
            if any(re.search(r'基础_(?:底板|[东西南北]壁|缺口下方)', t) for t in fparts):
                titles.append('坑底板、坑壁')
            for token, label in [('垫层', '垫层'), ('二次浇筑', '二次浇筑层'), ('预埋板', '预埋板'), ('地脚螺栓', '地脚螺栓'), ('预留孔', '预留孔'), ('柱脚板', '柱脚板'), ('立柱', '立柱'), ('GZ柱', '立柱'), ('承托梁', '承托梁'), ('横梁', '横梁'), ('纵梁', '纵梁'), ('撑', '支撑/斜撑'), ('水平杆', '水平杆'), ('限位杆', '限位杆'), ('花纹钢板', '平台板'), ('栏杆', '栏杆'), ('钢梯', '钢梯'), ('缺口', '坑壁缺口')]:
                if any(token in t for t in fparts):
                    titles.append(label)
            title = meta['name'] + '（' + '、'.join(dict.fromkeys(titles)) + '）'
            purpose = '围护、收集废水' if '集水坑' in meta['name'] else '承托设备、传递支承荷载'
            if '平台板' in titles or '钢梯' in titles or '栏杆' in titles:
                purpose += '；平台、钢梯和栏杆用于操作通行与防护'
            if '二次浇筑层' in titles:
                purpose += '；二次浇筑层提供找平和承压接触'
            if '地脚螺栓' in titles or '预埋板' in titles:
                purpose += '；锚栓/预埋板提供安装连接部位'
            row(title, meta['dimensions'], purpose + '；安装关系见表2')
            foundation_info.append(meta)
            evidence['foundation_parts'][key + '/' + fid] = {'source': fpath.relative_to(REPO).as_posix(), 'parts': len(fparts), 'listed_as': title}

        for unit in units:
            tag = unit['id']
            placed = installed.get(tag)
            fs = [f for f in cfg['foundations'] if tag in ([f.get('support_for')] if isinstance(f.get('support_for'), str) else f.get('support_for', []))]
            if key == 'L41B01':
                method = '三耳承托；支承梁/墩及承托EL待核'
            elif key in ['C41B04', 'D41B01', 'F41B03', 'L41B03']:
                method = '四托耳承托'
                if key == 'D41B01' and tag.endswith('A'):
                    method += '；A支架待核'
                if key == 'F41B03':
                    method += '；四墩与四耳无搭接，过渡连接待核'
            elif key == 'L41B05':
                method = '双鞍座支承；原单墩不能直接作为双鞍座安装方案'
            elif key.startswith('V'):
                method = '小车悬挂/轨道行走；实际挂装、轨道待核'
            elif key == 'F41B07':
                method = '地下集水坑；坑号对应、开口及土建接口待核'
            elif key in ['L41B02', 'F41B04']:
                method = '立式筒体/底部基础；锚固及钢塔架配合待核'
            elif key == 'L41B04':
                method = '主管支座安装；设备支座与两基础对应待核'
            elif key.startswith('P'):
                method = ('风机自身支脚、传动底座安装；土建基础另列' if key == 'P41B10' else '泵组底座/底脚安装；厂家底脚和锚固待核')
                if key in ['P41B07', 'P41B09']:
                    method = '台账为立式泵；当前卧式示意不作为确定安装方式'
            else:
                method = '槽底/底型钢在基础顶承托'
            fi = join(m['name'] + '：' + m['dimensions'] for m in foundation_info)
            if key == 'D41B01' and tag.endswith('A'):
                fi = 'A槽未确认支架；现有成对支架仅适用于B/C和D/E'
            elif key == 'L41B01':
                fi = '新本体支承结构待核；旧暂定圆台已退出组合'
            elif not fi:
                fi = '未登记本类独立基础；不据本体底脚推造土建基础'
            fworld = []
            for f in fs:
                pos = f['position_mm']
                fid = f['asset'].removeprefix('foundation-')
                datum = base['assets'].get(fid, {}).get('datum', {})
                position = f'{f["id"]}：X{pos[0]/1000:.4f} / Y{pos[1]/1000:.4f} / 原点EL{100+pos[2]/1000:.3f}'
                if 'top' in datum:
                    position += f'；基础/梁顶EL{100+(pos[2]+datum["top"])/1000:.3f}'
                if 'bottom' in datum:
                    position += f'；基础/架底EL{100+(pos[2]+datum["bottom"])/1000:.3f}'
                fworld.append(position)
            if not fworld:
                fworld = ['总装未登记该位号的独立基础/钢架实例；已有基础仅作独立查看' if foundation_info else '待核']
            if placed:
                x, y, z = placed['position_mm']
                rot = placed.get('rotation_deg', 0)
                orientation = f'绕Z转{n(rot)}°' + ('；局部Y镜像' if placed.get('mirror_y') else '')
                if key.startswith('P') and key != 'P41B10' and old.get('模型坐标基准', '').startswith('X 从进液端'):
                    angles = ['东', '东北', '北', '西北', '西', '西南', '南', '东南']
                    axis = angles[int((rot % 360 + 22.5) // 45) % 8]
                    orientation += f'；泵端→电机大致向{axis}'
                datum = placed.get('local_datum') or placed.get('model_origin') or params.get('datum') or params.get('local_datum') or old.get('模型坐标基准') or '当前设备净模原点；不一定等于几何中心'
                if isinstance(datum, dict):
                    datum = datum.get('origin', '当前本体参数定义的局部原点')
                status = join(['已入总装', placed.get('xy_status'), '原点标高：' + placed.get('z_status', '待核'), placed.get('orientation_status')]).replace('INSERT', '图块')
                values = [round(x/1000, 4), round(y/1000, 4), round(z/1000, 4), round(100+z/1000, 4)]
            else:
                orientation = '待定位 / 朝向待核'
                datum = params.get('datum', params.get('local_datum', '绝对安装原点待核'))
                if isinstance(datum, dict):
                    datum = datum.get('origin', '绝对安装原点待核')
                status = '未入总装；' + unplaced[tag]['reason']
                values = ['', '', '', '']
            if key in ['P41B07', 'P41B09']:
                status += '；台账立式与现卧式外形不符'
            tables[1].append([key, tag, name, unit.get('level', ''), *values, orientation, str(datum), method, fi, join(fworld), status])

        choice, pending = summaries(key)
        source_paths = []
        if params.get('source_drawing'):
            source_paths.append(params['source_drawing'])
        for filename in ['来源与差异.json', '复核记录.json']:
            path = ROOT / '版本/2.0' / key / filename
            if path.exists():
                src = load(path)
                source_paths.extend(src.get('sources', {}).keys())
                if src.get('source_drawing'):
                    source_paths.append(src['source_drawing'])
        if not params.get('source_drawing'):
            source_paths.append('水解设备模型库/示图建模_20260521/原始资料/水解设备模型示图_更新20261105.dxf')
        source_paths.extend([
            '水解设备模型库/示图建模_20260521/原始资料/2.水解水洗设备一览表 2026.5.21.xls',
            '水解设备模型库/示图建模_20260521/原始资料/3.水解工段设备布置图+2026.5.21.dxf',
        ])
        if foundation_info:
            source_paths.append('水解桥架工程/data/原始资料/设备基础/水解设备基础图.dxf')
        if key in ['L41B02', 'F41B04']:
            source_paths.append('水解桥架工程/data/原始资料/设备基础/水解设备基础图_增补烟囱及洗涤塔钢塔架_20261106.dxf')
        for ref in old.get('外形依据', []) if key.startswith('P') else []:
            if ref.startswith('原始资料/'):
                path = ROOT / '示图建模_20260521' / ref
                if path.exists():
                    source_paths.append(path.relative_to(REPO).as_posix())
        for kind in ['外形参考图', '进出口参考图']:
            ref = old.get(kind)
            if isinstance(ref, dict) and ref.get('文件'):
                path = ROOT / '示图建模_20260521' / ref['文件']
                if path.exists():
                    source_paths.append(path.relative_to(REPO).as_posix())
        # Source names are copied from existing records; opening those files is
        # intentionally outside this documentation task.
        source_paths = list(dict.fromkeys(p for p in source_paths if (REPO / p).exists() and Path(p).suffix.lower() in ['.dxf', '.dwg', '.pdf', '.xls', '.png'] and (foundation_info or '设备基础图' not in Path(p).name)))
        sources_index[key] = source_paths
        body_sources = [Path(p).name for p in source_paths if not any(s in Path(p).name for s in ['设备基础图', '设备布置图'])]
        install_sources = [Path(p).name for p in source_paths if any(s in Path(p).name for s in ['设备基础图', '设备布置图'])]
        tables[2].append([key, name, '、'.join(q['id'] for q in units), join(body_sources), join(install_sources), choice, pending])

    headers = [
        ['类别位号', '设备名称', '组成名称（含口号）', '规格（未注单位为mm）', '功能'],
        ['类别位号', '单台位号', '设备名称', '楼层（原记录）', 'X / m', 'Y / m', '原点Z / m', '原点EL / m', '朝向', '设备模型原点定义', '安装方式', '基础 / 支架规格', '基础 / 支架在总装的位置与标高（m）', '现有记录说明'],
        ['类别位号', '设备名称', '适用位号', '本体参考资料', '安装 / 基础参考资料', '现有取舍', '待核摘要'],
    ]
    assert len(tables[1]) == 99 and len(tables[2]) == 35
    assert len({q[1] for q in tables[1]}) == 99
    assert {r[0] for r in tables[0]} == {r[0] for r in tables[2]}
    for record in tables[1]:
        tag = record[1]
        if tag in installed:
            xyz = installed[tag]['position_mm']
            assert record[4:8] == [round(v/1000, 4) for v in xyz] + [round(100+xyz[2]/1000, 4)]
        else:
            assert record[4:8] == ['', '', '', '']
    return headers, tables, evidence, sources_index


def write_excel(headers, tables, note):
    wb = Workbook()
    wb.remove(wb.active)
    names = ['01 模型组成', '02 安装信息', '03 参考资料']
    widths = [[14, 22, 50, 68, 57], [14, 18, 22, 16, 12, 12, 14, 14, 38, 55, 52, 85, 85, 90], [14, 22, 55, 78, 78, 92, 92]]
    for index, (title, head, rows) in enumerate(zip(names, headers, tables)):
        ws = wb.create_sheet(title)
        ws.sheet_view.showGridLines = False
        ws.append([title[3:]])
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(head))
        ws['A1'].font = Font(size=18, bold=True, color='164653')
        ws.row_dimensions[1].height = 30
        ws.append([note[index]])
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(head))
        ws['A2'].alignment = Alignment(wrap_text=True, vertical='center')
        ws['A2'].font = Font(size=10, color='52636B')
        ws.row_dimensions[2].height = 43
        ws.append(head)
        for data in rows:
            ws.append(data)
        ws.freeze_panes = 'D4' if index == 1 else 'C4'
        table = Table(displayName=f'LibraryTable{index+1}', ref=f'A3:{get_column_letter(len(head))}{ws.max_row}')
        table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
        ws.add_table(table)
        for col, width in enumerate(widths[index], 1):
            ws.column_dimensions[get_column_letter(col)].width = width
        for cell in ws[3]:
            cell.font = Font(bold=True, color='FFFFFF')
            cell.fill = PatternFill('solid', fgColor='245563')
            cell.alignment = Alignment(wrap_text=True, vertical='center')
        ws.row_dimensions[3].height = 31
        for row in ws.iter_rows(min_row=4):
            for cell in row:
                cell.alignment = Alignment(vertical='top', wrap_text=True)
                cell.font = Font(name='Microsoft YaHei', size=10)
            ws.row_dimensions[row[0].row].height = 67 if index == 0 else 135
        if index == 1:
            for row in ws.iter_rows(min_row=4, min_col=5, max_col=8):
                for cell in row:
                    cell.number_format = '0.0000'
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.paperSize = ws.PAPERSIZE_A3
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.print_title_rows = '1:3'
    wb.save(OUT / '设备资料库三表.xlsx')


def write_page(headers, tables, notes):
    payload = json.dumps({'headers': headers, 'tables': tables}, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c')
    labels = ['表1 · 模型组成', '表2 · 安装信息', '表3 · 参考资料']
    options = ''.join(f'<option value="{html.escape(r[0])}">{html.escape(r[0]+" · "+r[1])}</option>' for r in tables[2])
    text = '''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>设备资料库三表</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101923;color:#dce8ef;font:14px/1.7 "Microsoft YaHei",sans-serif}main{max-width:1800px;margin:25px auto;padding:0 22px}h1{font-size:25px;margin-bottom:5px}p{margin:7px 0;color:#b7c9d2}a{color:#7cdce6}button,input,select{font:inherit;background:#1b303d;color:#e1edf2;border:1px solid #49616e;border-radius:5px;padding:8px 12px}button{cursor:pointer}button.active{border-color:#7cdce6;background:#2b5060}nav,.filters{display:flex;flex-wrap:wrap;gap:9px;margin:15px 0}.download{margin:12px 0}.download a{margin-right:17px}.frame{overflow:auto;border:1px solid #344957;border-radius:7px;max-height:72vh}table{border-collapse:collapse;min-width:1150px;width:100%}th,td{border-bottom:1px solid #344957;padding:11px;vertical-align:top;text-align:left;white-space:pre-line;min-width:95px}th{position:sticky;top:0;background:#24515e;z-index:1}tbody tr:nth-child(even){background:#152630}td:nth-child(3),td:nth-child(4),td:nth-child(5){min-width:190px}table[data-tab="1"]{min-width:2700px}table[data-tab="2"]{min-width:1750px}table[data-tab="2"] td:nth-child(n+4){min-width:280px}.count{color:#86dce5}small{color:#a8bec9}.note{padding:11px 15px;background:#1b303d;border-left:3px solid #79d4dd}@media print{body{background:white;color:black}.frame{max-height:none;overflow:visible}button,input,select,nav{display:none}th{position:static}p,a{color:#333}table{font-size:9px}td,th{min-width:0!important}.note{background:#eee}}</style></head><body><main>
<h1>设备资料库三表</h1><p>35类 · 99项设备 ｜ 当前资料整理，未重新分析原始图纸</p>
<div class="download"><a download href="设备资料库三表.xlsx">下载Excel（三个工作表）</a><a href="../index.html">设备模型库</a><a href="../版本/复核总览.html">既有复核总览</a></div>
<nav aria-label="资料表切换">NAV</nav><div class="filters"><select id="class-filter" aria-label="设备类别"><option value="">全部35类</option>OPTIONS</select><input id="search" type="search" aria-label="搜索" placeholder="搜索名称、位号或口号"><span id="count" class="count"></span></div>
<p id="note" class="note"></p><p><small>尺寸未注单位为mm；坐标为当前总装坐标（m），东+X、北+Y、上+Z，Z0=EL100。绕Z转角按模型局部轴表示；0°并不代表全部接口均已确认朝向。空坐标表示待定位。相同用途的重复构件合并列示；没有建出的内部件不补列为已建。功能为已有记录或组成件的一般用途，介质流向未登记时不推定。</small></p>
<div class="frame"><table id="data-table"><thead></thead><tbody></tbody></table></div><p id="csv-link"></p>
<script id="data" type="application/json">DATA</script><script>
const data=JSON.parse(document.querySelector('#data').textContent),notes=NOTES,files=FILES;let current=0;
const table=document.querySelector('#data-table'),select=document.querySelector('#class-filter'),search=document.querySelector('#search');
function cell(tag,value){const e=document.createElement(tag);e.textContent=value;return e}
function render(){const query=search.value.trim().toLowerCase(),key=select.value;table.dataset.tab=current;const rows=data.tables[current].filter(r=>(!key||r[0]===key)&&(!query||r.join(' ').toLowerCase().includes(query)));table.tHead.replaceChildren();const tr=document.createElement('tr');for(const h of data.headers[current])tr.append(cell('th',h));table.tHead.append(tr);const body=table.tBodies[0];body.replaceChildren();for(const r of rows){const row=document.createElement('tr');for(const v of r)row.append(cell('td',v));body.append(row)}document.querySelector('#count').textContent=rows.length+' / '+data.tables[current].length+' 行';document.querySelector('#note').textContent=notes[current];const a=document.createElement('a');a.href=files[current];a.download='';a.textContent='下载本表CSV';document.querySelector('#csv-link').replaceChildren(a);for(const b of document.querySelectorAll('nav button')){b.classList.toggle('active',Number(b.dataset.tab)===current);b.setAttribute('aria-pressed',String(Number(b.dataset.tab)===current))}}
for(const b of document.querySelectorAll('nav button'))b.onclick=()=>{current=Number(b.dataset.tab);render()};select.onchange=render;search.oninput=render;render();
</script></main></body></html>'''
    text = text.replace('NAV', ''.join(f'<button data-tab="{i}">{s}</button>' for i, s in enumerate(labels))).replace('OPTIONS', options).replace('DATA', payload).replace('NOTES', json.dumps(notes, ensure_ascii=False)).replace('FILES', json.dumps(['表1_模型组成.csv', '表2_安装信息.csv', '表3_参考资料.csv'], ensure_ascii=False))
    (OUT / 'index.html').write_text(text, encoding='utf-8')


def main():
    OUT.mkdir(exist_ok=True)
    headers, tables, evidence, source_index = extract()
    notes = [
        '按设备类别合并同构组成件；仅列当前模型反映的名称、规格和功能。DN为公称口径；外廓/显示尺寸不代替厂家规格，未登记用途不推定。基础/钢架列示表示资料库中有该模型，其安装关系见表2。',
        '99项逐台列示；72台已入总装、27台待定位。数值是当前模型原点的位置，原点定义随设备而异；标高或方位待核时保持现有状态。没有基础总装实例时，不将独立预览的对齐当作确定安装。',
        '35类逐类汇总现用参考、已有取舍和待核摘要；只整理既有来源与差异/参数/复核记录，没有重新量图。未登记管口用途保留在表1；更多原始细节仍留在各类既有档案。',
    ]
    filenames = ['表1_模型组成.csv', '表2_安装信息.csv', '表3_参考资料.csv']
    for filename, header, rows in zip(filenames, headers, tables):
        with (OUT / filename).open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    write_excel(headers, tables, notes)
    write_page(headers, tables, notes)
    payload = {'scope': '仅整理当前资料库，不重新分析原始资料', 'headers': headers, 'tables': tables, 'notes': notes}
    (OUT / '三表数据.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    evidence['source_documents_by_class'] = source_index
    evidence['row_counts'] = [len(rows) for rows in tables]
    evidence['inputs_sha256'] = {p.relative_to(REPO).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(INPUTS)}
    evidence['verification'] = '35类与99项齐全；72台坐标照录，27项无伪造坐标；现用本体分件全部归入组成表；不读取原始CAD/PDF/XLS'
    (OUT / '整理记录.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'written', 'rows': evidence['row_counts'], 'classes': 35, 'units': 99, 'raw_drawings_read': 0}, ensure_ascii=False))


if __name__ == '__main__':
    main()
