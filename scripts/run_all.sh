#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/Arvo-AI/hello_world}"
APP_NAME="${APP_NAME:-hello-world}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_PROFILE="${AWS_PROFILE:-default}"
EXTRA_ENV="${EXTRA_ENV:-}"

echo "[1/5] Checking prerequisites..."
command -v aws >/dev/null || { echo "Missing aws cli"; exit 1; }
command -v terraform >/dev/null || { echo "Missing terraform"; exit 1; }
command -v docker >/dev/null || { echo "Missing docker"; exit 1; }
python3 -V >/dev/null || { echo "Missing python3"; exit 1; }

echo "[2/5] Python venv & deps..."
python3 -m venv .venv
source .venv/bin/activate
pip install -r orchestrator/requirements.txt

echo "[3/5] Terraform init..."
terraform -chdir=infra init -upgrade

echo "[4/5] Deploy orchestration..."
ENV_ARGS=()
if [[ -n "$EXTRA_ENV" ]]; then
  IFS=',' read -ra PAIRS <<< "$EXTRA_ENV"
  for kv in "${PAIRS[@]}"; do
    ENV_ARGS+=(--env "$kv")
  done
fi

python -m orchestrator deploy   --repo "$REPO_URL"   --app-name "$APP_NAME"   --aws-region "$AWS_REGION"   --aws-profile "$AWS_PROFILE"   "${ENV_ARGS[@]}"

echo "[5/5] Done. If a PUBLIC_URL was printed above, open it in your browser."
