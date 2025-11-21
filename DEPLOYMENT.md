# 🚀 AWS Deployment Guide for Lingolino

Complete guide to deploy Lingolino to AWS Fargate.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [AWS Credentials Setup](#aws-credentials-setup)
3. [Infrastructure Deployment](#infrastructure-deployment)
4. [GitHub Actions Configuration](#github-actions-configuration)
5. [Initial Deployment](#initial-deployment)
6. [Verification](#verification)
7. [Monitoring](#monitoring)
8. [Troubleshooting](#troubleshooting)

---

## ✅ Prerequisites

### Required Tools

```bash
# Install Terraform
brew install terraform

# Install AWS CLI
brew install awscli

# Verify installations
terraform --version  # >= 1.0
aws --version        # >= 2.0
docker --version     # For local testing
```

### AWS Account
- Active AWS account
- Sufficient permissions (see [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md))

---

## 🔐 AWS Credentials Setup

### 1. Create IAM User

See [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md) for detailed steps.

**Quick version**:
1. Create IAM user: `github-actions-lingolino`
2. Attach required policies (ECR, ECS, S3, CloudFront, etc.)
3. Generate access keys
4. Save credentials securely

### 2. Configure AWS CLI

```bash
aws configure

# Enter:
# AWS Access Key ID: [Your Key]
# AWS Secret Access Key: [Your Secret]
# Default region: eu-central-1
# Default output format: json

# Test
aws sts get-caller-identity
```

---

## 🏗️ Infrastructure Deployment

### 1. Deploy with Terraform

```bash
# Navigate to terraform directory
cd terraform

# Initialize Terraform
terraform init

# Review planned changes
terraform plan

# Apply infrastructure
terraform apply
# Type 'yes' to confirm
```

**This creates 35+ AWS resources**:
- VPC, subnets, security groups
- ECS cluster and service
- Application Load Balancer
- ECR repository
- S3 buckets for frontends
- CloudFront distributions
- IAM roles
- CloudWatch logs

### 2. Save Outputs

After deployment completes, save these outputs:

```bash
terraform output

# Important outputs:
# - alb_dns_name: API endpoint
# - ecr_repository_url: Docker registry
# - ecs_cluster_name: Cluster name
# - web_client_cloudfront_url: Web client URL
# - prompt_admin_cloudfront_url: Admin UI URL
```

### 3. Create Secrets in AWS Secrets Manager

```bash
aws secretsmanager create-secret \
  --name lingolino/google-api-key \
  --description "Google Gemini API Key for Lingolino" \
  --secret-string "YOUR_GOOGLE_API_KEY_HERE" \
  --region eu-central-1

# Verify
aws secretsmanager describe-secret \
  --secret-id lingolino/google-api-key \
  --region eu-central-1
```

### 4. Push Initial Docker Image

Before GitHub Actions can deploy, you need an initial image:

```bash
# Go to project root
cd ..

# Login to ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-central-1.amazonaws.com

# Build image
docker build -t lingolino-api .

# Tag image
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url)
docker tag lingolino-api:latest $ECR_URL:latest

# Push image
docker push $ECR_URL:latest
```

---

## 🔧 GitHub Actions Configuration

### 1. Add GitHub Secrets

Go to: GitHub → Your Repo → Settings → Secrets → Actions

Add these secrets:

| Secret Name | Value | Where to Find |
|-------------|-------|---------------|
| `AWS_ACCESS_KEY_ID` | Your IAM access key | From IAM user creation |
| `AWS_SECRET_ACCESS_KEY` | Your IAM secret | From IAM user creation |

**That's it!** All other configuration is in the workflow files.

### 2. Verify Workflows

Workflows are already configured:
- `.github/workflows/deploy-backend.yml` - Deploys API to ECS
- `.github/workflows/deploy-frontend.yml` - Deploys web client & admin UI

---

## 🎬 Initial Deployment

### 1. Commit and Push

```bash
# Stage all files
git add .

# Commit
git commit -m "Add AWS deployment pipeline"

# Push to main branch
git push origin main
```

### 2. Monitor GitHub Actions

1. Go to GitHub → Your Repo → **Actions**
2. Watch the workflows run:
   - ✅ Deploy Backend API to AWS Fargate
   - ✅ Deploy Frontend to S3 & CloudFront

### 3. Wait for Completion

Both workflows should complete with green checkmarks ✅

---

## ✅ Verification

### 1. Test API Backend

```bash
# Get ALB URL
ALB_URL=$(terraform -chdir=terraform output -raw alb_dns_name)

# Test health endpoint
curl http://$ALB_URL/health

# Expected response:
# {"status":"healthy","timestamp":"2024-..."}

# Test API docs
open http://$ALB_URL/docs
```

### 2. Test Web Client

```bash
# Get CloudFront URL
CF_URL=$(terraform -chdir=terraform output -raw web_client_cloudfront_url)

# Open in browser
open $CF_URL
```

- Web client should load
- Can start conversation
- Can send messages
- Receives AI responses

### 3. Test Prompt Admin UI

```bash
# Get CloudFront URL
CF_ADMIN=$(terraform -chdir=terraform output -raw prompt_admin_cloudfront_url)

# Open in browser
open $CF_ADMIN
```

### 4. Check Logs

```bash
# View logs (real-time)
aws logs tail /ecs/lingolino-api --follow

# View last 10 minutes
aws logs tail /ecs/lingolino-api --since 10m
```

### 5. Check ECS Service

```bash
aws ecs describe-services \
  --cluster lingolino-cluster-dev \
  --services lingolino-api-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'
```

---

## 📊 Monitoring

### CloudWatch Logs

```bash
# Real-time logs
aws logs tail /ecs/lingolino-api --follow

# Filter errors
aws logs tail /ecs/lingolino-api --filter-pattern "ERROR"

# Last 30 minutes
aws logs tail /ecs/lingolino-api --since 30m
```

### ECS Service Status

```bash
# Service details
aws ecs describe-services \
  --cluster lingolino-cluster-dev \
  --services lingolino-api-service

# List tasks
aws ecs list-tasks \
  --cluster lingolino-cluster-dev \
  --service-name lingolino-api-service
```

### CloudWatch Dashboard

Access via AWS Console:
- CloudWatch → Dashboards → Container Insights
- Metrics for CPU, Memory, Network, etc.

---

## 🐛 Troubleshooting

### Issue: ECS Task Won't Start

**Symptoms**: Task keeps stopping

**Check**:
```bash
# View task stopped reason
aws ecs describe-tasks \
  --cluster lingolino-cluster-dev \
  --tasks TASK_ARN \
  --query 'tasks[0].stoppedReason'

# Check logs
aws logs tail /ecs/lingolino-api --since 10m
```

**Common Causes**:
- Secret doesn't exist in Secrets Manager
- IAM role lacks permissions
- Image not found in ECR
- Health check failing

### Issue: Health Check Failing

**Check**:
```bash
# Test health endpoint locally
docker run -p 8000:8000 YOUR_ECR_URL:latest

# In another terminal
curl http://localhost:8000/health
```

**Solutions**:
- Verify `/health` endpoint works
- Check security group allows ALB → ECS traffic (port 8000)
- Increase health check grace period in `terraform/ecs.tf`

### Issue: CORS Errors

**Solution**: Update CORS_ORIGINS in `terraform/ecs.tf`:

```hcl
{
  name  = "CORS_ORIGINS"
  value = "https://your-cloudfront-domain.net,https://another-domain.com"
}
```

Then: `terraform apply`

### Issue: GitHub Actions Fails

**Check**:
1. Verify GitHub secrets are set correctly
2. Check IAM user has all required permissions
3. Review GitHub Actions logs for specific error
4. Ensure infrastructure is deployed (`terraform apply` succeeded)

**Common Issues**:
- Wrong AWS credentials
- Infrastructure not created yet
- ECS service name mismatch

---

## 💰 Cost Management

### Monthly Cost (Dev Environment)

| Service | Cost |
|---------|------|
| ECS Fargate (0.5 vCPU, 1GB) | ~$30 |
| ALB | ~$16 |
| S3 + CloudFront | ~$2 |
| Other (ECR, logs) | ~$8 |
| **Total** | **~$56/month** |

### Cost Optimization

**Stop service when not needed**:
```bash
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --desired-count 0
```

**Restart service**:
```bash
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --desired-count 1
```

---

## 🧹 Cleanup

To destroy all infrastructure:

```bash
cd terraform
terraform destroy
# Type 'yes' to confirm
```

⚠️ **Warning**: This deletes all resources and cannot be undone!

---

## 📝 Deployment Checklist

### Pre-Deployment
- [ ] AWS CLI installed and configured
- [ ] Terraform installed
- [ ] AWS credentials created
- [ ] `.env` file created with GOOGLE_API_KEY

### Infrastructure
- [ ] `terraform init` completed
- [ ] `terraform apply` succeeded
- [ ] Outputs saved
- [ ] Secret created in Secrets Manager
- [ ] Initial Docker image pushed to ECR

### GitHub
- [ ] GitHub secrets configured
- [ ] Repository code pushed
- [ ] Workflows triggered

### Verification
- [ ] API health check returns 200
- [ ] Web client accessible
- [ ] Admin UI accessible
- [ ] Can send/receive messages
- [ ] Logs show no critical errors

---

## 🎉 Success!

If all steps are complete, your Lingolino application is running in the cloud!

**What's Next?**
- Configure custom domain (optional)
- Set up CloudWatch alarms
- Review and optimize costs
- Scale as needed

---

## 📚 Additional Resources

- **Quick Reference**: [QUICK_DEPLOY.md](QUICK_DEPLOY.md)
- **Architecture Overview**: [DEPLOYMENT_SUMMARY.md](DEPLOYMENT_SUMMARY.md)
- **Terraform Details**: [terraform/README.md](terraform/README.md)
- **AWS Credentials**: [AWS_CREDENTIALS.md](AWS_CREDENTIALS.md)

---

**Need Help?** Check logs first: `aws logs tail /ecs/lingolino-api --follow`

