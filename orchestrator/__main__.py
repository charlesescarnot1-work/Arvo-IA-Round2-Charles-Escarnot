import typer, os, pathlib, shutil, time, json
from git import Repo
from orchestrator.utils import ROOT, WORK, SRC, detect_language, detect_port, ensure_dockerfile, ensure_requirements, docker_build_tag_push, write_tfvars, run

app = typer.Typer(no_args_is_help=True, add_completion=False)

@app.command()
def deploy(
    repo: str = typer.Option(..., help="Git repo URL (https)"),
    app_name: str = typer.Option("autodeploy-app", help="ECR repo & ECS service name"),
    aws_region: str = typer.Option("us-east-1"),
    aws_profile: str = typer.Option("default"),
    env: list[str] = typer.Option(None, "--env", help="Extra env as KEY=VALUE (repeatable)")
):
    # prep workdir
    if WORK.exists(): shutil.rmtree(WORK)
    SRC.parent.mkdir(parents=True, exist_ok=True)

    print("==> Cloning repo...")
    Repo.clone_from(repo, SRC)

    print("==> Analyzing source...")
    lang = detect_language()
    port = detect_port()
    print(f"Detected lang={lang}, port={port}")

    print("==> Ensuring Dockerfile & minimal runtime files...")
    ensure_requirements(lang)
    ensure_dockerfile(lang, port)

    print("==> Building & pushing image...")
    image, registry = docker_build_tag_push(aws_region, aws_profile, app_name, image_tag=str(int(time.time())))
    print("Pushed:", image)

    print("==> Writing terraform.tfvars...")
    extra_env = {}
    if env:
        for item in env:
            if "=" in item:
                k, v = item.split("=", 1)
                extra_env[k.strip()] = v.strip()
    tfvars = write_tfvars(app_name, image, aws_region, port, extra_env=extra_env)
    print("tfvars at", tfvars)

    print("==> Terraform apply...")
    run(["terraform","init"], cwd=ROOT/"infra")
    run(["terraform","apply","-auto-approve"], cwd=ROOT/"infra")

    print("==> Fetching outputs...")
    out = run(["terraform","output","-json"], cwd=ROOT/"infra")
    try:
        data = json.loads(out.stdout)
        alb = data.get("alb_dns_name",{}).get("value")
        if alb:
            print(f"PUBLIC_URL: http://{alb}")
        else:
            print("No ALB output found.")
    except Exception as e:
        print("Could not parse terraform outputs:", e)
    print("==> Done.")

@app.command()
def destroy(
    aws_region: str = typer.Option("us-east-1"),
    aws_profile: str = typer.Option("default")
):
    print("==> Terraform destroy...")
    run(["terraform","destroy","-auto-approve"], cwd=ROOT/"infra")
    print("==> (Optional) Delete ECR repo manually if desired.")

if __name__ == "__main__":
    app()
