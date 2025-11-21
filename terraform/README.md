# Terraform Infrastructure for Lingolino

Infrastructure as Code for deploying Lingolino to AWS.

## Quick Start

```bash
# Initialize
terraform init

# Preview changes
terraform plan

# Deploy
terraform apply

# View outputs
terraform output
```

## Files

- `main.tf` - Core infrastructure (VPC, ALB, S3, CloudFront, IAM)
- `ecs.tf` - ECS Fargate service and auto-scaling
- `variables.tf` - Configuration variables
- `outputs.tf` - Resource outputs

## Resources Created

### Networking
- VPC (10.0.0.0/16)
- 2 Public Subnets
- 2 Private Subnets
- Internet Gateway
- Security Groups

### Compute
- ECS Cluster
- Fargate Service (0.5 vCPU, 1GB RAM)
- Auto Scaling (1-3 tasks)
- Application Load Balancer

### Storage & CDN
- ECR Repository
- 2 S3 Buckets (web client + admin UI)
- 2 CloudFront Distributions

### Security
- IAM Roles
- Security Groups
- Secrets Manager integration

## Configuration

Edit `variables.tf` or pass variables:

```bash
terraform apply -var="environment=prod" -var="ecs_desired_count=2"
```

## Cost

~$56/month for dev environment (0.5 vCPU, 1GB RAM, 5 concurrent users)

## Cleanup

```bash
terraform destroy
```

See ../DEPLOYMENT.md for complete guide.

