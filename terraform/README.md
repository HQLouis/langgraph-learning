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

## Project Structure

The Terraform configuration has been organized into logical files for better maintainability:

### Core Configuration
- `01-versions.tf` - Terraform and provider configurations
- `02-data-sources.tf` - Data sources for lookups (AWS account, AZs, Route53)
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `main.tf` - Documentation and overview

### Networking
- `03-networking.tf` - VPC, subnets, route tables, internet gateway
- `04-security-groups.tf` - Security groups for ALB and ECS tasks

### Application Infrastructure
- `05-alb.tf` - Application Load Balancer, target groups, listeners
- `06-ecr.tf` - ECR repository for Docker images
- `07-iam.tf` - IAM roles and policies for ECS
- `08-ecs-cluster.tf` - ECS cluster configuration
- `ecs.tf` - ECS service and task definitions

### Frontend & CDN
- `09-s3-frontend.tf` - S3 buckets for frontend hosting
- `10-cloudfront.tf` - CloudFront distributions
- `11-route53-acm.tf` - Route53 records and ACM certificates

### Monitoring
- `12-cloudwatch.tf` - CloudWatch log groups

## Why This Structure?

The previous monolithic `main.tf` (700+ lines) has been split into logical files:
- ✅ **Easier to navigate** - Find resources by category
- ✅ **Better git diffs** - Changes are isolated to specific files
- ✅ **Reduced merge conflicts** - Team members can work on different files
- ✅ **Clear dependencies** - Related resources are grouped together
- ✅ **Easier to review** - Smaller, focused files

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

