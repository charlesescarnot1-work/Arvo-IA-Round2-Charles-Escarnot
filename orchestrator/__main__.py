# orchestrator/__main__.py
from __future__ import annotations

import argparse
from datetime import datetime

from .utils import (
    BUILD,
    SRC,
    WORK,
    detect_language,
    detect_port,
    docker_build_tag_push,
    ensure_dockerfile,
    ensure_requirements,
    run,
    write_tfvars,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build & deploy to ECS Fargate")
    parser.add_argument("--aws-region", default="us-east-1")
    parser.add_argument("--aws-profile", default="arvo")
    parser.add_argument("--app-name", default="hello-world")
    parser.add_argument("--image-tag", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    image_tag: str = args.image_tag or datetime.utcnow().strftime("%Y%m%d%H%M%S")

    WORK.mkdir(parents=True, exist_ok=True)
    SRC.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)

    lang = detect_language()
    ensure_requirements(lang)
    port = detect_port(default=5000)
    ensure_dockerfile(lang, port)

    image_uri, _ = docker_build_tag_push(
        aws_region=args.aws_region,
        aws_profile=args.aws_profile,
        app_name=args.app_name,
        image_tag=image_tag,
    )

    tfvars_path = write_tfvars(
        app_name=args.app_name,
        image=image_uri,
        aws_region=args.aws_region,
        container_port=port,
        extra_env={"GUNICORN_CMD_ARGS": "--access-logfile - --log-level info"},
    )
    print(f"wrote {tfvars_path}")

    # terraform init / apply
    run(["terraform", "-chdir=infra", "init", "-upgrade"])
    run(
        [
            "terraform",
            "-chdir=infra",
            "apply",
            "-auto-approve",
            "-input=false",
        ]
    )

    # show outputs
    alb = run(["terraform", "-chdir=infra", "output", "-raw", "alb_dns_name"]).stdout.strip()
    svc = run(["terraform", "-chdir=infra", "output", "-raw", "service_name"]).stdout.strip()

    print("\n=== Deployment complete ===")
    print(f"Service  : {svc}")
    print(f"Endpoint : http://{alb}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
