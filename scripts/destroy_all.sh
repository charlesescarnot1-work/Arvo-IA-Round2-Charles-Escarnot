#!/usr/bin/env bash
set -euo pipefail
echo "Destroying terraform stack..."
terraform -chdir=infra destroy -auto-approve
echo "Done. (ECR repo deletion is manual if desired.)"
