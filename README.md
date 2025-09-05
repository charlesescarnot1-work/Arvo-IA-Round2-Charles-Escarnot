# Déploiement « Hello‑World » sur AWS ECS Fargate

---

## 🌐 Résultat attendu

* Une URL publique de type : `http://<alb_dns_name>` renvoyant **ok**.
* Un service **ECS Fargate** derrière un **ALB** (port 80) déployé dans **us‑east‑1**.

---

## 🧱 Architecture (IaC Terraform)

* **VPC** `10.10.0.0/16`
* **2 subnets publics** (AZs dynamiques)
* **Internet Gateway** + **Route table publique** (`0.0.0.0/0`)
* **ALB** + **Target Group (ip)** + **Listener :80**
* **Security Groups**

  * ALB : TCP/80 → `0.0.0.0/0`
  * Tasks : TCP/5000 depuis l’ALB
* **ECS**

  * Cluster Fargate
  * Task Definition (256/512) + **logs CloudWatch** `/ecs/<app>`
  * Service (desired\_count par défaut = `1`)
* **ECR** : dépôt d’images `<app>` pour la conteneurisation

> Tous les objets sont gérés par Terraform via le dossier `infra/`.

---

## ✅ Prérequis (Windows 10/11, 64‑bit)

* **AWS CLI v2** (profil nommé `arvo`)
* **Docker Desktop** (WSL 2 « Running »)
* **Terraform** ≥ 1.5 (dans le `PATH`)
* **Python** ≥ 3.11 (3.13 OK) + **Git Bash**
* Un **utilisateur IAM** avec, pour la démo, la stratégie **AdministratorAccess** (à restreindre ensuite)

---

## 🚀 Déploiement — pas à pas (ce qui a été exécuté)

> Ouvrez **Git Bash** dans le dossier dézippé `autodeploy_mvp_plus` et laissez **Docker Desktop** tourner.

### 1) Configurer AWS CLI (une fois)

```powershell
aws configure --profile arvo
# Region: us-east-1  | Output: json
```

Vérifier :

```powershell
aws sts get-caller-identity --profile arvo
```

### 2) (Si nécessaire) Installer les dépendances Python et initialiser Terraform

```bash
# Créer puis activer la venv (3.13 fonctionne) la version doit être supérieur à la 3.10
py -3.13 -m venv .venv  ||  py -3.11 -m venv .venv
source .venv/Scripts/activate

pip install -r orchestrator/requirements.txt
terraform -chdir=infra init -upgrade
```

### 3) Build & push de l’image + génération des tfvars + apply (orchestrateur)

```bash
python -m orchestrator deploy \
  --repo https://github.com/Arvo-AI/hello_world \
  --app-name hello-world \
  --aws-region us-east-1 \
  --aws-profile arvo
```

L’orchestrateur :

1. détecte le type d’app (ici **Python:5000**),
2. prépare le `Dockerfile` minimal si besoin,
3. crée le dépôt **ECR** (si absent),
4. **build/push** l’image vers ECR,
5. écrit `infra/terraform.tfvars`,
6. exécute `terraform apply`.

### 4) Récupérer l’URL publique

```bash
echo "http://$(terraform -chdir=infra output -raw alb_dns_name)"
```

Ouvrez l’URL dans le navigateur → **ok**.

---

## 🔍 Vérifications utiles

* **ECS** : Console AWS → *ECS* → cluster `hello-world-cluster` → service `hello-world` → **Tasks** = `RUNNING`.
* **Target Group** : *EC2 → Load Balancing → Target Groups* → `hello-world-tg` → **healthy**.
* **URL** :

```bash
ALB=$(terraform -chdir=infra output -raw alb_dns_name)
echo "http://$ALB" && curl -sS "http://$ALB"
```

* **Logs CloudWatch (Git Bash)** : attention à la conversion de chemins, utilisez `MSYS_NO_PATHCONV=1` :

```bash
# suivi en temps réel
MSYS_NO_PATHCONV=1 aws logs tail /ecs/hello-world --follow \
  --region us-east-1 --profile arvo
```

### Check final rapide (tout-en-un)

```bash
# 1) URL répond
ALB=$(terraform -chdir=infra output -raw alb_dns_name); curl -sS "http://$ALB" | head -n1
# 2) Service stable
aws ecs describe-services --cluster hello-world-cluster --services hello-world \
  --region us-east-1 --profile arvo \
  --query 'services[0].{desired:desiredCount,running:runningCount,status:status}'
# 3) Cibles healthy
TG=$(aws elbv2 describe-target-groups --names hello-world-tg \
  --region us-east-1 --profile arvo --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 describe-target-health --target-group-arn "$TG" \
  --region us-east-1 --profile arvo --query 'TargetHealthDescriptions[].TargetHealth.State'
```

---

## 📝 Access logs (optionnel)

Par défaut, Gunicorn ne trace pas chaque requête. Pour voir des `"GET /" 200` dans CloudWatch :

1. Ajoutez dans `infra/terraform.tfvars` :

```
extra_env = {
  GUNICORN_CMD_ARGS = "--access-logfile - --log-level info"
}
```

2. Appliquez :

```bash
terraform -chdir=infra apply -auto-approve
```

3. Relancez le suivi des logs (cf. commandes ci‑dessus) et rafraîchissez l’URL.

---

## ⚙️ Variables Terraform principales (fichier `infra/variables.tf`)

* `aws_region` (string)
* `app_name` (string)
* `image_uri` (string, l’image ECR)
* `container_port` (number, défaut `8080` → pour hello world = `5000`)
* `desired_count` (number, défaut `1`)
* `extra_env` (map(string), variables d’env optionnelles)

> Les valeurs effectives sont alimentées par `terraform.tfvars` généré par l’orchestrateur.

---

## ↕️ Mise à l’échelle (exemple)

```bash
terraform -chdir=infra apply -auto-approve -var="desired_count=2"
```

---

## 🧹 Nettoyage (éviter les coûts)

```bash
terraform -chdir=infra destroy -auto-approve
aws ecr delete-repository --repository-name hello-world --force --region us-east-1 --profile arvo
```

---
## Architecture
Voir le schéma : [docs/architecture.md](docs/architecture.md)

## Sources & crédits
- AWS (ECS, ALB, ECR, VPC)
- Terraform (core + AWS provider)
- Docker

## Next steps
- Support d’autres cibles (Lambda, Kubernetes)
- Politiques IAM "least privilege"
- Détecteurs de stacks supplémentaires (Node, Django, etc.)
- HTTPS via ACM + listener 443
