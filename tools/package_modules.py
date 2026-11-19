"""Build independent viewing/download ZIPs without editing any source asset.

Only Git-tracked module files are included. Dependencies keep their repository
paths, so the original viewers and frozen model files remain byte-identical.
"""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import html
import json
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / 'modules.json').read_text(encoding='utf-8'))
MODULES = CONFIG['modules']
REPO_URL = 'https://github.com/' + CONFIG['repository']


def belongs(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def selected_files(module, tracked):
    return sorted(p for p in tracked
                  if any(belongs(p, prefix) for prefix in module['include'])
                  and not any(belongs(p, prefix) for prefix in module['exclude']))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def landing(module_id=None):
    """The same portal works in the repository and inside an individual ZIP."""
    installed = set(MODULES if module_id is None or module_id == 'assembly' else [module_id])
    cards = []
    for key, module in MODULES.items():
        name = html.escape(module['name'])
        local = ('<a href="' + module['entry'] + '">打开三维模型</a> · ') if key in installed else ''
        cards.append(f'<article><h2>{name}</h2><p>{html.escape(module["description"])}</p>'
                     f'<p>{local}<a href="{REPO_URL}/tree/main/{module["directory"]}">GitHub目录</a> · '
                     f'<a href="{REPO_URL}/releases/latest/download/{module["asset"]}">下载独立ZIP</a></p></article>')
    title = '水解工段 · 模块入口' if module_id is None else MODULES[module_id]['name'] + ' · 独立下载包'
    return ('<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>body{{max-width:1050px;margin:40px auto;padding:20px;background:#101923;color:#dce8ef;font:15px sans-serif;line-height:1.8}}'
            'a{color:#7cdce6}article{border:1px solid #344957;border-radius:8px;padding:8px 22px;margin:18px 0}h2{font-size:20px}</style>'
            f'<h1>{title}</h1><p>东 +X · 北 +Y · 上 +Z · EL100 / 106 / 112</p>'
            '<p>下载后先完整解压，再打开本页选择模型。可旋转、分层查看；模型格式和参数在各模块页面下载。'
            'GitHub仓库页面展示文件、说明和预览图，不直接运行交互式3D。</p>'
            + ''.join(cards) + f'<p><a href="{REPO_URL}/releases">全部发布版本</a> · <a href="README.md">使用说明</a></p></html>').encode('utf-8')


def notice(module, prefix):
    """Make cross-module navigation explain which separate download to use."""
    depth = len(PurePosixPath(prefix).parts)
    back = '../' * depth + 'index.html'
    return (f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>{module["name"]}</title>'
            '<body style="background:#101923;color:#dce8ef;font:16px sans-serif;padding:40px;line-height:2">'
            f'<h1>{module["name"]}是独立模块</h1><p>当前下载包未包含此模块的三维浏览入口。请下载对应独立包，或下载总装包查看组合模型。</p>'
            f'<p><a style="color:#7cdce6" href="{REPO_URL}/releases/latest/download/{module["asset"]}">下载{module["name"]}</a> · '
            f'<a style="color:#7cdce6" href="{back}">返回模块入口</a></p></body></html>').encode('utf-8')


def build(output):
    output.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    tracked = [p for p in tracked if p]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT).decode().strip()
    versions = {
        'bridge': json.loads((ROOT/'水解桥架工程/project.json').read_text())['assembly_version'],
        'equipment': json.loads((ROOT/'水解设备模型库/project.json').read_text())['revisions'],
        'building_sha256': hashlib.sha256((ROOT/'厂房外观模型/建筑/model_data.js').read_bytes()).hexdigest(),
    }
    releases = []
    for module_id, module in MODULES.items():
        files = selected_files(module, tracked)
        assert module['entry'] in files, module_id
        manifest = {'module': module_id, 'name': module['name'], 'source_commit': commit,
                    'entry': module['entry'], 'versions': versions, 'dependencies': module['include'][1:],
                    'excluded': module['exclude'], 'source_files_sha256': {}}
        archive = output/module['asset']
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            for name in files:
                raw = (ROOT/name).read_bytes()
                manifest['source_files_sha256'][name] = hashlib.sha256(raw).hexdigest()
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, raw, compresslevel=6)
            z.writestr('index.html', landing(module_id))
            z.writestr('下载包清单.json', json_bytes(manifest))
            z.writestr('README.md', (
                f'# {module["name"]}独立浏览包\n\n{module["description"]}\n\n'
                '先完整解压到一个目录，双击根目录 index.html。推荐使用桌面版Chrome或Edge。'
                '若浏览器限制本地文件，在此目录运行 `python -m http.server 8000`，访问 http://localhost:8000/ 。\n\n'
                '各模块保留原目录结构；不要单独移动其中的HTML或JS。设备包附带的桥架目录仅为基础/支架等依赖。'
                '跨模块导航会提示下载对应包；总装包包含所有模块。\n\n'
                '本包用于浏览、下载模型和核对资料。完整维护/重建、跨模块校验请克隆完整仓库，按各模块README操作。'
                '冻结版本和源网格逐字节保留；下载包清单记录每个源文件SHA256和源提交。\n\n'
                f'源提交：{commit}\n\n仓库：{REPO_URL}\n').encode('utf-8'))
            names = set(files)
            for key, other in MODULES.items():
                if other['entry'] not in names:
                    z.writestr(other['entry'], notice(other, str(PurePosixPath(other['entry']).parent)))
        releases.append({'module': module_id, 'asset': archive.name, 'bytes': archive.stat().st_size,
                         'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(), 'source_files': len(files)})
        print(f'{archive.name}: {len(files)} files, {archive.stat().st_size/1024**2:.1f} MiB', flush=True)
    (output/'packages.json').write_bytes(json_bytes({'source_commit': commit, 'packages': releases}))
    (output/'SHA256SUMS.txt').write_text(''.join(f'{r["sha256"]}  {r["asset"]}\n' for r in releases), encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='输出到仓库外的发布目录')
    parser.add_argument('--portal-only', action='store_true', help='只生成仓库根目录模块入口')
    args = parser.parse_args()
    if args.portal_only:
        (ROOT/'index.html').write_bytes(landing())
    else:
        if args.output is None:
            parser.error('请用 --output 指定发布目录。')
        if args.output.resolve() == ROOT or ROOT in args.output.resolve().parents:
            parser.error('ZIP输出必须位于仓库外，避免重复归档生成文件。')
        build(args.output)
