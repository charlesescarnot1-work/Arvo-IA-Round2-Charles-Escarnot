.PHONY: venv tf-init run destroy

venv:
	python -m venv .venv && . .venv/bin/activate && pip install -r orchestrator/requirements.txt

tf-init:
	terraform -chdir=infra init

run:
	bash scripts/run_all.sh

destroy:
	bash scripts/destroy_all.sh
