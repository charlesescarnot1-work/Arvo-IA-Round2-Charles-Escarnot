import os, re, subprocess, json, shutil, pathlib
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORK = ROOT / ".workdir"
SRC  = WORK / "source"
BUILD = WORK / "build"

def run(cmd:list[str], env:Optional[dict]=None, cwd:Optional[str|os.PathLike]=None):
    print("$", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=cwd, env=env, check=True, text=True, capture_output=True)
    if proc.stdout: print(proc.stdout)
    if proc.stderr: print(proc.stderr)
    return proc

def detect_language():
    files = [p.name.lower() for p in SRC.rglob("*") if p.is_file()]
    if "package.json" in files:
        return "node"
    if "requirements.txt" in files or "pyproject.toml" in files:
        return "python"
    for p in SRC.rglob("*.py"):
        return "python"
    for p in SRC.rglob("*.js"):
        return "node"
    return "unknown"

def detect_port(default=8080):
    text = ""
    for p in SRC.rglob("*.*"):
        try:
            if p.stat().st_size > 200_000:
                continue
            text += p.read_text(encoding="utf-8", errors="ignore") + "\n"
        except Exception:
            pass
    m = re.search(r"(PORT|port)\s*[:=]\s*(\d{2,5})", text)
    if m:
        return int(m.group(2))
    m2 = re.search(r"app\.listen\((\d{2,5})", text)
    if m2:
        return int(m2.group(1))
    m3 = re.search(r"run\(host=.*?port\s*=\s*(\d{2,5})", text)
    if m3:
        return int(m3.group(1))
    return default

def ensure_dockerfile(lang:str, port:int):
    df = SRC / "Dockerfile"
    if df.exists():
        return
    if lang == "python":
        content = f"""FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt || true
COPY . .
ENV PORT={port}
EXPOSE {port}
CMD ["python","-m","gunicorn","--bind","0.0.0.0:{port}","app:app"]
"""
    elif lang == "node":
        content = f"""FROM node:20-slim
WORKDIR /app
COPY package*.json ./
RUN npm ci || npm install
COPY . .
ENV PORT={port}
EXPOSE {port}
CMD ["npm","start"]
"""
    else:
        content = f"""FROM alpine:3.20
CMD ["sh","-c","echo unsupported repo; sleep 3600"]
"""
    df.write_text(content)

def ensure_requirements(lang:str):
    if lang=="python":
        req = SRC/"requirements.txt"
        if not req.exists():
            req.write_text("flask\ngunicorn\n")
        app_py = SRC/"app.py"
        if not app_py.exists():
            app_py.write_text('from flask import Flask\napp=Flask(__name__)\n@app.get("/")\ndef hi(): return "ok"\n')
    if lang=="node":
        pkg = SRC/"package.json"
        if not pkg.exists():
            pkg.write_text('{"name":"app","version":"1.0.0","scripts":{"start":"node index.js"}}')
            (SRC/"index.js").write_text('const http=require("http");const port=process.env.PORT||8080;http.createServer((_,res)=>res.end("ok")).listen(port);')

def docker_build_tag_push(aws_region:str, aws_profile:str, app_name:str, image_tag:str):
    # Ensure repo exists
    try:
        run(["aws","ecr","describe-repositories","--repository-names",app_name,"--region",aws_region,"--profile",aws_profile])
    except Exception:
        run(["aws","ecr","create-repository","--repository-name",app_name,"--region",aws_region,"--profile",aws_profile])
    login = run(["aws","ecr","get-login-password","--region",aws_region,"--profile",aws_profile])
    account_id = run(["aws","sts","get-caller-identity","--query","Account","--output","text","--profile",aws_profile]).stdout.strip()
    registry = f"{account_id}.dkr.ecr.{aws_region}.amazonaws.com"
    proc = subprocess.Popen(["docker","login","--username","AWS","--password-stdin",registry], stdin=subprocess.PIPE, text=True)
    proc.communicate(input=login.stdout)
    if proc.returncode != 0:
        raise RuntimeError("docker login failed")

    image_local = f"{app_name}:{image_tag}"
    run(["docker","build","-t",image_local,"."], cwd=SRC)
    image_remote = f"{registry}/{app_name}:{image_tag}"
    run(["docker","tag",image_local,image_remote])
    run(["docker","push",image_remote])
    return image_remote, registry

def write_tfvars(app_name:str, image:str, aws_region:str, container_port:int, extra_env:dict|None=None):
    tfvars = (ROOT/"infra"/"terraform.tfvars")
    extra_env = extra_env or {}
    def hcl_map(d):
        items = []
        for k, v in d.items():
            k_esc = k.replace("\\", "\\\\").replace('"', '\"')
            v_esc = str(v).replace("\\", "\\\\").replace('"', '\"')
            items.append(f'"{k_esc}" = "{v_esc}"')
        return "{ " + ", ".join(items) + " }" if items else "{}"
    content = (
        f'app_name     = "{app_name}"\n'
        f'image_uri    = "{image}"\n'
        f'aws_region   = "{aws_region}"\n'
        f'container_port = {container_port}\n'
        f'desired_count  = 1\n'
        f'extra_env = {hcl_map(extra_env)}\n'
    )
    tfvars.write_text(content)
    return tfvars
