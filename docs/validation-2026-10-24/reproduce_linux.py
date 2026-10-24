import hashlib, concurrent.futures, datetime, importlib.util, json, os, pathlib, platform, shlex, subprocess, tempfile, tomllib
repo = pathlib.Path(__file__).resolve().parents[2]
out = repo / 'docs/validation-2026-10-24'
names = ['_meta', 'research-lookup', 'citation-management', 'literature-review', 'scientific-slides', 'scientific-schematics', 'latex-posters']
manifest = tomllib.loads((repo/'tests/skill-requirements.toml').read_text())
base_env = {k:v for k,v in os.environ.items() if k in {'PATH','HOME','TMPDIR','LANG','LC_ALL','SYSTEMROOT','SYSTEMDRIVE','SSL_CERT_FILE','SSL_CERT_DIR','UV_CACHE_DIR','UV_PYTHON_INSTALL_DIR'}}
base_env.update(PYTHONDONTWRITEBYTECODE='1', MPLBACKEND='Agg')
source_files = [p for root in ['skills', 'tests', '.github'] for p in (repo/root).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in {'.pyc'}]
source_before = {str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
with tempfile.TemporaryDirectory(prefix='pr1-offline-') as td:
    guard = pathlib.Path(td)
    (guard/'sitecustomize.py').write_text('import socket\ndef deny(*args, **kwargs):\n    raise AssertionError("Network disabled for offline PR validation")\nsocket.socket.connect = deny\nsocket.socket.connect_ex = deny\nsocket.create_connection = deny\n')
    def run(name):
        packages = ['jsonschema'] if name == '_meta' else manifest['skills'][name].get('packages', [])
        uv = ['uv','run','--no-project','--python','3.13','--with','pytest>=9.1.1','--with','pytest-socket']
        for p in packages: uv += ['--with',p]
        prepare = uv + ['python','-c','import sys,importlib.metadata,json; print(json.dumps({"python":sys.version,"packages":{d.metadata["Name"]:d.version for d in importlib.metadata.distributions()}},sort_keys=True))']
        env_result = subprocess.run(prepare,cwd=repo,env={**base_env, **{k:v for k,v in os.environ.items() if k in {'HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY','PIP_PROXY','PIP_CERT'}}},capture_output=True,text=True,timeout=240)
        (out/f'{name}-environment.json').write_text(env_result.stdout)
        if env_result.returncode:
            (out/f'{name}-linux.log').write_text(env_result.stderr)
            return {'suite':name,'setup_exit_code':env_result.returncode}
        cmd = uv + ['python','-m','pytest',f'tests/{name}','-q','-ra','--disable-socket',f'--junitxml=docs/validation-2026-10-24/{name}-linux.xml']
        env = dict(base_env, PYTHONPATH=str(guard))
        with (out/f'{name}-linux.log').open('w') as f:
            f.write('Command: '+shlex.join(cmd)+'\nEnvironment: credential-free allowlist; Python sockets blocked by sitecustomize.\n\n'); f.flush()
            completed = subprocess.run(cmd,cwd=repo,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=360)
        print(name, completed.returncode, flush=True)
        return {'suite':name,'exit_code':completed.returncode,'command':cmd}
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(run,names))
    data = {'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'system':platform.platform(),'python_target':'3.13','network_guard':'socket.connect/connect_ex/create_connection blocked in test Python processes via temporary sitecustomize; dependency installation separate before test; real credentials removed from test environment','results':results}
    data['source_tree_sha256'] = hashlib.sha256(json.dumps(source_before, sort_keys=True).encode()).hexdigest()
    data['source_unchanged_during_run'] = all(p.exists() and hashlib.sha256(p.read_bytes()).hexdigest() == source_before[str(p.relative_to(repo))] for p in source_files)
    data['tracked_worktree_diff'] = subprocess.check_output(['git','diff','--stat'],cwd=repo,text=True)
    (out/'linux-source-sha256.json').write_text(json.dumps(source_before,indent=2,sort_keys=True)+'\n')
    (out/'linux-summary.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data,indent=2))
