# 🚀 Quick Deployment Reference

This is a condensed reference for deploying Lingolino to AWS. For full details, see [DEPLOYMENT.md](DEPLOYMENT.md).

## ⚡ Prerequisites

```bash
# Install tools
brew install terraform awscli

# Configure AWS
aws configure
```

## 📦 One-Time Setup (30 minutes)

### 1. Deploy Infrastructure

```bash
cd terraform
terraform init
terraform apply  # Type 'yes' to confirm
```

### 2. Save Outputs

```bash
# Copy these values - you'll need them!
terraform output alb_dns_name
terraform output ecr_repository_url
terraform output ecs_cluster_name
terraform output web_client_cloudfront_id
terraform output prompt_admin_cloudfront_id
```

### 3. Create Secrets

```bash
# Store your Google API key
aws secretsmanager create-secret \
  --name lingolino/google-api-key \
  --secret-string "YOUR_GOOGLE_API_KEY" \
  --region eu-central-1
```

### 4. Push Initial Docker Image

```bash
cd ..  # Back to project root

# Login to ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-central-1.amazonaws.com

# Build and push
docker build -t lingolino-api .
ECR_URL=$(terraform -chdir=terraform output -raw ecr_repository_url)
docker tag lingolino-api:latest $ECR_URL:latest
docker push $ECR_URL:latest
```

### 5. Configure GitHub Secrets

Go to GitHub Repo → Settings → Secrets → Actions

Add these secrets:
- `AWS_ACCESS_KEY_ID`: Your IAM user access key
- `AWS_SECRET_ACCESS_KEY`: Your IAM user secret key

### 6. Deploy!

```bash
git add .
git commit -m "Add AWS deployment pipeline"
git push origin main
```

✅ **Done!** GitHub Actions will deploy everything automatically.

---

## 🔄 Daily Workflow

### Deploying Backend Changes

```bash
# Make changes to backend/ or agentic-system/
git add .
git commit -m "Update backend feature"
git push origin main

# GitHub Actions automatically:
# 1. Builds Docker image
# 2. Pushes to ECR
# 3. Updates ECS service
# Watch at: github.com/YOUR_REPO/actions
```

### Deploying Frontend Changes

```bash
# Make changes to examples/web_client_example.html or prompt_admin_ui.html
git add .
git commit -m "Update frontend"
git push origin main

# GitHub Actions automatically:
# 1. Processes HTML files
# 2. Uploads to S3
# 3. Invalidates CloudFront cache
```

---

## 📍 Access URLs

After deployment, access your services at:

```bash
# Get URLs
terraform -chdir=terraform output alb_url               # API
terraform -chdir=terraform output web_client_cloudfront_url    # Web Client
terraform -chdir=terraform output prompt_admin_cloudfront_url  # Admin UI
```

**Example URLs**:
- API: `http://lingolino-alb-dev-123456.eu-central-1.elb.amazonaws.com`
- API Docs: `http://[ALB-URL]/docs`
- Web Client: `https://d1234567890.cloudfront.net`
- Prompt Admin: `https://d0987654321.cloudfront.net`

---

## 🔍 Monitoring

### View Logs

```bash
# Real-time logs
aws logs tail /ecs/lingolino-api --follow

# Last 10 minutes
aws logs tail /ecs/lingolino-api --since 10m

# Filter errors
aws logs tail /ecs/lingolino-api --filter-pattern "ERROR"
```

### Check Service Health

```bash
# ECS service status
aws ecs describe-services \
  --cluster lingolingo-cluster-dev \
  --services lingolino-api-service \
  --query 'services[0].{Status:status,Running:runningCount,Desired:desiredCount}'

# Check API health
curl $(terraform -chdir=terraform output -raw alb_url)/health
```

### GitHub Actions Status

Go to: `github.com/YOUR_REPO/actions`

---

## 🛠️ Common Tasks

### Scale Service

```bash
# Scale up to 2 tasks
terraform apply -var="ecs_desired_count=2"

# Scale down to 1
terraform apply -var="ecs_desired_count=1"

# Stop completely (to save costs)
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --desired-count 0
```

### Update Environment Variables

Edit `terraform/ecs.tf`, find the `environment` section, make changes, then:

```bash
cd terraform
terraform apply
```

### Roll Back Deployment

