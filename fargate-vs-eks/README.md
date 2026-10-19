# ECS Fargate or EKS: the same container both ways

Code for the article **ECS Fargate or EKS: the same container deployed both ways, with the bill**
on the [NexifyPro blog](https://nexifypro.com/blog/ecs-fargate-or-eks-with-the-bill).

- `app/` the reference workload: a Node.js HTTP service that does a little CPU work per request,
  exposes `/healthz` with its version, and its Dockerfile.
- `terraform/shared/` one VPC with two public and two private subnets, a single NAT gateway and an
  ECR repository, used by both stacks. Outputs the VPC, subnet ids and the repository URL.
- `terraform/ecs-fargate/` stack A: an ECS service on Fargate behind an ALB with CPU target
  tracking. Inputs: the shared network ids, `image`, `app_version`, task size and task limits.
- `terraform/eks-auto/` stack B: an EKS cluster with Auto Mode (AWS-managed nodes, built-in load
  balancer controller and autoscaling). The workload itself is `terraform/k8s/app.yaml`: a
  Deployment, Service, IngressClass, Ingress and HorizontalPodAutoscaler, applied with kubectl.
- `bench/ramp.js` the k6 arrival-rate ramp (20 to 400 requests per second) that forces a scale-out
  from one task or pod to about ten.
- `scripts/measure.sh` timing helpers: time until a version is served, time to N running tasks or
  ready pods, and rollback (the first helper again, with the previous version).

## Run it

```bash
# 1. shared network and the image repository
cd terraform/shared && terraform init && terraform apply
REPO=$(terraform output -raw ecr_repository_url)

# 2. build and push the reference service
aws ecr get-login-password | docker login --username AWS --password-stdin "$REPO"
docker build -t "$REPO:v1" ../../app && docker push "$REPO:v1"

# 3a. stack A, with the network ids from step 1
cd ../ecs-fargate && terraform init && terraform apply -var "image=$REPO:v1" \
  -var "vpc_id=..." -var 'public_subnet_ids=[...]' -var 'private_subnet_ids=[...]'

# 3b. stack B, same network ids, then the workload
cd ../eks-auto && terraform init && terraform apply \
  -var "vpc_id=..." -var 'public_subnet_ids=[...]' -var 'private_subnet_ids=[...]'
$(terraform output -raw kubeconfig_command)
sed "s|IMAGE|$REPO:v1|" ../k8s/app.yaml | kubectl apply -f -

# 4. load and timings (one platform at a time)
k6 run -e URL=http://<load-balancer-dns> ../../bench/ramp.js
../../scripts/measure.sh scale ecs <cluster> <service> 10      # or: scale k8s <deployment> 10
../../scripts/measure.sh serving http://<load-balancer-dns> v2  # push-to-serving, or rollback with v1
```

Applying creates billable resources: the NAT gateway, two load balancers, Fargate tasks and an
EKS control plane. Destroy both stacks and then the shared network when you are done.

## Status

All three stacks pass `terraform fmt`, `terraform init` and `terraform validate` in this
repository's CI (Terraform 1.15.8, AWS provider 6.x); the service, the k6 script and the manifests
are syntax-checked there too. The measurements the article describes (push to serving, scale-out
under the ramp, rollback) have not been run for publication yet. When they are, the results land in
this folder as a dated CSV next to the commands that produced them. The cost table in the article
uses published prices observed on 2026-10-05.
