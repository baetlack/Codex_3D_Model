"""Create independently browsable Git trees from verified packages.

GitHub generates the ZIP download for each branch/tag, so releases need no
binary attachment upload. No source file is moved and main is never switched.
Push the returned refs after inspecting them. No force-push or tag overwrite.
"""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, tempfile, zipfile
from package_modules import ROOT, MODULES, REPO_URL


def git(*args, data=None, env=None):
    return subprocess.check_output(['git',*args],cwd=ROOT,input=data,env=env).decode().strip()


def publish(output, version):
    assert re.fullmatch(r'modules-[0-9]{4}-[0-9]{2}-[0-9]{2}(?:-[0-9]+)?',version),version
    assert not git('status','--porcelain'),'Commit the reviewed source before publishing'
    commit=git('rev-parse','HEAD');packages=json.loads((output/'packages.json').read_text())
    check=json.loads((output/'package-check.json').read_text())
    assert packages['source_commit']==check['source_commit']==commit
    assert check['status']=='passed' and check.get('browser'),'Verify extracted package viewers first'
    staged={}
    for item in git('ls-files','--stage','-z').split('\0'):
        if not item:continue
        metadata,name=item.split('\t',1);mode,sha,stage=metadata.split();assert stage=='0';staged[name]=(mode,sha)
    pending=[];receipt={'source_commit':commit,'modules':[]}
    for package in packages['packages']:
        key=package['module'];module=MODULES[key];branch='refs/heads/'+module['branch'];tag='refs/tags/'+version+'-'+key
        assert subprocess.run(['git','show-ref','--verify','--quiet',tag],cwd=ROOT).returncode!=0,'Never overwrite a version tag'
        old=subprocess.run(['git','rev-parse','--verify',branch],cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
        previous=old.stdout.strip() if old.returncode==0 else None
        archive=output/package['asset'];assert hashlib.sha256(archive.read_bytes()).hexdigest()==package['sha256']
        with tempfile.TemporaryDirectory(prefix='module-index-') as temp,zipfile.ZipFile(archive) as z:
            env={**os.environ,'GIT_INDEX_FILE':str(Path(temp)/'index')}
            git('read-tree','--empty',env=env);records=[]
            manifest=json.loads(z.read('下载包清单.json'))
            for name in z.namelist():
                raw=z.read(name)
                if name in manifest['source_files_sha256']:
                    assert hashlib.sha256(raw).hexdigest()==manifest['source_files_sha256'][name],name
                    assert raw==(ROOT/name).read_bytes(),name
                    mode,sha=staged[name]
                else:mode,sha='100644',git('hash-object','-w','--stdin',data=raw)
                records.append(f'{mode} {sha}\t{name}\0')
            git('update-index','-z','--index-info',data=''.join(records).encode(),env=env)
            tree=git('write-tree',env=env)
        parents=['-p',previous] if previous else []
        parents+=['-p',commit]
        result=git('commit-tree',tree,*parents,'-m',f'Publish {module["name"]} from {commit[:7]} ({version})')
        pending.append(f'update {branch} {result} {previous or "0"*40}\n')
        pending.append(f'create {tag} {result}\n')
        receipt['modules'].append({'module':key,'branch':branch,'tag':tag,'commit':result,'view':f'{REPO_URL}/tree/{module["branch"]}',
                                   'download':f'{REPO_URL}/archive/refs/tags/{version}-{key}.zip'})
    git('update-ref','--stdin',data=('start\n'+''.join(pending)+'prepare\ncommit\n').encode())
    (output/'module-refs.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(receipt,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path);parser.add_argument('--version',required=True);args=parser.parse_args();publish(args.output,args.version)
