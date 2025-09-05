SHELL := bash

.PHONY: venv deps init fmt validate deploy url logs destroy

venv:
	py -3.13 -m venv .venv || py -3.11 -m venv .venv
	@echo "source .venv/Scripts/activate"

deps:
	source .venv/Scripts/activate && pip install -r orchestrator/requirements.txt

init:
	terraform -chdir=infra init -upgrade

fmt:
	terraform -chdir=infra fmt -recursive

validate:
	terraform -chdir=infra validate

deploy:
	source .venv/Scripts/activate && \
	python -m orchestrator deploy \
	  --repo https://github.com/Arvo-AI/hello_world \
	  --app-name hello-world \
	  --aws-region us-east-1 \
	  --aws-profile arvo

url:
	@echo "http://$$(terraform -chdir=infra output -raw alb_dns_name)"

logs:
	MSYS_NO_PATHCONV=1 aws logs tail /ecs/hello-world --since 15m --follow \
	  --region us-east-1 --profile arvo

destroy:
	terraform -chdir=infra destroy -auto-approve ; \
	aws ecr delete-repository --repository-name hello-world --force \
	  --region us-east-1 --profile arvo || true
