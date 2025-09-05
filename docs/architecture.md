# Architecture

```mermaid
flowchart LR
  DEV[Developer] -->|prompt + repo| CLI[Orchestrator]
  CLI -->|Detect stack + build| Docker
  Docker --> ECR[(Amazon ECR)]
  CLI -->|tfvars| Terraform
  Terraform --> VPC[VPC + Subnets + IGW + RT]
  Terraform --> ALB[ALB:80 -> TG]
  Terraform --> ECS[ECS Fargate Service]
  ECS -->|pull| ECR
  ALB -->|HTTP| USER[(Public URL)]