```bash
# Find previous task definition
aws ecs list-task-definitions --family lingolino-api-task

# Update service to use previous version
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --task-definition lingolino-api-task:PREVIOUS_REVISION
```

### View Costs

```bash
# Use AWS Cost Explorer (GUI)
# Or CLI:
aws ce get-cost-and-usage \
  --time-period Start=2024-01-01,End=2024-01-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter file://cost-filter.json
```

---

## 🐛 Troubleshooting

### Issue: ECS Task Won't Start

```bash
# Check task status
aws ecs describe-tasks \
  --cluster lingolino-cluster-dev \
  --tasks $(aws ecs list-tasks --cluster lingolino-cluster-dev --service-name lingolino-api-service --query 'taskArns[0]' --output text)

# Check logs
aws logs tail /ecs/lingolino-api --since 5m
```

**Common causes**:
- Missing secret in Secrets Manager
- Incorrect IAM permissions
- Image pull errors (check ECR)

### Issue: Health Check Failing

```bash
# Test health endpoint from local
ALB_URL=$(terraform -chdir=terraform output -raw alb_dns_name)
curl -v http://$ALB_URL/health

# Check security groups allow traffic
# Check container is listening on port 8000
```

### Issue: CORS Errors

Update CORS origins in `terraform/ecs.tf`:

```hcl
{
  name  = "CORS_ORIGINS"
  value = "https://your-domain.com,https://another-domain.com"
}
```

Then: `terraform apply`

### Issue: GitHub Actions Fails

1. Check secrets are set in GitHub
2. Verify AWS credentials have correct permissions
3. Check workflow logs for specific error
4. Ensure infrastructure is deployed (`terraform apply` succeeded)

---

## 🌐 Custom Domain Setup

### Quick Steps

1. **Request SSL Certificate**:
   ```bash
   aws acm request-certificate \
     --domain-name "*.lingolino.io" \
     --validation-method DNS \
     --region us-east-1
   ```

2. **Add DNS Validation Records** to your domain registrar

3. **Wait for validation** (5-30 minutes)

4. **Update Terraform**: Uncomment certificate sections in `terraform/main.tf`

5. **Create Route53 Records**:
   ```
   api.lingolino.io → ALB DNS
   text-chat-client.lingolino.io → CloudFront domain
   prompt-admin.lingolino.io → CloudFront domain
   ```

6. **Apply changes**: `terraform apply`

---

## 💰 Cost Management

### Monthly Costs (Estimate)

| Service | Cost |
|---------|------|
| Fargate (0.5 vCPU, 1GB) | ~$30 |
| ALB | ~$16 |
| Other (S3, CloudFront, logs) | ~$10 |
| **Total** | **~$56/month** |

### Save Money

```bash
# Stop service when not using
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --desired-count 0

# Restart when needed
aws ecs update-service \
  --cluster lingolino-cluster-dev \
  --service lingolino-api-service \
  --desired-count 1
```

### Destroy Everything

```bash
cd terraform
terraform destroy  # Type 'yes' to confirm

# This deletes ALL resources
# Cannot be undone!
```

---

## 📋 Useful Commands

```bash
# Login to ECR
aws ecr get-login-password --region eu-central-1 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.eu-central-1.amazonaws.com

# View Terraform outputs
terraform -chdir=terraform output

# Check AWS account
aws sts get-caller-identity

# List ECS tasks
aws ecs list-tasks --cluster lingolino-cluster-dev

# Invalidate CloudFront cache
aws cloudfront create-invalidation \
  --distribution-id $(terraform -chdir=terraform output -raw web_client_cloudfront_id) \
  --paths "/*"

# View S3 bucket contents
aws s3 ls s3://text-chat-client.lingolino.io/
```

---

## 🆘 Getting Help

1. **Check logs**: `aws logs tail /ecs/lingolino-api --follow`
2. **Read full guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
3. **Terraform docs**: [terraform/README.md](terraform/README.md)
4. **AWS Console**: Check ECS, CloudWatch, ECR services

---

## ✅ Deployment Checklist

- [ ] Terraform infrastructure deployed
- [ ] Secrets created in Secrets Manager
- [ ] Initial Docker image pushed
- [ ] GitHub secrets configured
- [ ] First deployment successful
- [ ] API health check passing
- [ ] Web client accessible
- [ ] Admin UI accessible

---

**🎉 You're all set! Push to `main` branch to deploy automatically.**

